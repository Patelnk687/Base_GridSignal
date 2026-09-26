"""Step through the bundled scenario."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from gridsignal.analytics.features import pivot_series
from gridsignal.services.historical_replay import slice_as_of
from gridsignal.ui.charts import time_series
from gridsignal.ui.state import get_result
from gridsignal.ui.theme import synthetic_banner


def render() -> None:
    result = get_result()
    synthetic_banner(
        f"{result.scenario_id} is a constructed interval. "
        "A verified ERCOT replay appears here only after a cached pull."
    )
    st.title("Replay")
    stamps = pd.to_datetime(result.stress["timestamp_utc"], utc=True)
    if stamps.empty:
        st.info("Nothing to replay.")
        return
    labels = [stamp.strftime("%Y-%m-%d %H:%M UTC") for stamp in stamps]
    index = st.slider("Interval", 0, len(labels) - 1, len(labels) - 1, format="%d")
    st.write(labels[index])
    view = slice_as_of(result, stamps.iloc[index])
    current = view["current_stress"]
    if current:
        score = current.get("score")
        st.metric("Stress at this interval", "—" if score is None else f"{score:.0f}")
        st.write(current.get("explanation"))

    observations = view["observations"]
    load = pivot_series(observations, "load_mw_total", "TOTAL").rename("load_mw")
    wind = pivot_series(observations, "wind_gen_mw", "SYSTEM").rename("wind_mw")
    price = pivot_series(observations, "spp_usd_per_mwh", "HB_HUBAVG").rename("price")
    chart = pd.concat([load, wind, price], axis=1).reset_index(names="timestamp_utc")
    st.plotly_chart(
        time_series(
            chart,
            {"load_mw": "Load MW", "wind_mw": "Wind MW", "price": "HB_HUBAVG"},
            "Grid through this interval",
            "mixed units",
        ),
        use_container_width=True,
    )
    st.caption("Load and wind are MW. The price trace is USD/MWh on the same axis for timing, not for a shared scale.")

    anomalies = view["anomalies"]
    st.subheader(f"Anomalies through this interval ({len(anomalies)})")
    if anomalies.empty:
        st.info("None yet.")
    else:
        st.dataframe(
            anomalies[["timestamp_utc", "category", "location", "severity", "explanation"]],
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("Fleet state of charge")
    frames = []
    for name, sim in view["simulations"].items():
        steps = sim["steps"]
        if steps.empty:
            continue
        frames.append(steps[["timestamp_utc", "fleet_soc_mwh"]].rename(columns={"fleet_soc_mwh": name}))
    if not frames:
        st.info("No battery steps yet.")
        return
    merged = frames[0]
    for extra in frames[1:]:
        merged = merged.merge(extra, on="timestamp_utc", how="outer")
    st.plotly_chart(
        time_series(merged, {name: name for name in merged.columns if name != "timestamp_utc"}, "Fleet SOC", "MWh"),
        use_container_width=True,
    )
