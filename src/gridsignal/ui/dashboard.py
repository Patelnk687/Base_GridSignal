"""Page navigation."""

from __future__ import annotations

import streamlit as st

from gridsignal.ui.pages import anomalies, battery_lab, data_quality, overview, replay
from gridsignal.ui.theme import appearance_toggle, apply_theme, render_main_brand, render_sidebar_brand
from gridsignal.ui.state import purge_stale_widget_keys


def main() -> None:
    st.set_page_config(
        page_title="GridSignal",
        page_icon="⚡",
        layout="wide",
        # Collapses sidebar on phones so the main charts get the first viewport.
        initial_sidebar_state="auto",
    )
    purge_stale_widget_keys()
    # Toggle first so apply_theme reads the chosen appearance.
    render_sidebar_brand()
    appearance_toggle()
    apply_theme()
    st.sidebar.divider()
    st.sidebar.markdown("**5-minute demo path**")
    st.sidebar.caption(
        "1) Overview peak stress · 2) Anomaly facts/evidence · "
        "3) Battery idle vs hybrid vs oracle · 4) Replay scrub · 5) Data quality / snapshot."
    )
    st.sidebar.caption(
        "Offline: GRIDSIGNAL_DATA_MODE=snapshot after "
        "`python -m gridsignal.tools.refresh_live_snapshot`."
    )
    render_main_brand()
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
