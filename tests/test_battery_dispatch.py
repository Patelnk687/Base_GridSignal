"""Physical battery constraints."""

from datetime import UTC, datetime

import pandas as pd

from gridsignal.battery.dispatch import Action, Setpoint
from gridsignal.battery.metrics import soc_accounting_error
from gridsignal.battery.models import BatterySpec
from gridsignal.battery.simulation import apply_setpoint

UTC = UTC
STAMP = datetime(2024, 7, 15, 12, tzinfo=UTC)


def _spec(**kwargs: float) -> BatterySpec:
    base = dict(
        capacity_kwh=10,
        max_charge_kw=5,
        max_discharge_kw=5,
        min_soc_fraction=0.1,
        max_soc_fraction=1,
        charge_efficiency=0.5,
        discharge_efficiency=0.5,
        reserve_fraction=0.2,
        initial_soc_fraction=0.5,
    )
    base.update(kwargs)
    return BatterySpec(**base)


def test_charge_efficiency_and_power_limit() -> None:
    spec = _spec()
    step = apply_setpoint(
        spec,
        5.0,
        Setpoint(Action.CHARGE, 1.0, "test"),
        1.0,
        timestamp_utc=STAMP,
        price=10,
        stress=0,
    )
    assert step.charge_kw == 5
    assert step.discharge_kw == 0
    assert step.soc_kwh == 5 + 5 * 0.5
    assert step.violations == []


def test_discharge_stops_at_reserve() -> None:
    spec = _spec()
    step = apply_setpoint(
        spec,
        2.5,
        Setpoint(Action.DISCHARGE, 1.0, "test"),
        1.0,
        timestamp_utc=STAMP,
        price=10,
        stress=80,
    )
    assert step.soc_kwh == pytest_reserve(spec)
    assert step.discharge_kw <= spec.max_discharge_kw
    assert step.charge_kw == 0
    assert step.violations == []


def pytest_reserve(spec: BatterySpec) -> float:
    return spec.reserve_kwh


def test_no_simultaneous_charge_and_discharge() -> None:
    spec = _spec()
    step = apply_setpoint(
        spec,
        5,
        Setpoint(Action.CHARGE, 1, "test"),
        1,
        timestamp_utc=STAMP,
        price=None,
        stress=None,
    )
    assert not (step.charge_kw > 0 and step.discharge_kw > 0)


def test_soc_cannot_exceed_capacity() -> None:
    spec = _spec()
    step = apply_setpoint(
        spec,
        9.9,
        Setpoint(Action.CHARGE, 1, "test"),
        1,
        timestamp_utc=STAMP,
        price=1,
        stress=1,
    )
    assert step.soc_kwh <= spec.capacity_kwh + 1e-9
    assert step.violations == []


def test_accounting_over_several_steps() -> None:
    spec = _spec()
    soc = 5.0
    rows = []
    for action in (Action.CHARGE, Action.DISCHARGE, Action.HOLD):
        step = apply_setpoint(
            spec,
            soc,
            Setpoint(action, 1, "test"),
            1,
            timestamp_utc=STAMP,
            price=20,
            stress=10,
        )
        soc = step.soc_kwh
        rows.append(step.__dict__)
    frame = pd.DataFrame(rows)
    assert soc_accounting_error(frame, spec, 5.0) < 1e-6
