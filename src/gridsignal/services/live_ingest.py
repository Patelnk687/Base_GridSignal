"""Pull a bounded live window from ERCOT Public Reports into observations."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pandas as pd

from gridsignal.config import Settings
from gridsignal.data.ercot_client import ErcotClient, ErcotError
from gridsignal.data.normalization import NormalizationError, normalize_rows, observations_frame
from gridsignal.data.schemas import Observation
from gridsignal.data.source_registry import by_key, datasets

# Named points only. Unfiltered NP6-905 is ~160k rows/day.
DEFAULT_PRICE_POINTS = ("HB_HUBAVG", "LZ_HOUSTON", "LZ_WEST", "HB_NORTH")
REQUIRED_LIVE_KEYS = ("load_weather_zone", "wind_hourly", "solar_hourly", "rt_spp")


def live_window(days: int = 7) -> tuple[date, date]:
    end = date.today()
    start = end - timedelta(days=max(1, days))
    return start, end


def _dedupe_latest_posting(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep the latest postedDatetime revision per delivery hour when present."""
    if frame.empty or "postedDatetime" not in frame.columns:
        return frame
    keys = [column for column in ("deliveryDate", "operatingDay", "hourEnding") if column in frame.columns]
    if not keys:
        return frame
    ordered = frame.sort_values("postedDatetime")
    return ordered.drop_duplicates(subset=keys, keep="last").reset_index(drop=True)


def _hourly_mean_prices(frame: pd.DataFrame) -> pd.DataFrame:
    """Average DeliveryInterval prices into one hour-ending row per point."""
    if frame.empty:
        return frame
    work = frame.copy()
    work["settlementPointPrice"] = pd.to_numeric(work["settlementPointPrice"], errors="coerce")
    grouped = (
        work.groupby(["deliveryDate", "deliveryHour", "settlementPoint", "DSTFlag"], dropna=False)[
            "settlementPointPrice"
        ]
        .mean()
        .reset_index()
    )
    grouped = grouped.rename(columns={"deliveryHour": "hourEnding"})
    return grouped


def fetch_dataset_frame(
    client: ErcotClient,
    key: str,
    start: date,
    end: date,
    *,
    price_points: tuple[str, ...] = DEFAULT_PRICE_POINTS,
) -> pd.DataFrame:
    spec = by_key(key)
    if key == "rt_spp":
        frames: list[pd.DataFrame] = []
        for point in price_points:
            frames.append(
                client.fetch_report(
                    spec,
                    start,
                    end,
                    extra_params={"settlementPoint": point},
                )
            )
        if not frames:
            return pd.DataFrame()
        combined = pd.concat(frames, ignore_index=True)
        return _hourly_mean_prices(combined)
    frame = client.fetch_report(spec, start, end)
    return _dedupe_latest_posting(frame)


def observations_from_live(
    settings: Settings,
    *,
    days: int = 7,
    price_points: tuple[str, ...] = DEFAULT_PRICE_POINTS,
    client: ErcotClient | None = None,
) -> tuple[pd.DataFrame, list[str], str]:
    """Return observations, warnings, and a scenario id for the live window."""
    start, end = live_window(days)
    scenario_id = f"LIVE-{start.isoformat()}_to_{end.isoformat()}"
    warnings: list[str] = []
    client = client or ErcotClient(settings)
    ingested_at = datetime.now(UTC)
    observations: list[Observation] = []

    for key in REQUIRED_LIVE_KEYS:
        spec = by_key(key)
        try:
            frame = fetch_dataset_frame(client, key, start, end, price_points=price_points)
        except ErcotError as exc:
            warnings.append(f"{spec.emil_id} ({key}) fetch failed: {exc}")
            continue
        if frame.empty:
            warnings.append(f"{spec.emil_id} ({key}) returned no rows for {start}..{end}.")
            continue
        rows = frame.to_dict(orient="records")
        try:
            observations.extend(
                normalize_rows(
                    rows,
                    spec,
                    ingested_at=ingested_at,
                    is_synthetic=False,
                    raw_ref=scenario_id,
                )
            )
        except NormalizationError as exc:
            warnings.append(f"{spec.emil_id} ({key}) normalize failed: {exc}")

    optional = [item.key for item in datasets() if item.mvp and item.key not in REQUIRED_LIVE_KEYS]
    for key in optional:
        # Optional MVP products stay catalog-only until needed; skip by default for speed.
        _ = key

    if not observations:
        raise ErcotError("Live pull produced no observations. Check credentials and date window.")

    warnings.append(
        f"Live ERCOT Public API window {start} → {end}. "
        f"Prices are hourly means of named points {', '.join(price_points)}."
    )
    return observations_frame(observations), warnings, scenario_id
