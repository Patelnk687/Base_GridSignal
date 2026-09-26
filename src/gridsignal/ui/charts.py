"""Shared chart styling."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

ACCENT = "#e2a84b"
TEAL = "#2dd4bf"
ROSE = "#fb7185"
SLATE = "#93a0b8"


def base_layout(fig: go.Figure, title: str, y_title: str, height: int = 320) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        title={"text": title, "x": 0, "font": {"size": 16}},
        yaxis_title=y_title,
        xaxis_title=None,
        height=height,
        margin={"l": 48, "r": 16, "t": 48, "b": 32},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend={"orientation": "h", "y": 1.12},
        font={"color": "#e7ecf5"},
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)")
    return fig


def time_series(frame: pd.DataFrame, columns: dict[str, str], title: str, y_title: str) -> go.Figure:
    fig = go.Figure()
    colors = [ACCENT, TEAL, ROSE, "#7dd3fc", "#c4b5fd"]
    for index, (column, label) in enumerate(columns.items()):
        if column not in frame.columns:
            continue
        fig.add_trace(
            go.Scatter(
                x=frame["timestamp_utc"],
                y=frame[column],
                name=label,
                mode="lines",
                line={"color": colors[index % len(colors)], "width": 2},
            )
        )
    return base_layout(fig, title, y_title)
