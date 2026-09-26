"""Demo and live orchestration. Live fetches stay behind credentials."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from gridsignal.analytics.anomaly_detection import detect_anomalies
from gridsignal.analytics.features import pivot_series
from gridsignal.analytics.forecasting import price_forecast_report
from gridsignal.analytics.grid_stress import compute_stress
from gridsignal.battery.fleet import SimulationResult, compare_strategies
from gridsignal.battery.models import FleetSpec
from gridsignal.config import Settings, load_settings
from gridsignal.data.normalization import duplicate_report, missing_hourly_timestamps
from gridsignal.data.sample_data import SCENARIO_ID, load_synthetic_frame
from gridsignal.explain.evidence import Explanation, bundle_for_event
from gridsignal.explain.llm_provider import explain_with_ollama
from gridsignal.explain.templates import explain_anomaly


@dataclass
class PipelineResult:
    mode: str
    scenario_id: str
    synthetic: bool
    observations: pd.DataFrame
    anomalies: pd.DataFrame
    stress: pd.DataFrame
    simulations: dict[str, SimulationResult]
    explanations: list[Explanation]
    forecast: dict[str, object]
    warnings: list[str] = field(default_factory=list)
    fleet: FleetSpec = field(default_factory=FleetSpec)


def _explain_all(anomalies: pd.DataFrame, observations: pd.DataFrame, settings: Settings) -> list[Explanation]:
    explanations: list[Explanation] = []
    if anomalies.empty:
        return explanations
    for _, event in anomalies.iterrows():
        items = bundle_for_event(event, observations)
        payload = event.to_dict()
        if settings.llm_provider.lower() == "ollama":
            explanations.append(
                explain_with_ollama(
                    payload,
                    items,
                    base_url=settings.ollama_base_url,
                    model=settings.ollama_model,
                )
            )
        else:
            explanations.append(explain_anomaly(payload, items))
    return explanations


def run_demo(settings: Settings | None = None, fleet: FleetSpec | None = None) -> PipelineResult:
    settings = settings or load_settings()
    fleet = fleet or FleetSpec()
    observations = load_synthetic_frame()
    anomalies = detect_anomalies(
        observations,
        window=settings.anomaly_window,
        min_periods=settings.anomaly_min_periods,
        correlation_minutes=settings.correlation_window_minutes,
    )
    stress = compute_stress(
        observations,
        window=settings.anomaly_window,
        min_periods=settings.anomaly_min_periods,
    )
    prices = pivot_series(observations, "spp_usd_per_mwh", "HB_HUBAVG")
    stress_series = stress.set_index("timestamp_utc")["score"] if not stress.empty else pd.Series(dtype=float)
    simulations = compare_strategies(prices, stress_series, fleet)
    warnings = [
        "Demo series SYNTHETIC-STRESS-001 is constructed. It is not ERCOT history.",
    ]
    if settings.data_mode.lower() == "live" and not settings.live_credentials_ready:
        warnings.append("GRIDSIGNAL_DATA_MODE=live but ERCOT credentials are incomplete. Staying on the demo series.")
    wind = observations[(observations["series"] == "wind_gen_mw") & observations["value"].isna()]
    if not wind.empty:
        warnings.append(f"{len(wind)} wind interval(s) are missing and were not filled with zero.")
    return PipelineResult(
        mode="demo",
        scenario_id=SCENARIO_ID,
        synthetic=True,
        observations=observations,
        anomalies=anomalies,
        stress=stress,
        simulations=simulations,
        explanations=_explain_all(anomalies, observations, settings),
        forecast=price_forecast_report(observations),
        warnings=warnings,
        fleet=fleet,
    )


def quality_report(result: PipelineResult) -> dict[str, object]:
    frame = result.observations
    load = frame[(frame["series"] == "load_mw_total") & (frame["location"] == "TOTAL")]
    gaps = missing_hourly_timestamps(load["timestamp_utc"]) if not load.empty else []
    dupes = duplicate_report(frame)
    sources = sorted(frame["source_id"].dropna().unique().tolist()) if not frame.empty else []
    return {
        "mode": result.mode,
        "scenario_id": result.scenario_id,
        "synthetic": result.synthetic,
        "rows": int(len(frame)),
        "sources": sources,
        "duplicate_groups": int(len(dupes)),
        "conflict_groups": int((dupes["status"] == "conflict").sum()) if not dupes.empty else 0,
        "missing_load_hours": [item.isoformat() for item in gaps],
        "missing_values": int(frame["value"].isna().sum()) if not frame.empty else 0,
        "anomaly_count": int(len(result.anomalies)),
        "warnings": result.warnings,
    }
