"""Causal rolling features. The current observation is excluded from its baseline."""

from __future__ import annotations

import pandas as pd


def causal_median(series: pd.Series, window: int, min_periods: int) -> pd.Series:
    return series.shift(1).rolling(window, min_periods=min_periods).median()


def causal_mad(series: pd.Series, window: int, min_periods: int) -> pd.Series:
    baseline = causal_median(series, window, min_periods)
    deviation = (series.shift(1) - baseline).abs()
    return deviation.rolling(window, min_periods=min_periods).median()


def modified_z(value: float, baseline: float, mad: float) -> float | None:
    if pd.isna(baseline) or pd.isna(mad) or mad == 0:
        return None
    return float(0.6745 * (value - baseline) / mad)


def pivot_series(frame: pd.DataFrame, series: str, location: str) -> pd.Series:
    subset = frame[(frame["series"] == series) & (frame["location"] == location)].copy()
    subset = subset.sort_values("timestamp_utc")
    values = subset.drop_duplicates("timestamp_utc", keep="last").set_index("timestamp_utc")["value"]
    values.index = pd.to_datetime(values.index, utc=True)
    return values.sort_index().astype(float)
