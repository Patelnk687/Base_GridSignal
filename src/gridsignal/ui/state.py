"""Shared Streamlit session state. Kept out of dashboard.py to avoid import cycles."""

from __future__ import annotations

import streamlit as st

from gridsignal.battery.models import FleetSpec
from gridsignal.config import load_settings
from gridsignal.services.pipeline import PipelineResult, reanalyze, run_pipeline

# Old builds used st.form("fleet") and st.session_state["fleet"] together, which
# corrupts Streamlit widget state. Never reuse the bare key "fleet".
_FORBIDDEN_PREFIXES = ("FormSubmitter:fleet-", "fleet-")
_FORBIDDEN_KEYS = frozenset({"fleet"})


def purge_stale_widget_keys() -> None:
    """Drop leftover keys from the old form/session naming before any page runs."""
    for key in list(st.session_state.keys()):
        text = str(key)
        if text in _FORBIDDEN_KEYS or text.startswith(_FORBIDDEN_PREFIXES):
            del st.session_state[key]


def get_result() -> PipelineResult:
    if "gs_pipeline_result" not in st.session_state:
        settings = load_settings()
        fleet = FleetSpec()
        st.session_state["gs_settings"] = settings
        mode = settings.resolved_mode
        if mode == "live":
            message = "Pulling live ERCOT data (past week) and saving a local snapshot…"
        elif mode == "snapshot":
            message = "Loading saved ERCOT week snapshot…"
        else:
            message = "Loading synthetic demo scenario…"
        with st.spinner(message):
            st.session_state["gs_pipeline_result"] = run_pipeline(settings, fleet)
    return st.session_state["gs_pipeline_result"]


def clear_pipeline_cache() -> None:
    """Force the next page render to reload demo / snapshot / live data."""
    st.session_state.pop("gs_pipeline_result", None)
    st.session_state.pop("gs_settings", None)


def rerun(fleet: FleetSpec) -> PipelineResult:
    """Rebuild strategies for a new fleet without re-fetching ERCOT."""
    previous = st.session_state.get("gs_pipeline_result")
    settings = st.session_state.get("gs_settings") or load_settings()
    with st.spinner("Re-running fleet strategies…"):
        if previous is not None and not previous.observations.empty:
            result = reanalyze(previous, fleet, settings)
        else:
            result = run_pipeline(settings, fleet)
    st.session_state["gs_pipeline_result"] = result
    return result
