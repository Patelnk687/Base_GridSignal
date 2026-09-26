"""Shared Streamlit session state. Kept out of dashboard.py to avoid import cycles."""

from __future__ import annotations

import streamlit as st

from gridsignal.battery.models import FleetSpec
from gridsignal.config import load_settings
from gridsignal.services.pipeline import PipelineResult, run_demo


def get_result() -> PipelineResult:
    if "result" not in st.session_state:
        st.session_state["settings"] = load_settings()
        st.session_state["fleet"] = FleetSpec()
        st.session_state["result"] = run_demo(st.session_state["settings"], st.session_state["fleet"])
    return st.session_state["result"]


def rerun(fleet: FleetSpec) -> PipelineResult:
    settings = st.session_state.get("settings") or load_settings()
    result = run_demo(settings, fleet)
    st.session_state["fleet"] = fleet
    st.session_state["result"] = result
    return result
