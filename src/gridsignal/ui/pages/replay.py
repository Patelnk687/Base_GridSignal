"""Step through the live or synthetic window."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from gridsignal.analytics.features import pivot_series
from gridsignal.services.historical_replay import slice_as_of
from gridsignal.ui.charts import plot, time_series
from gridsignal.ui.state import get_result
from gridsignal.ui.theme import chart_note, mode_banner, why_block


def render() -> None:
    result = get_result()
    mode_banner(
        synthetic=result.synthetic,
        scenario_id=result.scenario_id,
        text=(
            f"{result.scenario_id} is a constructed interval. "
            "A verified ERCOT replay appears here only after a cached pull."
            if result.synthetic
            else f"Replaying cached live window {result.scenario_id}."
        ),
    )
    st.subheader("Replay")
    why_block(
        "<strong>Usability for Base tomorrow:</strong> scrub to any hour and only see what was "
        "knowable then. Anomaly baselines never peek ahead — so this is a decision clock, not a "
        "hindsight chart dump."
    )
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
    plot(
        time_series(
            chart,
            {"load_mw": "Load MW", "wind_mw": "Wind MW", "price": "HB_HUBAVG"},
            "Grid through this interval",
            "mixed units",
        )
    )
    chart_note(
        "What this shows:",
        "Everything through the selected hour only. Load and wind are MW; HB_HUBAVG is $/MWh on the "
        "same axis so you can see timing (not a shared physical scale). If price spikes while wind "
        "drops and load rises, that co-move is the story — not any single line.",
    )

    anomalies = view["anomalies"]
    st.subheader(f"Anomalies through this interval ({len(anomalies)})")
    st.caption("Flags that had already fired by this hour. Later events stay hidden until you scrub forward.")
    if anomalies.empty:
        st.info("None yet.")
    else:
        st.dataframe(
            anomalies[["timestamp_utc", "category", "location", "severity", "explanation"]],
            width="stretch",
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
    plot(
        time_series(
            merged,
            {name: name for name in merged.columns if name != "timestamp_utc"},
            "Fleet SOC",
            "MWh",
        )
    )
    chart_note(
        "What this shows:",
        "Fleet energy stored (MWh) for each strategy up to this hour. Compare who conserved SOC into "
        "the expensive/stressful period versus who idle'd or spent early. Oracle may look better — "
        "it cheated with future prices.",
    )
