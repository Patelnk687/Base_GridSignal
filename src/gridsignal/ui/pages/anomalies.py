"""Filter anomalies and read the evidence-backed explanation."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from gridsignal.explain.evidence import bundle_for_event
from gridsignal.ui.state import get_result
from gridsignal.ui.theme import synthetic_banner


def render() -> None:
    result = get_result()
    synthetic_banner("Anomaly baselines use only earlier intervals. Correlation is not causation.")
    st.title("Anomaly explorer")
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
        view[["timestamp_utc", "location", "category", "severity", "observed", "baseline", "deviation", "modified_z"]],
        use_container_width=True,
        hide_index=True,
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
    st.dataframe(pd.DataFrame([item.model_dump() for item in evidence]), use_container_width=True, hide_index=True)
