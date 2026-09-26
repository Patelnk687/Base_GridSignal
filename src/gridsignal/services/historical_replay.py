"""Slice a finished run at a replay instant.

Anomaly baselines were already computed without future rows, so trimming the
display does not change a past event. Oracle battery decisions are still
labeled perfect-foresight even when the chart is sliced.
"""

from __future__ import annotations

import pandas as pd

from gridsignal.services.pipeline import PipelineResult


def slice_as_of(result: PipelineResult, as_of: pd.Timestamp) -> dict[str, object]:
    as_of = pd.Timestamp(as_of)
    if as_of.tzinfo is None:
        as_of = as_of.tz_localize("UTC")
    else:
        as_of = as_of.tz_convert("UTC")

    def _upto(frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty or "timestamp_utc" not in frame.columns:
            return frame
        stamps = pd.to_datetime(frame["timestamp_utc"], utc=True)
        return frame.loc[stamps <= as_of].copy()

    observations = _upto(result.observations)
    anomalies = _upto(result.anomalies)
    stress = _upto(result.stress)
    simulations = {}
    for name, sim in result.simulations.items():
        steps = _upto(sim.steps)
        simulations[name] = {
            "uses_future": sim.uses_future,
            "steps": steps,
            "ending_soc_mwh": None if steps.empty else float(steps["fleet_soc_mwh"].iloc[-1]),
            "charge_mwh": 0.0 if steps.empty else float(steps["fleet_charge_mwh"].sum()),
            "discharge_mwh": 0.0 if steps.empty else float(steps["fleet_discharge_mwh"].sum()),
        }
    current_stress = None if stress.empty else stress.iloc[-1].to_dict()
    return {
        "as_of": as_of,
        "observations": observations,
        "anomalies": anomalies,
        "stress": stress,
        "current_stress": current_stress,
        "simulations": simulations,
    }
