"""Timestamp conversion, missing values, and duplicate revisions."""

from datetime import UTC, date, datetime

import pandas as pd
import pytest

from gridsignal.data.normalization import (
    LocalTimeError,
    NormalizationError,
    duplicate_report,
    hour_ending_interval_end_utc,
    missing_hourly_timestamps,
    normalize_rows,
)
from gridsignal.data.source_registry import by_key

UTC = UTC


def test_winter_hour_ending_maps_to_utc() -> None:
    assert hour_ending_interval_end_utc(date(2024, 1, 15), 1, False) == datetime(2024, 1, 15, 7, tzinfo=UTC)
    assert hour_ending_interval_end_utc(date(2024, 1, 15), 24, False) == datetime(2024, 1, 16, 6, tzinfo=UTC)


def test_spring_forward_hour_ending_2_is_rejected() -> None:
    with pytest.raises(LocalTimeError):
        hour_ending_interval_end_utc(date(2024, 3, 10), 2, False)


def test_fall_back_repeated_hour_ending_2() -> None:
    first = hour_ending_interval_end_utc(date(2024, 11, 3), 2, False)
    second = hour_ending_interval_end_utc(date(2024, 11, 3), 2, True)
    assert first == datetime(2024, 11, 3, 7, tzinfo=UTC)
    assert second == datetime(2024, 11, 3, 8, tzinfo=UTC)
    assert second - first == pd.Timedelta(hours=1)


def test_missing_value_is_not_zero() -> None:
    rows = [
        {
            "DELIVERY_DATE": "2024-07-15",
            "HOUR_ENDING": 1,
            "DSTFlag": "N",
            "SYSTEM_WIDE_GEN": None,
            "STWPF_SYSTEM_WIDE": 10,
            "WGRPP_SYSTEM_WIDE": 9,
        }
    ]
    observations = normalize_rows(
        rows,
        by_key("wind_hourly"),
        ingested_at=datetime(2024, 7, 16, tzinfo=UTC),
        is_synthetic=True,
    )
    actual = next(item for item in observations if item.series == "wind_gen_mw")
    assert actual.value is None
    assert "missing_value" in actual.quality_flags
    assert actual.value != 0


def test_malformed_number_raises() -> None:
    rows = [
        {
            "OperDay": "2024-07-15",
            "HourEnding": 1,
            "DSTFlag": "N",
            "COAST": "nope",
            "EAST": 1,
            "FAR_WEST": 1,
            "NORTH": 1,
            "NORTH_C": 1,
            "SOUTHERN": 1,
            "SOUTH_C": 1,
            "WEST": 1,
            "TOTAL": 1,
        }
    ]
    with pytest.raises(NormalizationError):
        normalize_rows(rows, by_key("load_weather_zone"), ingested_at=datetime(2024, 7, 16, tzinfo=UTC))


def test_duplicates_and_conflicts() -> None:
    stamp = datetime(2024, 7, 15, 6, tzinfo=UTC)
    base = {
        "source_id": "NP6-345-CD",
        "series": "load_mw_total",
        "location": "TOTAL",
        "timestamp_utc": stamp,
        "value": 1.0,
    }
    dupes = duplicate_report(pd.DataFrame([base, dict(base)]))
    assert dupes.iloc[0]["status"] == "duplicate"
    conflict = duplicate_report(pd.DataFrame([base, {**base, "value": 2.0}]))
    assert conflict.iloc[0]["status"] == "conflict"


def test_missing_hours_are_listed_not_filled() -> None:
    stamps = pd.to_datetime(["2024-07-15T06:00:00Z", "2024-07-15T08:00:00Z"], utc=True)
    gaps = missing_hourly_timestamps(pd.Series(stamps))
    assert len(gaps) == 1
    assert gaps[0] == pd.Timestamp("2024-07-15T07:00:00Z")
