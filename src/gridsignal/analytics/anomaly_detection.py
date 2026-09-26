"""Interpretable anomaly detection.

Primary flags use a past-only median and MAD. Isolation Forest is optional and
is fit only on a prefix so later scores do not train on the points they judge.
A statistical outlier is not labeled a grid emergency.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from gridsignal.analytics.features import causal_mad, causal_median, modified_z, pivot_series

SEVERITY_ORDER = {"low": 1, "moderate": 2, "high": 3}


@dataclass(frozen=True)
class AnomalyRule:
    series: str
    location: str
    category: str
    min_abs: float
    z_threshold: float = 3.5
    direction: str = "both"  # both, up, down


DEFAULT_RULES: tuple[AnomalyRule, ...] = (
    AnomalyRule("load_mw_total", "TOTAL", "load_deviation", 1500.0, direction="both"),
    AnomalyRule("wind_gen_mw", "SYSTEM", "renewable_ramp", 800.0, direction="both"),
    AnomalyRule("solar_gen_mw", "SYSTEM", "renewable_ramp", 800.0, direction="both"),
    AnomalyRule("spp_usd_per_mwh", "HB_HUBAVG", "price_spike", 40.0, direction="up"),
    AnomalyRule("spp_usd_per_mwh", "HB_HUBAVG", "price_drop", 40.0, direction="down"),
    AnomalyRule("spp_usd_per_mwh", "LZ_HOUSTON", "price_spike", 40.0, direction="up"),
    AnomalyRule("shadow_price", "SYNTHETIC_CONSTRAINT", "constraint_shadow", 20.0, direction="up"),
)


def _severity(z_abs: float) -> str:
    if z_abs >= 8:
        return "high"
    if z_abs >= 5:
        return "moderate"
    return "low"


def detect_series(
    values: pd.Series,
    rule: AnomalyRule,
    *,
    window: int,
    min_periods: int,
    source_id: str,
) -> list[dict[str, object]]:
    baseline = causal_median(values, window, min_periods)
    mad = causal_mad(values, window, min_periods)
    events: list[dict[str, object]] = []
    for stamp, value in values.items():
        if pd.isna(value):
            continue
        base = baseline.loc[stamp]
        scale = mad.loc[stamp]
        warnings: list[str] = []
        if pd.isna(base):
            continue
        deviation = float(value) - float(base)
        if rule.direction == "up" and deviation <= 0:
            continue
        if rule.direction == "down" and deviation >= 0:
            continue
        if abs(deviation) < rule.min_abs:
            continue
        score = modified_z(float(value), float(base), float(scale) if pd.notna(scale) else np.nan)
        if score is None:
            warnings.append("zero_mad")
            severity = "high" if abs(deviation) >= 5 * rule.min_abs else "moderate"
        else:
            if abs(score) < rule.z_threshold:
                continue
            severity = _severity(abs(score))
        pct = None if float(base) == 0 else 100.0 * deviation / float(base)
        strength = 0.7 if score is None else round(min(1.0, abs(score) / 10.0), 2)
        events.append(
            {
                "event_id": f"evt-{rule.category}-{rule.location}-{pd.Timestamp(stamp).isoformat()}",
                "timestamp_utc": pd.Timestamp(stamp),
                "location": rule.location,
                "category": rule.category,
                "severity": severity,
                "series": rule.series,
                "observed": float(value),
                "baseline": float(base),
                "deviation": deviation,
                "deviation_pct": pct,
                "modified_z": score,
                "evidence_strength": strength,
                "source_id": source_id,
                "missing_data_warnings": warnings,
                "method": "causal_median_mad",
            }
        )
    return events


def _source_for(frame: pd.DataFrame, series: str, location: str) -> str:
    subset = frame[(frame["series"] == series) & (frame["location"] == location)]
    if subset.empty:
        return ""
    return str(subset.iloc[0]["source_id"])


def hub_zone_spread_events(
    frame: pd.DataFrame,
    *,
    window: int,
    min_periods: int,
) -> list[dict[str, object]]:
    hub = pivot_series(frame, "spp_usd_per_mwh", "HB_HUBAVG")
    zone = pivot_series(frame, "spp_usd_per_mwh", "LZ_HOUSTON")
    if hub.empty or zone.empty:
        return []
    aligned = pd.concat({"hub": hub, "zone": zone}, axis=1).dropna()
    spread = aligned["zone"] - aligned["hub"]
    rule = AnomalyRule("hub_zone_spread", "LZ_HOUSTON-HB_HUBAVG", "hub_zone_spread", 25.0, direction="up")
    events = detect_series(
        spread,
        rule,
        window=window,
        min_periods=min_periods,
        source_id=_source_for(frame, "spp_usd_per_mwh", "HB_HUBAVG"),
    )
    for event in events:
        event["series"] = "spp_usd_per_mwh"
        event["supporting"] = "LZ_HOUSTON minus HB_HUBAVG"
    return events


def forecast_divergence_events(
    frame: pd.DataFrame,
    *,
    window: int,
    min_periods: int,
) -> list[dict[str, object]]:
    actual = pivot_series(frame, "wind_gen_mw", "SYSTEM")
    forecast = pivot_series(frame, "wind_forecast_stwpf_mw", "SYSTEM")
    if actual.empty or forecast.empty:
        return []
    aligned = pd.concat({"actual": actual, "forecast": forecast}, axis=1)
    residual = (aligned["actual"] - aligned["forecast"]).dropna()
    rule = AnomalyRule("wind_forecast_residual", "SYSTEM", "forecast_divergence", 800.0)
    return detect_series(
        residual,
        rule,
        window=window,
        min_periods=min_periods,
        source_id=_source_for(frame, "wind_gen_mw", "SYSTEM"),
    )


def correlate(events: list[dict[str, object]], window_minutes: int) -> list[dict[str, object]]:
    ordered = sorted(events, key=lambda item: pd.Timestamp(item["timestamp_utc"]))
    group = 0
    last_stamp: pd.Timestamp | None = None
    for event in ordered:
        stamp = pd.Timestamp(event["timestamp_utc"])
        if last_stamp is None or (stamp - last_stamp) > pd.Timedelta(minutes=window_minutes):
            group += 1
        event["correlation_group"] = f"grp-{group}"
        event["causation"] = "temporal_coincidence_only"
        last_stamp = stamp
    return ordered


def explain_event(event: dict[str, object], frame: pd.DataFrame) -> str:
    stamp = pd.Timestamp(event["timestamp_utc"])
    wind = _value_at(frame, "wind_gen_mw", "SYSTEM", stamp)
    load = _value_at(frame, "load_mw_total", "TOTAL", stamp)
    price = _value_at(frame, "spp_usd_per_mwh", "HB_HUBAVG", stamp)
    parts = [
        f"At {stamp.isoformat()}, {event['category']} at {event['location']}: "
        f"observed {event['observed']:.2f} versus a past-only median baseline of {event['baseline']:.2f} "
        f"(deviation {event['deviation']:.2f})."
    ]
    context = []
    if load is not None:
        context.append(f"system load was {load:.1f} MW")
    if wind is not None:
        context.append(f"system wind generation was {wind:.1f} MW")
    if price is not None:
        context.append(f"HB_HUBAVG settlement price was {price:.2f} USD/MWh")
    if context:
        parts.append("During the same interval, " + ", ".join(context) + ".")
    parts.append(
        "These series coincide in time. The detector does not establish that one series caused another, "
        "and a statistical outlier is not an ERCOT emergency notice."
    )
    if event.get("missing_data_warnings"):
        parts.append("Warnings: " + ", ".join(event["missing_data_warnings"]) + ".")
    return " ".join(parts)


def _value_at(frame: pd.DataFrame, series: str, location: str, stamp: pd.Timestamp) -> float | None:
    subset = frame[
        (frame["series"] == series)
        & (frame["location"] == location)
        & (pd.to_datetime(frame["timestamp_utc"], utc=True) == stamp)
    ]
    if subset.empty or pd.isna(subset.iloc[0]["value"]):
        return None
    return float(subset.iloc[0]["value"])


def detect_anomalies(
    frame: pd.DataFrame,
    *,
    window: int = 12,
    min_periods: int = 8,
    correlation_minutes: int = 90,
    rules: tuple[AnomalyRule, ...] = DEFAULT_RULES,
) -> pd.DataFrame:
    events: list[dict[str, object]] = []
    for rule in rules:
        values = pivot_series(frame, rule.series, rule.location)
        if values.empty:
            continue
        events.extend(
            detect_series(
                values,
                rule,
                window=window,
                min_periods=min_periods,
                source_id=_source_for(frame, rule.series, rule.location),
            )
        )
    events.extend(hub_zone_spread_events(frame, window=window, min_periods=min_periods))
    events.extend(forecast_divergence_events(frame, window=window, min_periods=min_periods))
    events = correlate(events, correlation_minutes)
    for event in events:
        event["explanation"] = explain_event(event, frame)
    if not events:
        return pd.DataFrame()
    return pd.DataFrame(events).sort_values(["timestamp_utc", "severity"]).reset_index(drop=True)


def isolation_forest_scores(
    values: pd.Series,
    train_end: int,
    *,
    contamination: float = 0.08,
    random_state: int = 7,
) -> pd.Series:
    """Score only the suffix. Training uses ``values.iloc[:train_end]`` and nothing after it."""
    scores = pd.Series(np.nan, index=values.index, dtype=float)
    clean = values.dropna()
    if train_end < 8 or len(clean) <= train_end:
        return scores
    train = clean.iloc[:train_end].to_numpy().reshape(-1, 1)
    model = IsolationForest(contamination=contamination, random_state=random_state)
    model.fit(train)
    tail = clean.iloc[train_end:]
    decision = model.decision_function(tail.to_numpy().reshape(-1, 1))
    # Negative decision_function means more anomalous. Flip the sign for a positive score.
    scores.loc[tail.index] = -decision
    return scores
