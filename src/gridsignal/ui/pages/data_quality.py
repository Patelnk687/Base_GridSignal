"""Source status without revealing credentials."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from gridsignal.config import load_settings
from gridsignal.data.snapshot import snapshot_exists, snapshot_paths
from gridsignal.data.source_registry import datasets
from gridsignal.services.pipeline import quality_report
from gridsignal.ui.state import get_result
from gridsignal.ui.theme import mode_banner, why_block


def render() -> None:
    result = get_result()
    settings = load_settings()
    mode_banner(
        synthetic=result.synthetic,
        scenario_id=result.scenario_id,
        text="Credential values are not displayed.",
    )
    st.title("Data quality")
    why_block(
        "<strong>Use it tomorrow:</strong> refresh once with "
        "<code>python -m gridsignal.tools.refresh_live_snapshot</code>, "
        "then set <code>GRIDSIGNAL_DATA_MODE=snapshot</code> for offline demos. "
        "Missing values stay null — never filled with zero."
    )
    quality = quality_report(result)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mode", str(quality["mode"]))
    c2.metric("Rows", str(quality["rows"]))
    c3.metric("Missing values", str(quality["missing_values"]))
    c4.metric("Duplicate groups", str(quality["duplicate_groups"]))

    obs_path, meta_path = snapshot_paths(settings.snapshot_dir)
    st.subheader("Offline snapshot")
    st.write(
        {
            "snapshot_present": snapshot_exists(settings.snapshot_dir),
            "observations_path": str(obs_path),
            "meta_path": str(meta_path),
            "lookback_days": settings.live_lookback_days,
        }
    )

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
            "Snapshot demos do not need a live key."
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
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    st.subheader("Forecast check")
    forecast = result.forecast
    st.write(
        f"Seasonal-naive MAE on hub price holdout: {forecast.get('mae')} "
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
