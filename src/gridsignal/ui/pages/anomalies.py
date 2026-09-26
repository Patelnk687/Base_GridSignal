"""Filter anomalies and read the evidence-backed explanation."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from gridsignal.explain.evidence import bundle_for_event
from gridsignal.ui.state import get_result
from gridsignal.ui.theme import chart_note, mode_banner, why_block


def render() -> None:
    result = get_result()
    mode_banner(
        synthetic=result.synthetic,
        scenario_id=result.scenario_id,
        text="Anomaly baselines use only earlier intervals. Correlation is not causation.",
    )
    st.subheader("Anomaly explorer")
    why_block(
        "<strong>Non-obvious output:</strong> most ERCOT viewers see a spike. GridSignal names the "
        "series, the past-only baseline, the deviation, and aligned evidence (load/wind/price) with "
        "report IDs. Facts ≠ interpretation ≠ hypothesis — coincidence in time is not cause."
    )
    events = result.anomalies
    if events.empty:
        st.info("No anomalies in this scenario.")
        return

    categories = ["All", *sorted(events["category"].unique())]
    severities = ["All", *sorted(events["severity"].unique())]
    locations = ["All", *sorted(events["location"].astype(str).unique())]
    c1, c2, c3 = st.columns(3)
    category = c1.selectbox("Category", categories)
    severity = c2.selectbox("Severity", severities)
    location = c3.selectbox("Location", locations)
    view = events
    if category != "All":
        view = view[view["category"] == category]
    if severity != "All":
        view = view[view["severity"] == severity]
    if location != "All":
        view = view[view["location"] == location]
    if view.empty:
        st.info("No anomalies match those filters.")
        return

    st.dataframe(
        view[
            [
                "timestamp_utc",
                "location",
                "category",
                "severity",
                "observed",
                "baseline",
                "deviation",
                "modified_z",
            ]
        ],
        width="stretch",
        hide_index=True,
    )
    chart_note(
        "How to read the table:",
        "<em>observed</em> is the live value; <em>baseline</em> is the causal rolling median "
        "(earlier hours only); <em>deviation</em> is the gap; <em>modified_z</em> is robust z vs MAD "
        "(blank/unavailable when the recent window was flat). Pick an event below for the full write-up.",
    )
    labels = [
        f"{pd.Timestamp(row.timestamp_utc).strftime('%m-%d %H:%M')} · {row.category} · {row.location}"
        for row in view.itertuples(index=False)
    ]
    choice = st.selectbox("Event", labels)
    event = view.iloc[labels.index(choice)]
    st.subheader(str(event["category"]).replace("_", " ").title())
    explanation = next(
        (item for item in result.explanations if item.subject_id == event["event_id"]),
        None,
    )
    if explanation is None:
        st.write(event["explanation"])
    else:
        st.markdown("**Facts**")
        for fact in explanation.facts:
            st.write(fact)
        st.markdown("**Interpretation**")
        for line in explanation.interpretation:
            st.write(line)
        st.markdown("**Hypothesis**")
        for line in explanation.hypotheses:
            st.write(line)
        if explanation.missing:
            st.warning("Missing: " + ", ".join(explanation.missing))
    evidence = bundle_for_event(event, result.observations)
    st.subheader("Evidence")
    if not evidence:
        st.info("No aligned measurements at this timestamp.")
        return
    st.dataframe(pd.DataFrame([item.model_dump() for item in evidence]), width="stretch", hide_index=True)
    chart_note(
        "What evidence means:",
        "Other series measured at the same timestamp (with source product IDs). "
        "Use them to see co-moves — e.g. wind down while price up — without calling that causation.",
    )
