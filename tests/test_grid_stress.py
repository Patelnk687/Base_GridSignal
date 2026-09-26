"""Stress weights drop out when an input is missing."""

from datetime import UTC, datetime

import pandas as pd

from gridsignal.analytics.grid_stress import DEFAULT_WEIGHTS, compute_stress
from gridsignal.data.schemas import Observation, SeriesKind

UTC = UTC


def _obs(series: str, location: str, hour: int, value: float | None, kind: SeriesKind = SeriesKind.ACTUAL) -> dict:
    return Observation(
        observation_id=f"{series}-{hour}",
        source_id="TEST",
        source_name="test",
        dataset_key="test",
        location=location,
        series=series,
        kind=kind,
        timestamp_utc=datetime(2024, 7, 1, hour, tzinfo=UTC),
        interval_hours=1.0,
        value=value,
        unit="MW" if "price" not in series else "USD/MWh",
        ingested_at_utc=datetime(2024, 7, 2, tzinfo=UTC),
    ).model_dump()


def _frame(include_price: bool, price_fill: float | None = None) -> pd.DataFrame:
    rows = []
    for hour in range(20):
        rows.append(_obs("load_mw_total", "TOTAL", hour, 40000 + hour * 100))
        rows.append(_obs("wind_gen_mw", "SYSTEM", hour, 10000.0))
        rows.append(_obs("solar_gen_mw", "SYSTEM", hour, 1000.0))
        if include_price:
            price = 30.0 if price_fill is None else price_fill
            if hour == 19:
                price = 400.0
            rows.append(_obs("spp_usd_per_mwh", "HB_HUBAVG", hour, price, SeriesKind.PRICE))
    return pd.DataFrame(rows)


def test_missing_price_is_not_treated_as_zero() -> None:
    full = compute_stress(_frame(True), window=6, min_periods=4)
    missing = compute_stress(_frame(False), window=6, min_periods=4)
    zeroed = compute_stress(_frame(True, price_fill=0.0), window=6, min_periods=4)
    assert (missing["status"] == "incomplete").any()
    last_missing = missing.dropna(subset=["score"]).iloc[-1]
    last_zero = zeroed.dropna(subset=["score"]).iloc[-1]
    assert last_missing["score"] != last_zero["score"]
    assert last_missing["component_price_level"] is None
    assert full.dropna(subset=["score"]).iloc[-1]["score"] is not None


def test_weights_renormalize() -> None:
    scored = compute_stress(_frame(False), window=6, min_periods=4)
    row = scored.dropna(subset=["score"]).iloc[-1]
    present = {name: DEFAULT_WEIGHTS[name] for name in DEFAULT_WEIGHTS if row[f"component_{name}"] is not None}
    expected = sum(present[name] * row[f"component_{name}"] for name in present) / sum(present.values())
    assert abs(row["score"] - expected) < 0.02
    assert row["completeness"] < 1
