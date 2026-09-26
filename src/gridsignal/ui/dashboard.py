"""Page navigation."""

from __future__ import annotations

import streamlit as st

from gridsignal.ui.pages import anomalies, battery_lab, data_quality, overview, replay
from gridsignal.ui.theme import apply_theme


def main() -> None:
    st.set_page_config(
        page_title="GridSignal",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_theme()
    st.sidebar.markdown("**GridSignal**")
    st.sidebar.caption("ERCOT anomalies, evidence, and a virtual battery fleet. Analytical simulation only.")
    navigation = st.navigation(
        [
            st.Page(overview.render, title="Overview", url_path="overview", default=True),
            st.Page(anomalies.render, title="Anomaly Explorer", url_path="anomalies"),
            st.Page(battery_lab.render, title="Battery Lab", url_path="battery"),
            st.Page(replay.render, title="Historical Replay", url_path="replay"),
            st.Page(data_quality.render, title="Data Quality", url_path="quality"),
        ]
    )
    navigation.run()
