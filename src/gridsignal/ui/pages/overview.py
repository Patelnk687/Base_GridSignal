"""Overview: stress, anomalies, and the fleet in one pass."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from gridsignal.analytics.features import pivot_series
from gridsignal.ui.charts import time_series
from gridsignal.ui.state import get_result
from gridsignal.ui.theme import synthetic_banner


def render() -> None:
    result = get_result()
    synthetic_banner(result.warnings[0] if result.warnings else "Demo mode.")
    st.title("Grid conditions and a virtual fleet")
    for warning in result.warnings[1:]:
        st.warning(warning)

    stress = result.stress.dropna(subset=["score"])
    latest = None if stress.empty else stress.iloc[-1]
    hybrid = result.simulations["hybrid"].summary
    cols = st.columns(4)
    cols[0].metric(
        "GridSignal stress",
        "—" if latest is None else f"{latest['score']:.0f}",
        None if latest is None or latest["trend"] is None else f"{latest['trend']:+.0f} vs prior hour",
    )
    cols[1].metric("Anomalies", str(len(result.anomalies)))
    cols[2].metric(
        "Hybrid discharge",
        f"{hybrid['discharge_mwh']:.2f} MWh",
    )
    cols[3].metric(
        "Hybrid net value",
        "—" if hybrid["net_energy_value_usd"] is None else f"${hybrid['net_energy_value_usd']:,.0f}",
    )
    st.caption(
        "Stress is a GridSignal score, not an ERCOT rating. "
        "Dollars are simulated MWh times the interval price. They are not a market-price impact."
    )

    load = pivot_series(result.observations, "load_mw_total", "TOTAL").rename("load_mw")
    wind = pivot_series(result.observations, "wind_gen_mw", "SYSTEM").rename("wind_mw")
    solar = pivot_series(result.observations, "solar_gen_mw", "SYSTEM").rename("solar_mw")
    grid = pd.concat([load, wind, solar], axis=1).reset_index(names="timestamp_utc")
    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            time_series(
                grid,
                {"load_mw": "Load", "wind_mw": "Wind", "solar_mw": "Solar"},
                "Load and generation",
                "MW",
            ),
            use_container_width=True,
        )
    hub = pivot_series(result.observations, "spp_usd_per_mwh", "HB_HUBAVG").rename("hub")
    houston = pivot_series(result.observations, "spp_usd_per_mwh", "LZ_HOUSTON").rename("houston")
    west = pivot_series(result.observations, "spp_usd_per_mwh", "LZ_WEST").rename("west")
    prices = pd.concat([hub, houston, west], axis=1).reset_index(names="timestamp_utc")
    with right:
        st.plotly_chart(
            time_series(
                prices,
                {"hub": "HB_HUBAVG", "houston": "LZ_HOUSTON", "west": "LZ_WEST"},
                "Settlement prices",
                "USD/MWh",
            ),
            use_container_width=True,
        )

    stress_chart = result.stress.rename(columns={"score": "stress"}).copy()
    st.plotly_chart(
        time_series(stress_chart, {"stress": "Stress"}, "GridSignal Stress Indicator", "0–100"),
        use_container_width=True,
    )
    if latest is not None:
        st.write(latest["explanation"])

    st.subheader("Recent anomalies")
    if result.anomalies.empty:
        st.info("No anomalies matched the configured thresholds.")
        return
    view = result.anomalies[
        ["timestamp_utc", "location", "category", "severity", "observed", "baseline", "deviation"]
    ].tail(8)
    st.dataframe(view, use_container_width=True, hide_index=True)
