"""ERCOT Public API client.

Auth, pacing, and error handling follow the official registration guide and
known-limits page. Report rows are discovered from each product's ``fields``
metadata. This module does not invent artifact slugs.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pandas as pd
import requests

from gridsignal.config import API_ROOT, TOKEN_SCOPE, TOKEN_URL, Settings
from gridsignal.data.cache import ResponseCache
from gridsignal.data.schemas import DataPage, ReportField, TokenResponse
from gridsignal.data.source_registry import DatasetSpec

logger = logging.getLogger("gridsignal.ercot")

Sleeper = Callable[[float], None]


class ErcotError(Exception):
    pass


class ErcotAuthError(ErcotError):
    pass


class ErcotForbidden(ErcotError):
    pass


class ErcotNotFound(ErcotError):
    pass


class ErcotRateLimitError(ErcotError):
    pass


class ErcotServerError(ErcotError):
    pass


class ErcotSchemaError(ErcotError):
    pass


class RedactingFilter(logging.Filter):
    def __init__(self, secrets: list[str]) -> None:
        super().__init__()
        self.secrets = [item for item in secrets if item]

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for secret in self.secrets:
            message = message.replace(secret, "***")
        record.msg = message
        record.args = ()
        return True


def install_redaction(secrets: list[str]) -> None:
    logger.filters = [item for item in logger.filters if not isinstance(item, RedactingFilter)]
    logger.addFilter(RedactingFilter(secrets))


def build_range_params(
    fields: list[ReportField],
    start: date,
    end: date,
    page: int,
    size: int,
) -> dict[str, Any]:
    """Build query params from metadata.

    ``page`` and ``size`` are the paging controls ERCOT staff described
    (default page size 1,000). ``{field}From`` / ``{field}To`` is the ranged
    filter form staff demonstrated for ``deliveryDate`` and ``hourEnding``.
    A filter is added only when that field is present and ``hasRange`` is true.
    """
    params: dict[str, Any] = {"page": page, "size": size}
    by_name = {field.name: field for field in fields}
    for name in ("deliveryDate", "operatingDay", "postedDatetime", "SCEDTimestamp"):
        field = by_name.get(name)
        if field is None or not field.hasRange:
            continue
        params[f"{name}From"] = start.isoformat()
        params[f"{name}To"] = end.isoformat()
        break
    else:
        # Fall back to any DATE field the metadata marks as ranged.
        for field in fields:
            if field.hasRange and (field.dataType or "").upper() == "DATE":
                params[f"{field.name}From"] = start.isoformat()
                params[f"{field.name}To"] = end.isoformat()
                break
    return params


def parse_data_page(payload: dict[str, Any]) -> pd.DataFrame:
    page = DataPage.model_validate(payload)
    if page.data is None:
        if page.fields:
            raise ErcotSchemaError(
                "ERCOT returned report metadata without data rows. "
                "A ranged filter such as deliveryDateFrom is required for data."
            )
        raise ErcotSchemaError("response did not contain a data array")
    if not page.fields:
        raise ErcotSchemaError("response data has no field list")
    names = [field.name for field in page.fields]
    for index, row in enumerate(page.data):
        if len(row) != len(names):
            raise ErcotSchemaError(f"row {index} has {len(row)} values, expected {len(names)}")
    frame = pd.DataFrame(page.data, columns=names)
    return frame


class ErcotClient:
    def __init__(
        self,
        settings: Settings,
        session: requests.Session | None = None,
        sleeper: Sleeper = time.sleep,
        cache: ResponseCache | None = None,
    ) -> None:
        self.settings = settings
        self.session = session or requests.Session()
        self.sleeper = sleeper
        self.cache = cache or ResponseCache(settings.cache_path)
        self._id_token = ""
        self._token_deadline: datetime | None = None
        self._last_request_at = 0.0
        self._auth_failures = 0
        install_redaction(
            [
                settings.ercot_password,
                settings.ercot_subscription_key,
                settings.ercot_username,
            ]
        )

    def _pace(self) -> None:
        wait = self.settings.min_request_interval_s - (time.monotonic() - self._last_request_at)
        if wait > 0:
            self.sleeper(wait)
        self._last_request_at = time.monotonic()

    def authenticate(self, force: bool = False) -> str:
        if not force and self._id_token and self._token_deadline and datetime.now(UTC) < self._token_deadline:
            return self._id_token
        if not self.settings.ercot_username or not self.settings.ercot_password:
            raise ErcotAuthError("ERCOT_USERNAME and ERCOT_PASSWORD are required. See docs/DATA_SOURCES.md.")
        # Form body, not the query string, so credentials stay out of URLs.
        response = self.session.post(
            TOKEN_URL,
            data={
                "username": self.settings.ercot_username,
                "password": self.settings.ercot_password,
                "grant_type": "password",
                "scope": TOKEN_SCOPE,
                "client_id": self.settings.ercot_client_id,
                "response_type": "id_token",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=self.settings.request_timeout_s,
        )
        if response.status_code != 200:
            raise ErcotAuthError(f"token endpoint returned HTTP {response.status_code}")
        token = TokenResponse.model_validate(response.json())
        # The registration guide says to send the ID token. It expires in one hour
        # and cannot be refreshed; a new POST is required.
        self._id_token = token.id_token
        skew = timedelta(seconds=60)
        self._token_deadline = datetime.now(UTC) + timedelta(seconds=token.expires_in) - skew
        install_redaction(
            [
                self.settings.ercot_password,
                self.settings.ercot_subscription_key,
                self.settings.ercot_username,
                self._id_token,
            ]
        )
        logger.info("ERCOT ID token acquired; expires_in=%s", token.expires_in)
        return self._id_token

    def _headers(self) -> dict[str, str]:
        if not self.settings.ercot_subscription_key:
            raise ErcotAuthError(
                "ERCOT_SUBSCRIPTION_KEY is missing. Copy the API Explorer Primary key "
                "into .env. Do not paste it into chat."
            )
        token = self.authenticate()
        return {
            "Authorization": f"Bearer {token}",
            "Ocp-Apim-Subscription-Key": self.settings.ercot_subscription_key,
            "Accept": "application/json",
        }

    def request_json(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        params = params or {}
        if use_cache:
            cached = self.cache.get(url, params)
            if cached is not None:
                logger.info("cache hit %s", url)
                return cached
        payload = self._request_with_retries(url, params)
        if use_cache:
            self.cache.put(url, params, payload)
        return payload

    def _request_with_retries(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        refreshed = False
        last_error: Exception | None = None
        for attempt in range(self.settings.max_retries):
            self._pace()
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=self._headers(),
                    timeout=self.settings.request_timeout_s,
                )
            except requests.Timeout as exc:
                last_error = exc
                self._backoff(attempt)
                continue
            except requests.RequestException as exc:
                last_error = exc
                self._backoff(attempt)
                continue

            status = response.status_code
            if status == 200:
                try:
                    body = response.json()
                except ValueError as exc:
                    raise ErcotSchemaError("ERCOT response was not JSON") from exc
                if not isinstance(body, dict):
                    raise ErcotSchemaError("ERCOT JSON response was not an object")
                return body
            if status == 401 and not refreshed:
                logger.info("HTTP 401; requesting a new ID token")
                self.authenticate(force=True)
                refreshed = True
                continue
            if status == 401:
                raise ErcotAuthError(self._safe_error(response))
            if status == 403:
                raise ErcotForbidden(self._safe_error(response))
            if status == 404:
                raise ErcotNotFound(self._safe_error(response))
            if status == 429:
                self._sleep_retry_after(response, attempt)
                last_error = ErcotRateLimitError(self._safe_error(response))
                continue
            if status >= 500:
                last_error = ErcotServerError(self._safe_error(response))
                self._backoff(attempt)
                continue
            raise ErcotError(self._safe_error(response))
        raise ErcotError(f"request failed after retries: {last_error}")

    def _safe_error(self, response: requests.Response) -> str:
        text = response.text[:300]
        for secret in (
            self.settings.ercot_password,
            self.settings.ercot_subscription_key,
            self._id_token,
        ):
            if secret:
                text = text.replace(secret, "***")
        return f"HTTP {response.status_code}: {text}"

    def _backoff(self, attempt: int) -> None:
        self.sleeper(min(30.0, 0.5 * (2**attempt)))

    def _sleep_retry_after(self, response: requests.Response, attempt: int) -> None:
        header = response.headers.get("Retry-After", "")
        try:
            delay = float(header)
        except ValueError:
            delay = min(60.0, 2.0 * (2**attempt))
        logger.info("HTTP 429; waiting %.1fs", delay)
        self.sleeper(delay)

    def list_products(self) -> dict[str, Any]:
        return self.request_json(API_ROOT)

    def resolve_artifact_url(self, spec: DatasetSpec) -> str:
        """Prefer the catalog href. Use a hardcoded path only when ERCOT published it."""
        product_url = f"{API_ROOT}/{spec.emil_id.lower()}"
        try:
            payload = self.request_json(product_url)
        except ErcotError:
            if spec.candidate_path and spec.candidate_status in {
                "official_user_guide",
                "staff_discussion",
                "official_release_notes",
            }:
                logger.info("catalog lookup failed; using published path for %s", spec.emil_id)
                return API_ROOT + spec.candidate_path
            raise
        artifacts = payload.get("artifacts") or []
        embedded = payload.get("_embedded") or {}
        if not artifacts and isinstance(embedded, dict):
            artifacts = embedded.get("artifacts") or []
        for artifact in artifacts:
            links = artifact.get("_links") or {}
            endpoint = (links.get("endpoint") or {}).get("href")
            if endpoint:
                return str(endpoint)
            if artifact.get("endpoint"):
                return str(artifact["endpoint"])
        if spec.candidate_path and spec.candidate_status in {
            "official_user_guide",
            "staff_discussion",
            "official_release_notes",
        }:
            return API_ROOT + spec.candidate_path
        raise ErcotNotFound(
            f"No artifact endpoint published in the catalog for {spec.emil_id}. Refusing to guess a slug."
        )

    def fetch_report(
        self,
        spec: DatasetSpec,
        start: date,
        end: date,
        extra_params: dict[str, Any] | None = None,
    ) -> pd.DataFrame:
        url = self.resolve_artifact_url(spec)
        metadata = self.request_json(url, params={})
        fields = [ReportField.model_validate(item) for item in metadata.get("fields") or []]
        if not fields:
            raise ErcotSchemaError(f"{spec.emil_id} metadata did not include fields")
        frames: list[pd.DataFrame] = []
        page = 1
        total_pages = 1
        while page <= total_pages:
            params = build_range_params(fields, start, end, page, self.settings.page_size)
            if extra_params:
                params.update(extra_params)
            payload = self.request_json(url, params=params)
            frame = parse_data_page(payload)
            frames.append(frame)
            meta = payload.get("_meta") or {}
            total_pages = int(meta.get("totalPages") or 1)
            page += 1
            if page > 1000:
                raise ErcotError("pagination exceeded 1000 pages; narrow the date range")
        if not frames:
            return pd.DataFrame()
        combined = pd.concat(frames, ignore_index=True)
        self.cache.record_coverage(spec.key, start, end)
        return combined
