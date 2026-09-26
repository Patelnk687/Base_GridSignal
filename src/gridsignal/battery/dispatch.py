"""Dispatch policies.

Causal policies may use the current interval and earlier intervals.
``oracle_price`` uses the full price series and is labeled as perfect foresight.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

import pandas as pd

from gridsignal.battery.models import BatterySpec


class Action(StrEnum):
    HOLD = "hold"
    CHARGE = "charge"
    DISCHARGE = "discharge"


@dataclass(frozen=True)
class Setpoint:
    action: Action
    power_fraction: float
    rationale: str
    uses_future: bool = False


@dataclass
class DispatchContext:
    timestamp_utc: datetime
    local_hour_ending: int
    price: float | None
    prices_through_now: pd.Series
    all_prices: pd.Series
    stress: float | None
    soc_kwh: float
    battery: BatterySpec


def _quantile_action(price: float, low: float, high: float, ctx: DispatchContext, future: bool) -> Setpoint:
    if high - low < 1.0:
        return Setpoint(Action.HOLD, 0.0, "charge and discharge thresholds are not separated", future)
    if price <= low and ctx.soc_kwh < ctx.battery.max_soc_kwh - 1e-9:
        return Setpoint(Action.CHARGE, 1.0, "price at or below the low threshold", future)
    if price >= high and ctx.soc_kwh > ctx.battery.reserve_kwh + 1e-9:
        return Setpoint(Action.DISCHARGE, 1.0, "price at or above the high threshold", future)
    return Setpoint(Action.HOLD, 0.0, "price is between the charge and discharge thresholds", future)


def idle(_: DispatchContext) -> Setpoint:
    return Setpoint(Action.HOLD, 0.0, "baseline: no dispatch")


def fixed_schedule(ctx: DispatchContext) -> Setpoint:
    if ctx.local_hour_ending in {2, 3, 4, 5}:
        return Setpoint(Action.CHARGE, 1.0, "fixed overnight charge window")
    if ctx.local_hour_ending in {18, 19, 20, 21}:
        return Setpoint(Action.DISCHARGE, 1.0, "fixed evening discharge window")
    return Setpoint(Action.HOLD, 0.0, "outside the fixed schedule")


def price_arbitrage(ctx: DispatchContext) -> Setpoint:
    if ctx.price is None:
        return Setpoint(Action.HOLD, 0.0, "price missing; holding rather than assuming zero")
    known = ctx.prices_through_now.dropna()
    if len(known) < 6:
        return Setpoint(Action.HOLD, 0.0, "fewer than 6 observed prices; holding")
    low = float(known.quantile(0.30))
    high = float(known.quantile(0.70))
    return _quantile_action(ctx.price, low, high, ctx, future=False)


def oracle_price(ctx: DispatchContext) -> Setpoint:
    if ctx.price is None:
        return Setpoint(Action.HOLD, 0.0, "price missing", uses_future=True)
    known = ctx.all_prices.dropna()
    low = float(known.quantile(0.30))
    high = float(known.quantile(0.70))
    decision = _quantile_action(ctx.price, low, high, ctx, future=True)
    return Setpoint(
        decision.action,
        decision.power_fraction,
        "oracle perfect-foresight thresholds. " + decision.rationale,
        uses_future=True,
    )


def grid_stress(ctx: DispatchContext) -> Setpoint:
    if ctx.stress is None:
        return Setpoint(Action.HOLD, 0.0, "stress score missing; holding")
    if ctx.stress >= 70 and ctx.soc_kwh > ctx.battery.reserve_kwh + 1e-9:
        return Setpoint(Action.DISCHARGE, 1.0, "stress at or above 70; discharging above reserve")
    if ctx.stress <= 25 and ctx.soc_kwh < ctx.battery.max_soc_kwh - 1e-9:
        return Setpoint(Action.CHARGE, 1.0, "stress at or below 25; recharging")
    return Setpoint(Action.HOLD, 0.0, "stress is between the charge and discharge bands")


def hybrid(ctx: DispatchContext) -> Setpoint:
    if ctx.stress is not None and ctx.stress >= 70 and ctx.soc_kwh > ctx.battery.reserve_kwh + 1e-9:
        return Setpoint(Action.DISCHARGE, 1.0, "hybrid: stress override discharge")
    price_decision = price_arbitrage(ctx)
    if price_decision.action == Action.DISCHARGE and (ctx.stress is None or ctx.stress < 50):
        return Setpoint(Action.DISCHARGE, 1.0, "hybrid: price discharge while stress is below 50")
    if price_decision.action == Action.CHARGE:
        return Setpoint(Action.CHARGE, 1.0, "hybrid: price charge")
    return Setpoint(Action.HOLD, 0.0, "hybrid: no action")


STRATEGIES = {
    "idle": idle,
    "fixed_schedule": fixed_schedule,
    "price_arbitrage": price_arbitrage,
    "grid_stress": grid_stress,
    "hybrid": hybrid,
    "oracle_price": oracle_price,
}
