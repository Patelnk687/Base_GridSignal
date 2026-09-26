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
    "colors": ["#0f6e56", "#c27803", "#e11d48", "#2563eb", "#0e7490"],
    "fill": "rgba(15,110,86,0.12)",
    "band": "rgba(225,29,72,0.08)",
}
DARK = {
    "template": "plotly_dark",
    "font": "#e7ecf5",
    "grid": "rgba(255,255,255,0.06)",
    "colors": ["#2dd4bf", "#fbbf24", "#fb7185", "#60a5fa", "#67e8f9"],
    "fill": "rgba(45,212,191,0.15)",
    "band": "rgba(251,113,133,0.12)",
}


def _palette() -> dict[str, object]:
    return LIGHT if get_appearance() == "light" else DARK


def base_layout(
    fig: go.Figure,
    title: str,
    y_title: str,
    height: int = 340,
    *,
    annotations: list[dict[str, object]] | None = None,
) -> go.Figure:
    palette = _palette()
    fig.update_layout(
        template=str(palette["template"]),
        title={"text": title, "x": 0, "font": {"size": 16, "color": str(palette["font"])}},
        yaxis_title=y_title,
        xaxis_title=None,
        height=height,
        margin={"l": 48, "r": 16, "t": 52, "b": 32},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend={"orientation": "h", "y": 1.14},
        font={"color": str(palette["font"]), "family": "IBM Plex Sans, sans-serif"},
        annotations=annotations or [],
        hovermode="x unified",
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
    fill_first: bool = False,
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
                line={"color": colors[index % len(colors)], "width": 2.4},
                fill="tozeroy" if fill_first and index == 0 else None,
                fillcolor=str(_palette()["fill"]) if fill_first and index == 0 else None,
            )
        )
    annotations: list[dict[str, object]] = []
    if marker_x is not None and "timestamp_utc" in frame.columns:
        fig.add_vline(x=marker_x, line_width=2, line_dash="dot", line_color=colors[2])
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
                    "bgcolor": "rgba(0,0,0,0)",
                }
            )
    return base_layout(fig, title, y_title, annotations=annotations)


def spread_series(
    frame: pd.DataFrame,
    value_column: str,
    title: str,
    *,
    marker_x: object | None = None,
) -> go.Figure:
    """Signed spread chart with a zero line — congestion jumps pop visually."""
    fig = go.Figure()
    colors = list(_palette()["colors"])  # type: ignore[arg-type]
    positive = frame[value_column].clip(lower=0)
    negative = frame[value_column].clip(upper=0)
    fig.add_trace(
        go.Scatter(
            x=frame["timestamp_utc"],
            y=positive,
            name="Houston > hub",
            mode="lines",
            line={"color": colors[2], "width": 2},
            fill="tozeroy",
            fillcolor=str(_palette()["band"]),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=frame["timestamp_utc"],
            y=negative,
            name="Houston < hub",
            mode="lines",
            line={"color": colors[3], "width": 2},
            fill="tozeroy",
            fillcolor="rgba(37,99,235,0.12)",
        )
    )
    fig.add_hline(y=0, line_width=1, line_color=str(_palette()["font"]), opacity=0.35)
    if marker_x is not None:
        fig.add_vline(x=marker_x, line_width=2, line_dash="dot", line_color=colors[1])
    return base_layout(fig, title, "USD/MWh")


def plot(fig: go.Figure) -> None:
    st.plotly_chart(fig, width="stretch")
