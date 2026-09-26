"""Fleet totals and strategy labels."""

import pandas as pd

from gridsignal.battery.fleet import compare_strategies, simulate_fleet
from gridsignal.battery.metrics import net_grid_mwh
from gridsignal.battery.models import BatterySpec, FleetSpec
from gridsignal.config import load_settings
from gridsignal.services.pipeline import run_demo


def test_fleet_scales_and_balances() -> None:
    index = pd.date_range("2024-07-15", periods=12, freq="h", tz="UTC")
    prices = pd.Series(20.0, index=index)
    prices.iloc[-1] = 300
    stress = pd.Series(10.0, index=index)
    stress.iloc[-1] = 90
    fleet = FleetSpec(
        count=10,
        battery=BatterySpec(capacity_kwh=10, max_charge_kw=2, max_discharge_kw=2, initial_soc_fraction=0.8),
    )
    result = simulate_fleet("grid_stress", prices, stress, fleet)
    assert result.summary["violation_count"] == 0
    assert result.summary["label"] == "causal"
    one = simulate_fleet("grid_stress", prices, stress, FleetSpec(count=1, battery=fleet.battery))
    assert abs(result.summary["discharge_mwh"] - 10 * one.summary["discharge_mwh"]) < 1e-6
    assert abs(net_grid_mwh(result.steps) - (result.summary["discharge_mwh"] - result.summary["charge_mwh"])) < 1e-5


def test_oracle_is_labeled_and_idle_does_nothing() -> None:
    index = pd.date_range("2024-07-15", periods=8, freq="h", tz="UTC")
    prices = pd.Series([10, 10, 10, 10, 80, 10, 10, 90], index=index, dtype=float)
    stress = pd.Series(0.0, index=index)
    compared = compare_strategies(prices, stress, FleetSpec(count=2))
    assert compared["oracle_price"].uses_future
    assert compared["oracle_price"].summary["label"] == "oracle_perfect_foresight"
    assert compared["idle"].summary["charge_mwh"] == 0
    assert compared["idle"].summary["discharge_mwh"] == 0
    assert compared["price_arbitrage"].uses_future is False


def test_demo_replay_is_reproducible() -> None:
    settings = load_settings(_env_file=None, data_mode="demo")
    first = run_demo(settings)
    second = run_demo(settings)
    assert first.anomalies["event_id"].tolist() == second.anomalies["event_id"].tolist()
    assert first.simulations["hybrid"].summary["discharge_mwh"] == second.simulations["hybrid"].summary["discharge_mwh"]
