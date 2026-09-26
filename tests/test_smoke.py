"""End-to-end demo path used by the dashboard."""

from gridsignal.config import load_settings
from gridsignal.services.historical_replay import slice_as_of
from gridsignal.services.pipeline import quality_report, run_demo


def test_demo_pipeline_produces_dashboard_inputs() -> None:
    result = run_demo(load_settings(_env_file=None, data_mode="demo"))
    assert result.synthetic
    assert not result.observations.empty
    assert not result.anomalies.empty
    assert result.stress["score"].notna().any()
    assert set(result.simulations) >= {"idle", "price_arbitrage", "grid_stress", "hybrid"}
    assert result.explanations
    quality = quality_report(result)
    assert quality["conflict_groups"] == 0
    as_of = result.stress["timestamp_utc"].iloc[len(result.stress) // 2]
    view = slice_as_of(result, as_of)
    assert view["observations"]["timestamp_utc"].max() <= as_of
    assert result.simulations["hybrid"].summary["violation_count"] == 0
