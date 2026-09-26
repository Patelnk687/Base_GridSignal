"""Configure the virtual fleet and compare strategies."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from gridsignal.battery.models import BatterySpec, FleetSpec
from gridsignal.ui.charts import plot, time_series
from gridsignal.ui.state import get_result, rerun
from gridsignal.ui.theme import chart_note, mode_banner, why_block


def render() -> None:
    result = get_result()
    mode_banner(
        synthetic=result.synthetic,
        scenario_id=result.scenario_id,
        text="Battery behavior is simulated. Nothing is dispatched to the ERCOT grid.",
    )
    st.subheader("Battery lab")
    why_block(
        "<strong>What most people miss:</strong> a price spike chart does not tell you whether a "
        "physically constrained fleet could have discharged into it. Compare <em>idle</em> (do nothing), "
        "causal price/stress policies, and an <em>oracle</em> that peeks at future prices — the gap is "
        "foresight value, not a claim the fleet moved ERCOT prices."
    )
    st.caption(result.fleet.battery.assumption_note)

    with st.form("gs_battery_lab_form_v3"):
        c1, c2, c3 = st.columns(3)
        count = c1.number_input(
            "Batteries",
            min_value=1,
            max_value=100000,
            value=int(result.fleet.count),
            step=100,
            key="gs_batt_count",
        )
        capacity = c2.number_input(
            "Capacity (kWh)",
            min_value=1.0,
            value=float(result.fleet.battery.capacity_kwh),
            key="gs_batt_capacity",
        )
        charge_kw = c3.number_input(
            "Max charge (kW)",
            min_value=0.1,
            value=float(result.fleet.battery.max_charge_kw),
            key="gs_batt_charge_kw",
        )
        discharge_kw = c1.number_input(
            "Max discharge (kW)",
            min_value=0.1,
            value=float(result.fleet.battery.max_discharge_kw),
            key="gs_batt_discharge_kw",
        )
        # Keep sliders inside BatterySpec bounds (min SOC floor is 0.10).
        initial = c2.slider(
            "Initial SOC",
            0.10,
            1.0,
            float(result.fleet.battery.initial_soc_fraction),
            key="gs_batt_initial_soc",
        )
        reserve = c3.slider(
            "Reserve SOC",
            0.10,
            1.0,
            float(result.fleet.battery.reserve_fraction),
            key="gs_batt_reserve_soc",
        )
        efficiency = c1.slider(
            "One-way efficiency",
            0.5,
            1.0,
            float(result.fleet.battery.charge_efficiency),
            key="gs_batt_efficiency",
        )
        degradation = c2.number_input(
            "Degradation ($/kWh throughput)",
            min_value=0.0,
            value=float(result.fleet.battery.degradation_usd_per_kwh),
            step=0.01,
            key="gs_batt_degradation",
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
                    degradation_usd_per_kwh=float(degradation),
                ),
            )
        except Exception as exc:
            st.error(str(exc))
            return
        rerun(fleet)
        st.rerun()

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
    available = [column for column in show if column in table.columns]
    st.subheader("Strategy comparison")
    st.dataframe(table[available], width="stretch", hide_index=True)
    chart_note(
        "How to read the table:",
        "Each row is one dispatch policy on the same price/stress series. "
        "<code>label=causal</code> means decisions use only past data; "
        "<code>oracle_perfect_foresight</code> peeks ahead (benchmark only). "
        "Net value = discharge MWh × price − charge MWh × price − optional degradation. "
        "Violation count must stay 0 (SOC, power, no simultaneous charge/discharge).",
    )
    note = table.iloc[0].get("economics_note") if not table.empty else None
    if note:
        st.caption(str(note))

    strategy = st.selectbox("Strategy timeline", list(result.simulations))
    sim = result.simulations[strategy]
    if sim.uses_future:
        st.warning("This strategy is an oracle perfect-foresight benchmark. It uses prices from later intervals.")
    steps = sim.steps.copy()
    if steps.empty:
        st.info("No price intervals available for this fleet run.")
        return
    steps["soc_pct"] = steps["soc_kwh"] / result.fleet.battery.capacity_kwh * 100
    left, right = st.columns(2)
    with left:
        plot(
            time_series(
                steps,
                {"fleet_charge_mw": "Charge", "fleet_discharge_mw": "Discharge"},
                f"{strategy} fleet power",
                "MW",
            )
        )
        chart_note(
            "What this shows:",
            "Fleet grid charge MW (into batteries) and discharge MW (to the grid) over time. "
            "They never overlap in the same hour — the simulator forbids simultaneous charge/discharge.",
        )
    with right:
        plot(time_series(steps, {"soc_pct": "State of charge"}, f"{strategy} state of charge", "%"))
        chart_note(
            "What this shows:",
            "State of charge as % of pack capacity. Watch whether the policy held energy into expensive "
            "or high-stress hours, or spent SOC too early. Efficiency losses appear as SOC drop without "
            "full discharge credit.",
        )
    violations = sim.summary.get("violation_count", 0)
    if violations:
        st.error(f"{violations} constraint violation(s).")
    else:
        st.success("No state-of-charge, power, or simultaneous charge/discharge violations in this run.")
