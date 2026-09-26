"""Shared chart styling for light and dark appearance."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from gridsignal.ui.theme import get_appearance

LIGHT = {
    "template": "plotly_white",
    "font": "#152033",
    "grid": "rgba(16,35,63,0.08)",
    "colors": ["#0f6e56", "#b45309", "#b42318", "#175cd3", "#6941c6"],
}
DARK = {
    "template": "plotly_dark",
    "font": "#e7ecf5",
    "grid": "rgba(255,255,255,0.06)",
    "colors": ["#e2a84b", "#2dd4bf", "#fb7185", "#7dd3fc", "#c4b5fd"],
}


def _palette() -> dict[str, object]:
    return LIGHT if get_appearance() == "light" else DARK


def base_layout(
    fig: go.Figure,
    title: str,
    y_title: str,
    height: int = 320,
    *,
    annotations: list[dict[str, object]] | None = None,
) -> go.Figure:
    palette = _palette()
    fig.update_layout(
        template=str(palette["template"]),
        title={"text": title, "x": 0, "font": {"size": 16}},
        yaxis_title=y_title,
        xaxis_title=None,
        height=height,
        margin={"l": 48, "r": 16, "t": 48, "b": 32},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend={"orientation": "h", "y": 1.12},
        font={"color": str(palette["font"]), "family": "IBM Plex Sans, sans-serif"},
        annotations=annotations or [],
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor=str(palette["grid"]))
    return fig


def time_series(
    frame: pd.DataFrame,
    columns: dict[str, str],
    title: str,
    y_title: str,
    *,
    marker_x: object | None = None,
    marker_label: str | None = None,
) -> go.Figure:
    fig = go.Figure()
    colors = list(_palette()["colors"])  # type: ignore[arg-type]
    for index, (column, label) in enumerate(columns.items()):
        if column not in frame.columns:
            continue
        fig.add_trace(
            go.Scatter(
                x=frame["timestamp_utc"],
                y=frame[column],
                name=label,
                mode="lines",
                line={"color": colors[index % len(colors)], "width": 2.2},
            )
        )
    annotations: list[dict[str, object]] = []
    if marker_x is not None and "timestamp_utc" in frame.columns:
        fig.add_vline(x=marker_x, line_width=1.5, line_dash="dot", line_color=colors[1])
        if marker_label:
            annotations.append(
                {
                    "x": marker_x,
                    "y": 1.02,
                    "xref": "x",
                    "yref": "paper",
                    "text": marker_label,
                    "showarrow": False,
                    "font": {"size": 11, "color": str(_palette()["font"])},
                }
            )
    return base_layout(fig, title, y_title, annotations=annotations)


def plot(fig: go.Figure) -> None:
    st.plotly_chart(fig, width="stretch")
