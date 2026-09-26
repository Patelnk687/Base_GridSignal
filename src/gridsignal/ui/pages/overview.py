"""Overview: stress, anomalies, and the fleet in one pass."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from gridsignal.analytics.features import pivot_series
from gridsignal.ui.charts import plot, time_series
from gridsignal.ui.state import get_result
from gridsignal.ui.theme import chart_note, mode_banner, pipeline_strip, why_block


def _missed_insight(result) -> str:
    """One non-obvious sentence judges can repeat — computed from this window."""
    hub = pivot_series(result.observations, "spp_usd_per_mwh", "HB_HUBAVG")
    houston = pivot_series(result.observations, "spp_usd_per_mwh", "LZ_HOUSTON")
    load = pivot_series(result.observations, "load_mw_total", "TOTAL")
    wind = pivot_series(result.observations, "wind_gen_mw", "SYSTEM")
    bits: list[str] = []
    if not hub.empty and not houston.empty:
        spread = (houston.reindex(hub.index) - hub).dropna()
        if not spread.empty:
            stamp = spread.abs().idxmax()
            bits.append(
                f"Largest hub-Houston spread is {spread.loc[stamp]:+.1f} $/MWh at "
                f"{pd.Timestamp(stamp).strftime('%m-%d %H:%MZ')} — congestion the hub average alone hides."
            )
    if not load.empty and not wind.empty:
        aligned = pd.concat([load.rename("load"), wind.rename("wind")], axis=1).dropna()
        if len(aligned) >= 12:
            load_z = (aligned["load"] - aligned["load"].rolling(12, min_periods=8).median()) / aligned[
                "load"
            ].rolling(12, min_periods=8).std().replace(0, pd.NA)
            wind_z = (aligned["wind"] - aligned["wind"].rolling(12, min_periods=8).median()) / aligned[
                "wind"
            ].rolling(12, min_periods=8).std().replace(0, pd.NA)
            coincident = aligned[(load_z > 1.5) & (wind_z < -1.5)]
            if not coincident.empty:
                bits.append(
                    f"{len(coincident)} hour(s) show load elevated while wind is depressed vs their own "
                    "recent past — the co-move most single-series dashboards miss."
                )
    cats = result.anomalies["category"].value_counts().to_dict() if not result.anomalies.empty else {}
    if cats:
        top = max(cats, key=cats.get)
        bits.append(f"Dominant anomaly class: {top.replace('_', ' ')} ({cats[top]} events).")
    if not bits:
        return "Scan peak stress, then open Anomaly Explorer for the evidence IDs behind each flag."
    return " ".join(bits[:2])


def render() -> None:
    result = get_result()
    mode_banner(
        synthetic=result.synthetic,
        scenario_id=result.scenario_id,
        text=result.warnings[0] if result.warnings else "Demo mode.",
    )
    st.title("What most people miss in ERCOT's public feeds")
    pipeline_strip()
    why_block(
        "<strong>The problem:</strong> Base reads prices, load, generation, and congestion better than "
        "everyone else. Raw EMIL charts do not say which hours are jointly weird, why, or what a "
        "constrained battery fleet would have done.<br/>"
        "<strong>Our why:</strong> causal anomaly detection (past-only baselines) + evidence-grounded "
        "explanations + virtual fleet strategies on the same clock — offline from a saved week, no "
        "dispatch and no price-impact fairy tales."
    )
    why_block(f"<strong>In this window:</strong> {_missed_insight(result)}")
    for warning in result.warnings[1:]:
        st.warning(warning)

    stress = result.stress.dropna(subset=["score"])
    peak = None if stress.empty else stress.loc[stress["score"].idxmax()]
    latest = None if stress.empty else stress.iloc[-1]
    hybrid = result.simulations["hybrid"].summary
    cols = st.columns(4)
    cols[0].metric(
        "Peak stress (window)",
        "—" if peak is None else f"{peak['score']:.0f}",
        None if peak is None else str(pd.Timestamp(peak["timestamp_utc"]).strftime("%m-%d %H:%MZ")),
    )
    cols[1].metric("Anomalies", str(len(result.anomalies)))
    discharge = hybrid.get("discharge_mwh")
    cols[2].metric(
        "Hybrid discharge",
        "—" if discharge is None else f"{float(discharge):.2f} MWh",
    )
    cols[3].metric(
        "Hybrid net value",
        "—" if hybrid.get("net_energy_value_usd") is None else f"${hybrid['net_energy_value_usd']:,.0f}",
    )
    last_stress = "—"
    if latest is not None and latest["score"] is not None:
        last_stress = f"{latest['score']:.0f}"
    st.caption(
        "Metrics: peak GridSignal stress (0–100, not an ERCOT rating); anomaly count; "
        "hybrid-strategy discharge MWh; ledger dollars = MWh × interval price (not market impact). "
        f"Last-hour stress: {last_stress}."
    )

    load = pivot_series(result.observations, "load_mw_total", "TOTAL").rename("load_mw")
    wind = pivot_series(result.observations, "wind_gen_mw", "SYSTEM").rename("wind_mw")
    solar = pivot_series(result.observations, "solar_gen_mw", "SYSTEM").rename("solar_mw")
    grid = pd.concat([load, wind, solar], axis=1).reset_index(names="timestamp_utc")
    left, right = st.columns(2)
    peak_x = None if peak is None else peak["timestamp_utc"]
    with left:
        plot(
            time_series(
                grid,
                {"load_mw": "Load", "wind_mw": "Wind", "solar_mw": "Solar"},
                "Load and generation",
                "MW",
                marker_x=peak_x,
                marker_label="peak stress",
            )
        )
        chart_note(
            "What this shows:",
            "System load (TOTAL), wind, and solar in MW on one UTC clock. "
            "The dotted marker is the peak stress hour — look for load rising while wind falls. "
            "Source products: NP6-345-CD load, NP4-732-CD wind, NP4-737-CD solar.",
        )
    hub = pivot_series(result.observations, "spp_usd_per_mwh", "HB_HUBAVG").rename("hub")
    houston = pivot_series(result.observations, "spp_usd_per_mwh", "LZ_HOUSTON").rename("houston")
    west = pivot_series(result.observations, "spp_usd_per_mwh", "LZ_WEST").rename("west")
    prices = pd.concat([hub, houston, west], axis=1).reset_index(names="timestamp_utc")
    with right:
        plot(
            time_series(
                prices,
                {"hub": "HB_HUBAVG", "houston": "LZ_HOUSTON", "west": "LZ_WEST"},
                "Settlement prices",
                "USD/MWh",
                marker_x=peak_x,
                marker_label="peak stress",
            )
        )
        chart_note(
            "What this shows:",
            "Real-time settlement point prices ($/MWh). HB_HUBAVG is the hub average; "
            "LZ_HOUSTON / LZ_WEST are load zones. When Houston lifts above the hub, that gap is "
            "congestion — invisible if you only plot one series. NP6-905-CD, hourly means of intervals.",
        )

    stress_chart = result.stress.rename(columns={"score": "stress"}).copy()
    plot(
        time_series(
            stress_chart,
            {"stress": "Stress"},
            "GridSignal Stress Indicator",
            "0–100",
            marker_x=peak_x,
            marker_label="peak",
        )
    )
    chart_note(
        "What this shows:",
        "A project score combining load level/ramp, renewable drop, and price level/change "
        "(weights renormalize when an input is missing — missing ≠ zero). "
        "Not an official ERCOT reliability rating. Read the sentence under the chart for which "
        "components drove the peak hour.",
    )
    if peak is not None:
        st.write(peak["explanation"])

    st.subheader("Highest-severity anomalies")
    st.caption(
        "Each row is an hour that cleared a past-only median/MAD rule (or absolute floor when MAD is 0). "
        "Open Anomaly Explorer for Facts / Interpretation / Hypothesis and evidence IDs."
    )
    if result.anomalies.empty:
        st.info("No anomalies matched the configured thresholds.")
        return
    rank = {"high": 0, "moderate": 1, "low": 2}
    view = result.anomalies.copy()
    view["_rank"] = view["severity"].map(lambda item: rank.get(str(item), 9))
    view = view.sort_values(["_rank", "timestamp_utc"], ascending=[True, False]).head(8)
    st.dataframe(
        view[["timestamp_utc", "location", "category", "severity", "observed", "baseline", "deviation"]],
        width="stretch",
        hide_index=True,
    )
