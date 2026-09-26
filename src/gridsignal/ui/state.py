"""Shared Streamlit session state. Kept out of dashboard.py to avoid import cycles."""

from __future__ import annotations

import streamlit as st

from gridsignal.battery.models import FleetSpec
from gridsignal.config import load_settings
from gridsignal.services.pipeline import PipelineResult, run_pipeline


def get_result() -> PipelineResult:
    if "result" not in st.session_state:
        settings = load_settings()
        fleet = FleetSpec()
        st.session_state["settings"] = settings
        st.session_state["fleet"] = fleet
        mode = settings.resolved_mode
        if mode == "live":
            message = "Pulling live ERCOT data (past week) and saving a local snapshot…"
        elif mode == "snapshot":
            message = "Loading saved ERCOT week snapshot…"
        else:
            message = "Loading synthetic demo scenario…"
        with st.spinner(message):
            st.session_state["result"] = run_pipeline(settings, fleet)
    return st.session_state["result"]


def rerun(fleet: FleetSpec) -> PipelineResult:
    settings = st.session_state.get("settings") or load_settings()
    with st.spinner("Re-running fleet strategies…"):
        result = run_pipeline(settings, fleet)
    st.session_state["fleet"] = fleet
    st.session_state["result"] = result
    return result
