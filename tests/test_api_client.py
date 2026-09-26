"""Mocked ERCOT HTTP behavior."""

import json
import logging
from datetime import date

import pytest

from gridsignal.config import Settings
from gridsignal.data.cache import ResponseCache, missing_ranges
from gridsignal.data.ercot_client import (
    ErcotAuthError,
    ErcotClient,
    ErcotForbidden,
    ErcotNotFound,
    ErcotSchemaError,
    build_range_params,
    parse_data_page,
)
from gridsignal.data.schemas import ReportField
from gridsignal.data.source_registry import by_key


class FakeResponse:
    def __init__(self, status: int, payload: dict | None = None, headers: dict | None = None, text: str = ""):
        self.status_code = status
        self._payload = payload
        self.headers = headers or {}
        self.text = text or (json.dumps(payload) if payload is not None else "")

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


class FakeSession:
    def __init__(self, gets: list[FakeResponse], posts: list[FakeResponse] | None = None):
        self.gets = list(gets)
        self.posts = list(posts or [])
        self.calls: list[tuple[str, str]] = []

    def post(self, url, data=None, headers=None, timeout=None):
        self.calls.append(("POST", url))
        return self.posts.pop(0)

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append(("GET", url))
        return self.gets.pop(0)


def _settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        ercot_username="user",
        ercot_password="secret-password",
        ercot_subscription_key="secret-key",
        cache_path=tmp_path / "cache.sqlite",
        min_request_interval_s=0,
        max_retries=3,
    )


def test_authenticate_uses_form_body_and_id_token(tmp_path) -> None:
    session = FakeSession(
        [],
        [
            FakeResponse(
                200,
                {
                    "token_type": "Bearer",
                    "expires_in": "3600",
                    "id_token": "id-token-value",
                    "access_token": "access-token-value",
                },
            )
        ],
    )
    client = ErcotClient(_settings(tmp_path), session=session, sleeper=lambda _: None)
    token = client.authenticate()
    assert token == "id-token-value"
    assert session.calls[0][0] == "POST"


def test_redacts_password(tmp_path, caplog) -> None:
    session = FakeSession(
        [],
        [FakeResponse(200, {"token_type": "Bearer", "expires_in": 3600, "id_token": "id-token-value"})],
    )
    client = ErcotClient(_settings(tmp_path), session=session, sleeper=lambda _: None)
    client.authenticate()
    with caplog.at_level(logging.INFO, logger="gridsignal.ercot"):
        logging.getLogger("gridsignal.ercot").info("password=secret-password key=secret-key")
    assert "secret-password" not in caplog.text
    assert "secret-key" not in caplog.text


def test_401_refreshes_once(tmp_path) -> None:
    posts = [
        FakeResponse(200, {"token_type": "Bearer", "expires_in": 3600, "id_token": "first"}),
        FakeResponse(200, {"token_type": "Bearer", "expires_in": 3600, "id_token": "second"}),
    ]
    gets = [FakeResponse(401, {"message": "expired"}), FakeResponse(200, {"ok": True})]
    client = ErcotClient(
        _settings(tmp_path),
        session=FakeSession(gets, posts),
        sleeper=lambda _: None,
    )
    body = client.request_json("https://api.ercot.com/api/public-reports", use_cache=False)
    assert body["ok"] is True


def test_429_then_success(tmp_path) -> None:
    posts = [FakeResponse(200, {"token_type": "Bearer", "expires_in": 3600, "id_token": "tok"})]
    gets = [
        FakeResponse(429, {"error_key": "throttled"}, headers={"Retry-After": "0"}),
        FakeResponse(200, {"ok": 1}),
    ]
    client = ErcotClient(_settings(tmp_path), session=FakeSession(gets, posts), sleeper=lambda _: None)
    assert client.request_json("https://example.test", use_cache=False)["ok"] == 1


def test_404_and_403(tmp_path) -> None:
    posts = [FakeResponse(200, {"token_type": "Bearer", "expires_in": 3600, "id_token": "tok"})]
    client = ErcotClient(
        _settings(tmp_path),
        session=FakeSession([FakeResponse(404, {"message": "missing"})], posts),
        sleeper=lambda _: None,
    )
    with pytest.raises(ErcotNotFound):
        client.request_json("https://example.test/missing", use_cache=False)
    posts2 = [FakeResponse(200, {"token_type": "Bearer", "expires_in": 3600, "id_token": "tok"})]
    client2 = ErcotClient(
        _settings(tmp_path),
        session=FakeSession([FakeResponse(403, {"message": "no"})], posts2),
        sleeper=lambda _: None,
    )
    with pytest.raises(ErcotForbidden):
        client2.request_json("https://example.test/denied", use_cache=False)


def test_pagination_and_schema(tmp_path) -> None:
    fields = [
        {"name": "deliveryDate", "dataType": "DATE", "hasRange": True},
        {"name": "value", "dataType": "DOUBLE", "hasRange": False},
    ]
    page1 = {"fields": fields, "data": [["2024-07-15", 1]], "_meta": {"totalPages": 2}}
    page2 = {"fields": fields, "data": [["2024-07-16", 2]], "_meta": {"totalPages": 2}}
    product = {
        "artifacts": [
            {
                "_links": {
                    "endpoint": {"href": "https://api.ercot.com/api/public-reports/np3-233-cd/hourly_res_outage_cap"}
                }
            }
        ]
    }
    meta = {"fields": fields}
    posts = [FakeResponse(200, {"token_type": "Bearer", "expires_in": 3600, "id_token": "tok"})]
    gets = [FakeResponse(200, product), FakeResponse(200, meta), FakeResponse(200, page1), FakeResponse(200, page2)]
    client = ErcotClient(_settings(tmp_path), session=FakeSession(gets, posts), sleeper=lambda _: None)
    frame = client.fetch_report(by_key("outage_capacity"), date(2024, 7, 15), date(2024, 7, 16))
    assert list(frame["value"]) == [1, 2]
    with pytest.raises(ErcotSchemaError):
        parse_data_page({"fields": fields, "data": [["only-one"]]})


def test_query_builder_uses_only_ranged_fields() -> None:
    params = build_range_params(
        [ReportField(name="deliveryDate", dataType="DATE", hasRange=True), ReportField(name="settlementPoint")],
        date(2024, 7, 1),
        date(2024, 7, 2),
        1,
        1000,
    )
    assert params["deliveryDateFrom"] == "2024-07-01"
    assert params["deliveryDateTo"] == "2024-07-02"
    assert "settlementPoint" not in params


def test_missing_ranges_and_cache(tmp_path) -> None:
    assert missing_ranges(date(2024, 7, 1), date(2024, 7, 5), [(date(2024, 7, 2), date(2024, 7, 3))]) == [
        (date(2024, 7, 1), date(2024, 7, 1)),
        (date(2024, 7, 4), date(2024, 7, 5)),
    ]
    cache = ResponseCache(tmp_path / "c.sqlite")
    cache.put("https://example.test", {"page": 1}, {"data": [1]})
    assert cache.get("https://example.test", {"page": 1}) == {"data": [1]}


def test_missing_subscription_key(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        ercot_username="user",
        ercot_password="pw",
        ercot_subscription_key="",
        cache_path=tmp_path / "c.sqlite",
        min_request_interval_s=0,
    )
    client = ErcotClient(settings, session=FakeSession([]), sleeper=lambda _: None)
    with pytest.raises(ErcotAuthError):
        client.request_json("https://example.test", use_cache=False)
