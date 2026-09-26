"""Accounting checks for a simulated trajectory."""

from __future__ import annotations

import pandas as pd

from gridsignal.battery.models import BatterySpec


def soc_accounting_error(steps: pd.DataFrame, spec: BatterySpec, initial_soc_kwh: float) -> float:
    soc = initial_soc_kwh
    error = 0.0
    for row in steps.itertuples(index=False):
        stored = float(row.grid_charge_kwh) * spec.charge_efficiency
        removed = float(row.grid_discharge_kwh) / spec.discharge_efficiency
        expected = soc + stored - removed
        error += abs(expected - float(row.soc_kwh))
        soc = float(row.soc_kwh)
    return error


def net_grid_mwh(steps: pd.DataFrame) -> float:
    """Energy delivered to the grid minus energy drawn from the grid, in MWh."""
    return float(steps["fleet_discharge_mwh"].sum() - steps["fleet_charge_mwh"].sum())
