"""Source status without revealing credentials."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from gridsignal.config import load_settings
from gridsignal.data.source_registry import datasets
from gridsignal.services.pipeline import quality_report
from gridsignal.ui.state import get_result
from gridsignal.ui.theme import synthetic_banner


def render() -> None:
    result = get_result()
    settings = load_settings()
    synthetic_banner("Credential values are not displayed.")
    st.title("Data quality")
    quality = quality_report(result)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mode", str(quality["mode"]))
    c2.metric("Rows", str(quality["rows"]))
    c3.metric("Missing values", str(quality["missing_values"]))
    c4.metric("Duplicate groups", str(quality["duplicate_groups"]))

    st.subheader("API configuration")
    st.write(
        {
            "username": "set" if settings.ercot_username else "missing",
            "password": "set" if settings.ercot_password else "missing",
            "subscription_key": "set" if settings.ercot_subscription_key else "missing",
            "live_ready": settings.live_credentials_ready,
            "requested_mode": settings.data_mode,
            "resolved_mode": result.mode,
        }
    )
    if not settings.ercot_subscription_key:
        st.info(
            "The subscription key is still empty. Register in the API Explorer, open Profile, "
            "and put the Primary key in .env as ERCOT_SUBSCRIPTION_KEY. Do not paste it into chat. "
            "The demo does not need it."
        )

    st.subheader("Registry")
    rows = [
        {
            "product": item.emil_id,
            "name": item.name,
            "mvp": item.mvp,
            "path_status": item.candidate_status,
            "required": item.required_for_mvp,
        }
        for item in datasets()
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.subheader("Forecast check")
    forecast = result.forecast
    st.write(
        f"Seasonal-naive MAE on the demo hub price holdout: {forecast.get('mae')} "
        f"USD/MWh over {forecast.get('holdout_points')} points."
    )
    st.caption(str(forecast.get("claim")))

    st.subheader("Gaps")
    gaps = quality["missing_load_hours"]
    if gaps:
        st.write(gaps)
    else:
        st.write("No missing hourly timestamps in system load.")
    for warning in quality["warnings"]:
        st.write(warning)
