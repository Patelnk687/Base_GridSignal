"""Known spikes and a future-data leakage check."""

from __future__ import annotations

import pandas as pd

from gridsignal.analytics.anomaly_detection import AnomalyRule, detect_series, isolation_forest_scores
from gridsignal.analytics.features import pivot_series
from gridsignal.config import load_settings
from gridsignal.data.sample_data import SPIKE_INDEX, load_synthetic_frame
from gridsignal.services.pipeline import run_demo


def _rule() -> AnomalyRule:
    return AnomalyRule("value", "LAB", "price_spike", 10.0, z_threshold=3.0, direction="up")


def _series() -> pd.Series:
    index = pd.date_range("2024-07-01", periods=30, freq="h", tz="UTC")
    values = pd.Series(20.0, index=index)
    values.iloc[20] = 200.0
    return values


def test_spike_is_flagged_and_quiet_hours_are_not() -> None:
    events = detect_series(_series(), _rule(), window=8, min_periods=6, source_id="TEST")
    stamps = [pd.Timestamp(event["timestamp_utc"]) for event in events]
    assert pd.Timestamp("2024-07-01 20:00", tz="UTC") in stamps
    assert all(stamp >= pd.Timestamp("2024-07-01 08:00", tz="UTC") for stamp in stamps)


def test_future_values_do_not_change_an_earlier_baseline() -> None:
    original = _series()
    mutated = original.copy()
    mutated.iloc[21:] = 9999.0
    rule = _rule()
    before = detect_series(original, rule, window=8, min_periods=6, source_id="TEST")
    after = detect_series(mutated, rule, window=8, min_periods=6, source_id="TEST")
    target = pd.Timestamp("2024-07-01 20:00", tz="UTC")
    left = next(event for event in before if pd.Timestamp(event["timestamp_utc"]) == target)
    right = next(event for event in after if pd.Timestamp(event["timestamp_utc"]) == target)
    assert left["baseline"] == right["baseline"]
    assert left["modified_z"] == right["modified_z"]


def test_isolation_forest_does_not_score_its_training_prefix() -> None:
    values = _series()
    scores = isolation_forest_scores(values, train_end=15)
    assert scores.iloc[:15].isna().all()
    assert scores.iloc[15:].notna().any()


def test_demo_scenario_flags_the_constructed_spike() -> None:
    frame = load_synthetic_frame()
    result = run_demo(load_settings(_env_file=None, data_mode="demo"))
    prices = pivot_series(frame, "spp_usd_per_mwh", "HB_HUBAVG")
    spike_time = prices.index[SPIKE_INDEX]
    categories = set(result.anomalies.loc[result.anomalies["timestamp_utc"] == spike_time, "category"])
    assert "price_spike" in categories
    assert bool(result.observations["is_synthetic"].all())
