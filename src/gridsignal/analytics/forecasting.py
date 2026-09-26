"""Baseline price forecast.

Seasonal naive (same hour yesterday) is evaluated on a trailing holdout.
This is not a claim that GridSignal predicts ERCOT prices.
"""

from __future__ import annotations

import pandas as pd

from gridsignal.analytics.features import pivot_series


def seasonal_naive_forecast(series: pd.Series, season: int = 24) -> pd.Series:
    """Forecast each point with the value ``season`` steps earlier. No future values are used."""
    return series.shift(season)


def evaluate_holdout(series: pd.Series, holdout: int = 12, season: int = 24) -> dict[str, float | int | None]:
    forecast = seasonal_naive_forecast(series, season=season)
    if len(series) <= holdout + season:
        return {"mae": None, "holdout_points": 0, "season": season}
    actual = series.iloc[-holdout:]
    predicted = forecast.iloc[-holdout:]
    paired = pd.concat({"actual": actual, "predicted": predicted}, axis=1).dropna()
    if paired.empty:
        return {"mae": None, "holdout_points": 0, "season": season}
    mae = float((paired["actual"] - paired["predicted"]).abs().mean())
    return {"mae": round(mae, 3), "holdout_points": int(len(paired)), "season": season}


def price_forecast_report(frame: pd.DataFrame) -> dict[str, object]:
    prices = pivot_series(frame, "spp_usd_per_mwh", "HB_HUBAVG")
    metrics = evaluate_holdout(prices)
    metrics["series"] = "spp_usd_per_mwh"
    metrics["location"] = "HB_HUBAVG"
    metrics["model"] = "seasonal_naive_24h"
    metrics["claim"] = "Holdout error on the series that was scored. Not a validated forecast of future ERCOT prices."
    return metrics
