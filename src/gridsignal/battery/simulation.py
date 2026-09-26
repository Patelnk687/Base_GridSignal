"""Single-battery step. The simulator, not the strategy, enforces physics."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from gridsignal.battery.dispatch import Action, Setpoint
from gridsignal.battery.models import BatterySpec


@dataclass
class StepResult:
    timestamp_utc: datetime
    interval_hours: float
    action: str
    charge_kw: float
    discharge_kw: float
    grid_charge_kwh: float
    grid_discharge_kwh: float
    soc_kwh: float
    losses_kwh: float
    price: float | None
    stress: float | None
    rationale: str
    uses_future: bool
    violations: list[str] = field(default_factory=list)


def apply_setpoint(
    spec: BatterySpec,
    soc_kwh: float,
    setpoint: Setpoint,
    hours: float,
    *,
    timestamp_utc: datetime,
    price: float | None,
    stress: float | None,
) -> StepResult:
    if hours <= 0:
        raise ValueError("interval length must be positive")
    fraction = min(1.0, max(0.0, setpoint.power_fraction))
    charge_kw = spec.max_charge_kw * fraction if setpoint.action == Action.CHARGE else 0.0
    discharge_kw = spec.max_discharge_kw * fraction if setpoint.action == Action.DISCHARGE else 0.0
    if charge_kw > 0 and discharge_kw > 0:
        raise ValueError("strategy requested charge and discharge together")

    grid_charge_kwh = charge_kw * hours
    stored_kwh = grid_charge_kwh * spec.charge_efficiency
    room = spec.max_soc_kwh - soc_kwh
    if stored_kwh > room:
        stored_kwh = max(room, 0.0)
        grid_charge_kwh = stored_kwh / spec.charge_efficiency
        charge_kw = grid_charge_kwh / hours

    grid_discharge_kwh = discharge_kw * hours
    removed_kwh = grid_discharge_kwh / spec.discharge_efficiency
    available = soc_kwh - spec.reserve_kwh
    if removed_kwh > available:
        removed_kwh = max(available, 0.0)
        grid_discharge_kwh = removed_kwh * spec.discharge_efficiency
        discharge_kw = grid_discharge_kwh / hours

    new_soc = soc_kwh + stored_kwh - removed_kwh
    losses = (grid_charge_kwh - stored_kwh) + (removed_kwh - grid_discharge_kwh)
    violations: list[str] = []
    if charge_kw - spec.max_charge_kw > 1e-6 or discharge_kw - spec.max_discharge_kw > 1e-6:
        violations.append("power_limit")
    if charge_kw > 1e-9 and discharge_kw > 1e-9:
        violations.append("simultaneous_charge_discharge")
    if new_soc < spec.min_soc_kwh - 1e-6 or new_soc > spec.max_soc_kwh + 1e-6:
        violations.append("soc_bounds")
    expected = soc_kwh + stored_kwh - removed_kwh
    if abs(new_soc - expected) > 1e-6:
        violations.append("energy_balance")
    return StepResult(
        timestamp_utc=timestamp_utc,
        interval_hours=hours,
        action=setpoint.action.value if charge_kw + discharge_kw > 1e-9 else Action.HOLD.value,
        charge_kw=charge_kw,
        discharge_kw=discharge_kw,
        grid_charge_kwh=grid_charge_kwh,
        grid_discharge_kwh=grid_discharge_kwh,
        soc_kwh=new_soc,
        losses_kwh=losses,
        price=price,
        stress=stress,
        rationale=setpoint.rationale,
        uses_future=setpoint.uses_future,
        violations=violations,
    )
