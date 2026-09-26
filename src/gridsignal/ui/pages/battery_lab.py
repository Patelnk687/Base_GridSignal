"""Configure the virtual fleet and compare strategies."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from gridsignal.battery.models import BatterySpec, FleetSpec
from gridsignal.ui.charts import time_series
from gridsignal.ui.state import get_result, rerun
from gridsignal.ui.theme import synthetic_banner


def render() -> None:
    result = get_result()
    synthetic_banner("Battery behavior is simulated. Nothing is dispatched to the ERCOT grid.")
    st.title("Battery lab")
    st.caption(result.fleet.battery.assumption_note)

    with st.form("fleet"):
        c1, c2, c3 = st.columns(3)
        count = c1.number_input("Batteries", min_value=1, max_value=100000, value=result.fleet.count, step=100)
        capacity = c2.number_input("Capacity (kWh)", min_value=1.0, value=float(result.fleet.battery.capacity_kwh))
        charge_kw = c3.number_input("Max charge (kW)", min_value=0.1, value=float(result.fleet.battery.max_charge_kw))
        discharge_kw = c1.number_input(
            "Max discharge (kW)", min_value=0.1, value=float(result.fleet.battery.max_discharge_kw)
        )
        initial = c2.slider("Initial SOC", 0.1, 1.0, float(result.fleet.battery.initial_soc_fraction))
        reserve = c3.slider("Reserve SOC", 0.0, 1.0, float(result.fleet.battery.reserve_fraction))
        efficiency = c1.slider("One-way efficiency", 0.5, 1.0, float(result.fleet.battery.charge_efficiency))
        degradation = c2.number_input(
            "Degradation ($/kWh throughput)",
            min_value=0.0,
            value=float(result.fleet.battery.degradation_usd_per_kwh),
            step=0.01,
        )
        submitted = st.form_submit_button("Run fleet")
    if submitted:
        try:
            fleet = FleetSpec(
                count=int(count),
                battery=BatterySpec(
                    capacity_kwh=float(capacity),
                    max_charge_kw=float(charge_kw),
                    max_discharge_kw=float(discharge_kw),
                    initial_soc_fraction=float(initial),
                    reserve_fraction=float(reserve),
                    charge_efficiency=float(efficiency),
                    discharge_efficiency=float(efficiency),
                ),
            )
            fleet.battery.degradation_usd_per_kwh = float(degradation)
        except ValueError as exc:
            st.error(str(exc))
            return
        result = rerun(fleet)

    rows = []
    for name, sim in result.simulations.items():
        summary = dict(sim.summary)
        summary["strategy"] = name
        rows.append(summary)
    table = pd.DataFrame(rows)
    show = [
        "strategy",
        "label",
        "charge_mwh",
        "discharge_mwh",
        "losses_mwh",
        "ending_soc_mwh",
        "charging_cost_usd",
        "discharge_value_usd",
        "net_energy_value_usd",
        "violation_count",
    ]
    st.dataframe(table[show], use_container_width=True, hide_index=True)
    st.caption(table.iloc[0]["economics_note"])

    strategy = st.selectbox("Strategy timeline", list(result.simulations))
    sim = result.simulations[strategy]
    if sim.uses_future:
        st.warning("This strategy is an oracle perfect-foresight benchmark. It uses prices from later intervals.")
    steps = sim.steps.copy()
    steps["soc_pct"] = steps["soc_kwh"] / result.fleet.battery.capacity_kwh * 100
    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            time_series(
                steps,
                {"fleet_charge_mw": "Charge", "fleet_discharge_mw": "Discharge"},
                f"{strategy} fleet power",
                "MW",
            ),
            use_container_width=True,
        )
    with right:
        st.plotly_chart(
            time_series(steps, {"soc_pct": "State of charge"}, f"{strategy} state of charge", "%"),
            use_container_width=True,
        )
    violations = sim.summary["violation_count"]
    if violations:
        st.error(f"{violations} constraint violation(s).")
    else:
        st.success("No state-of-charge, power, or simultaneous charge/discharge violations in this run.")
