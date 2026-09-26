"""Homogeneous fleet: one physical battery, scaled by count.

Identical batteries on the same strategy take the same action, so the fleet
totals are the single-battery result multiplied by ``count``. That is an
assumption of this simulator, not a claim about a real fleet.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from gridsignal.battery.dispatch import STRATEGIES, DispatchContext
from gridsignal.battery.models import FleetSpec
from gridsignal.battery.simulation import StepResult, apply_setpoint


def local_hour_ending(stamp: pd.Timestamp) -> int:
    local = pd.Timestamp(stamp).tz_convert("America/Chicago")
    return 24 if local.hour == 0 else int(local.hour)


@dataclass
class SimulationResult:
    strategy: str
    uses_future: bool
    steps: pd.DataFrame
    summary: dict[str, object]


def _interval_hours(index: pd.DatetimeIndex) -> list[float]:
    hours = [1.0]
    for previous, current in zip(index[:-1], index[1:], strict=False):
        delta = (current - previous).total_seconds() / 3600.0
        if delta <= 0:
            raise ValueError(f"timestamps are not increasing at {current}")
        hours.append(float(delta))
    return hours


def simulate_fleet(
    strategy_name: str,
    prices: pd.Series,
    stress: pd.Series,
    fleet: FleetSpec | None = None,
) -> SimulationResult:
    if strategy_name not in STRATEGIES:
        raise KeyError(strategy_name)
    fleet = fleet or FleetSpec()
    policy = STRATEGIES[strategy_name]
    index = pd.DatetimeIndex(pd.to_datetime(prices.index, utc=True)).sort_values()
    prices = prices.copy()
    prices.index = pd.to_datetime(prices.index, utc=True)
    stress = stress.reindex(index)
    hours = _interval_hours(index)
    soc = fleet.battery.initial_soc_fraction * fleet.battery.capacity_kwh
    steps: list[StepResult] = []
    uses_future = strategy_name == "oracle_price"
    for stamp, interval_hours in zip(index, hours, strict=True):
        price_value = prices.loc[stamp]
        price = None if pd.isna(price_value) else float(price_value)
        stress_value = stress.loc[stamp]
        stress_score = None if pd.isna(stress_value) else float(stress_value)
        context = DispatchContext(
            timestamp_utc=stamp.to_pydatetime(),
            local_hour_ending=local_hour_ending(stamp),
            price=price,
            prices_through_now=prices.loc[:stamp],
            all_prices=prices,
            stress=stress_score,
            soc_kwh=soc,
            battery=fleet.battery,
        )
        setpoint = policy(context)
        if setpoint.uses_future:
            uses_future = True
        step = apply_setpoint(
            fleet.battery,
            soc,
            setpoint,
            interval_hours,
            timestamp_utc=stamp.to_pydatetime(),
            price=price,
            stress=stress_score,
        )
        soc = step.soc_kwh
        steps.append(step)
    frame = pd.DataFrame([step.__dict__ for step in steps])
    if not frame.empty:
        frame["timestamp_utc"] = pd.to_datetime(frame["timestamp_utc"], utc=True)
        count = fleet.count
        frame["fleet_charge_mw"] = frame["charge_kw"] * count / 1000.0
        frame["fleet_discharge_mw"] = frame["discharge_kw"] * count / 1000.0
        frame["fleet_charge_mwh"] = frame["grid_charge_kwh"] * count / 1000.0
        frame["fleet_discharge_mwh"] = frame["grid_discharge_kwh"] * count / 1000.0
        frame["fleet_soc_mwh"] = frame["soc_kwh"] * count / 1000.0
        frame["fleet_losses_mwh"] = frame["losses_kwh"] * count / 1000.0
        frame["batteries_charging"] = (frame["charge_kw"] > 1e-9).astype(int) * count
        frame["batteries_discharging"] = (frame["discharge_kw"] > 1e-9).astype(int) * count
        frame["batteries_holding"] = count - frame["batteries_charging"] - frame["batteries_discharging"]
    return SimulationResult(
        strategy=strategy_name,
        uses_future=uses_future,
        steps=frame,
        summary=summarize(frame, fleet, uses_future),
    )


def summarize(frame: pd.DataFrame, fleet: FleetSpec, uses_future: bool) -> dict[str, object]:
    if frame.empty:
        return {"strategy_note": "no intervals"}
    charge = float(frame["fleet_charge_mwh"].sum())
    discharge = float(frame["fleet_discharge_mwh"].sum())
    priced = frame.dropna(subset=["price"])
    missing_price_energy = float(
        frame.loc[frame["price"].isna(), "fleet_charge_mwh"].sum()
        + frame.loc[frame["price"].isna(), "fleet_discharge_mwh"].sum()
    )
    cost = float((priced["fleet_charge_mwh"] * priced["price"]).sum())
    value = float((priced["fleet_discharge_mwh"] * priced["price"]).sum())
    throughput_kwh = float((frame["grid_charge_kwh"] + frame["grid_discharge_kwh"]).sum()) * fleet.count
    degradation = throughput_kwh * fleet.battery.degradation_usd_per_kwh
    violations = [item for row in frame["violations"] for item in row]
    return {
        "battery_count": fleet.count,
        "assumption": fleet.battery.assumption_note,
        "uses_future": uses_future,
        "label": "oracle_perfect_foresight" if uses_future else "causal",
        "charge_mwh": round(charge, 6),
        "discharge_mwh": round(discharge, 6),
        "losses_mwh": round(float(frame["fleet_losses_mwh"].sum()), 6),
        "ending_soc_mwh": round(float(frame["fleet_soc_mwh"].iloc[-1]), 6),
        "charging_cost_usd": None if missing_price_energy else round(cost, 2),
        "discharge_value_usd": None if missing_price_energy else round(value, 2),
        "net_energy_value_usd": None if missing_price_energy else round(value - cost - degradation, 2),
        "economics_note": (
            "Illustrative product of simulated MWh and the interval settlement price. "
            "This does not recompute ERCOT prices and does not include a market-impact counterfactual."
        ),
        "constraint_violations": violations,
        "violation_count": len(violations),
    }


def compare_strategies(
    prices: pd.Series,
    stress: pd.Series,
    fleet: FleetSpec | None = None,
) -> dict[str, SimulationResult]:
    return {name: simulate_fleet(name, prices, stress, fleet) for name in STRATEGIES}
