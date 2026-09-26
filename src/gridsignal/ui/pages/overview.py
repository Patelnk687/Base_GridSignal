"""Overview: stress, anomalies, and the fleet in one pass."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from gridsignal.analytics.features import pivot_series
from gridsignal.ui.charts import plot, spread_series, time_series
from gridsignal.ui.insights import build_insight_cards
from gridsignal.ui.state import get_result
from gridsignal.ui.theme import chart_note, hero_block, insight_cards, mode_banner, pipeline_strip, severity_pill, why_block


def render() -> None:
    result = get_result()
    mode_banner(
        synthetic=result.synthetic,
        scenario_id=result.scenario_id,
        text=result.warnings[0] if result.warnings else "Demo mode.",
    )
    hero_block(
        "What most people miss in ERCOT's public feeds",
        "Co-moving odd hours, hub–zone congestion gaps, and what a constrained virtual battery fleet "
        "would have done on the same clock — with evidence IDs, not vibes.",
    )
    pipeline_strip()
    why_block(
        "<strong>The problem:</strong> Base reads prices, load, generation, and congestion better than "
        "everyone else. Raw EMIL charts do not say which hours are jointly weird, why, or what a "
        "constrained battery fleet would have done.<br/>"
        "<strong>Our why:</strong> causal anomaly detection (past-only baselines) + evidence-grounded "
        "explanations + virtual fleet strategies — offline from a saved week."
    )

    cards = build_insight_cards(result)
    if cards:
        st.subheader("Signals in this window")
        insight_cards(cards)

    for warning in result.warnings[1:]:
        st.warning(warning)

    stress = result.stress.dropna(subset=["score"])
    peak = None if stress.empty else stress.loc[stress["score"].idxmax()]
    latest = None if stress.empty else stress.iloc[-1]
    hybrid = result.simulations["hybrid"].summary
    idle = result.simulations["idle"].summary
    cols = st.columns(4)
    cols[0].metric(
        "Peak stress",
        "—" if peak is None else f"{peak['score']:.0f}",
        None if peak is None else str(pd.Timestamp(peak["timestamp_utc"]).strftime("%m-%d %H:%MZ")),
    )
    cols[1].metric("Anomalies", str(len(result.anomalies)))
    discharge = hybrid.get("discharge_mwh")
    cols[2].metric(
        "Hybrid discharge",
        "—" if discharge is None else f"{float(discharge):.2f} MWh",
    )
    hybrid_val = hybrid.get("net_energy_value_usd")
    idle_val = idle.get("net_energy_value_usd")
    delta = None
    if hybrid_val is not None and idle_val is not None:
        delta = f"{float(hybrid_val) - float(idle_val):+,.0f} vs idle"
    cols[3].metric(
        "Hybrid net value",
        "—" if hybrid_val is None else f"${float(hybrid_val):,.0f}",
        delta,
    )
    last_stress = "—"
    if latest is not None and latest["score"] is not None:
        last_stress = f"{latest['score']:.0f}"
    st.caption(
        "Peak GridSignal stress is 0–100 (not an ERCOT rating). "
        "Dollars are MWh × interval price — not market impact. "
        f"Last-hour stress: {last_stress}."
    )

    load = pivot_series(result.observations, "load_mw_total", "TOTAL").rename("load_mw")
    wind = pivot_series(result.observations, "wind_gen_mw", "SYSTEM").rename("wind_mw")
    solar = pivot_series(result.observations, "solar_gen_mw", "SYSTEM").rename("solar_mw")
    grid = pd.concat([load, wind, solar], axis=1).rename_axis("timestamp_utc").reset_index()
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
                fill_first=True,
            )
        )
        chart_note(
            "What this shows:",
            "System load (filled), wind, and solar in MW. Dotted line = peak stress hour — "
            "watch load rise while wind falls. Sources: NP6-345-CD, NP4-732-CD, NP4-737-CD.",
        )
    hub = pivot_series(result.observations, "spp_usd_per_mwh", "HB_HUBAVG").rename("hub")
    houston = pivot_series(result.observations, "spp_usd_per_mwh", "LZ_HOUSTON").rename("houston")
    west = pivot_series(result.observations, "spp_usd_per_mwh", "LZ_WEST").rename("west")
    prices = pd.concat([hub, houston, west], axis=1).rename_axis("timestamp_utc").reset_index()
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
            "Hub vs load-zone prices ($/MWh). When Houston lifts off the hub, that is congestion "
            "texture a single-series chart never shows. NP6-905-CD hourly means.",
        )

    if not hub.empty and not houston.empty:
        spread = (
            (houston.reindex(hub.index) - hub)
            .dropna()
            .rename("spread")
            .rename_axis("timestamp_utc")
            .reset_index()
        )
        plot(spread_series(spread, "spread", "Houston − hub spread (congestion tell)", marker_x=peak_x))
        chart_note(
            "What this shows:",
            "Signed $/MWh gap. Above zero = Houston richer than the hub (typical binding path into the coast). "
            "Below zero = Houston cheaper. This is often what operators mean by 'the hub lied.'",
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
            fill_first=True,
        )
    )
    chart_note(
        "What this shows:",
        "Composite 0–100 from load level/ramp, renewable drop, price level/change. "
        "Missing inputs are dropped (never treated as zero). Not an official ERCOT rating.",
    )
    if peak is not None:
        st.info(peak["explanation"])

    st.subheader("Highest-severity anomalies")
    st.caption("Past-only baselines. Open Anomaly Explorer for Facts / Interpretation / Hypothesis.")
    if result.anomalies.empty:
        st.info("No anomalies matched the configured thresholds.")
        return
    rank = {"high": 0, "moderate": 1, "low": 2}
    view = result.anomalies.copy()
    view["_rank"] = view["severity"].map(lambda item: rank.get(str(item), 9))
    view = view.sort_values(["_rank", "timestamp_utc"], ascending=[True, False]).head(8)
    html_rows = []
    for row in view.itertuples(index=False):
        html_rows.append(
            "<tr>"
            f"<td>{pd.Timestamp(row.timestamp_utc).strftime('%m-%d %H:%MZ')}</td>"
            f"<td>{row.location}</td>"
            f"<td>{str(row.category).replace('_', ' ')}</td>"
            f"<td>{severity_pill(str(row.severity))}</td>"
            f"<td>{float(row.observed):,.1f}</td>"
            f"<td>{float(row.baseline):,.1f}</td>"
            f"<td>{float(row.deviation):+,.1f}</td>"
            "</tr>"
        )
    st.markdown(
        "<div class='gs-scroll-table'>"
        "<table style='width:100%; border-collapse:collapse; font-size:0.9rem;'>"
        "<thead><tr>"
        "<th align='left'>Time</th><th align='left'>Location</th><th align='left'>Category</th>"
        "<th align='left'>Severity</th><th align='right'>Observed</th>"
        "<th align='right'>Baseline</th><th align='right'>Deviation</th>"
        "</tr></thead><tbody>"
        + "".join(html_rows)
        + "</tbody></table></div>",
        unsafe_allow_html=True,
    )
