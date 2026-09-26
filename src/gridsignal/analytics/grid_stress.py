"""GridSignal Stress Indicator.

This is a project-defined score. It is not an ERCOT reliability rating.
Weights are documented assumptions. A missing input is dropped and the
remaining weights are renormalized. It is never treated as a normal condition.
"""

from __future__ import annotations

import pandas as pd

from gridsignal.analytics.features import causal_mad, causal_median, modified_z, pivot_series

# Initial weights. Rationale: price and load carry the operational story a
# battery operator would see first; ramps catch the fast moves that level
# alone misses. They are not estimated from a reliability study.
DEFAULT_WEIGHTS: dict[str, float] = {
    "load_level": 0.25,
    "load_ramp": 0.15,
    "renewable_drop": 0.20,
    "price_level": 0.25,
    "price_change": 0.15,
}

# Scale assumptions used only to map a physical delta onto 0-100.
LOAD_RAMP_MW_FOR_FULL_SCORE = 8000.0
RENEWABLE_DROP_MW_FOR_FULL_SCORE = 6000.0
PRICE_CHANGE_USD_FOR_FULL_SCORE = 150.0


def _clip_score(value: float) -> float:
    return float(max(0.0, min(100.0, value)))


def _positive_z_score(series: pd.Series, window: int, min_periods: int) -> pd.Series:
    baseline = causal_median(series, window, min_periods)
    mad = causal_mad(series, window, min_periods)
    scores = []
    for stamp, value in series.items():
        if pd.isna(value) or pd.isna(baseline.loc[stamp]) or pd.isna(mad.loc[stamp]):
            scores.append(None)
            continue
        score = modified_z(float(value), float(baseline.loc[stamp]), float(mad.loc[stamp]))
        if score is None:
            scores.append(None)
        else:
            scores.append(_clip_score(max(score, 0.0) / 4.0 * 100.0))
    return pd.Series(scores, index=series.index, dtype=object)


def _ramp_score(series: pd.Series, full_scale: float, *, positive: bool) -> pd.Series:
    delta = series - series.shift(1)
    scores = []
    for stamp, change in delta.items():
        if pd.isna(change) or pd.isna(series.loc[stamp]):
            scores.append(None)
            continue
        signed = float(change) if positive else -float(change)
        scores.append(_clip_score(signed / full_scale * 100.0))
    return pd.Series(scores, index=series.index, dtype=object)


def compute_stress(
    frame: pd.DataFrame,
    *,
    window: int = 12,
    min_periods: int = 8,
    weights: dict[str, float] | None = None,
) -> pd.DataFrame:
    weights = dict(weights or DEFAULT_WEIGHTS)
    load = pivot_series(frame, "load_mw_total", "TOTAL")
    wind = pivot_series(frame, "wind_gen_mw", "SYSTEM")
    solar = pivot_series(frame, "solar_gen_mw", "SYSTEM")
    price = pivot_series(frame, "spp_usd_per_mwh", "HB_HUBAVG")
    index = load.index.union(wind.index).union(solar.index).union(price.index).sort_values()
    renewable = (wind.reindex(index) + solar.reindex(index)).astype(float)
    # A missing wind or solar hour must not become zero inside the sum.
    both_present = wind.reindex(index).notna() & solar.reindex(index).notna()
    renewable = renewable.where(both_present)

    components = {
        "load_level": _positive_z_score(load.reindex(index), window, min_periods),
        "load_ramp": _ramp_score(load.reindex(index), LOAD_RAMP_MW_FOR_FULL_SCORE, positive=True),
        "renewable_drop": _ramp_score(renewable, RENEWABLE_DROP_MW_FOR_FULL_SCORE, positive=False),
        "price_level": _positive_z_score(price.reindex(index), window, min_periods),
        "price_change": _ramp_score(price.reindex(index), PRICE_CHANGE_USD_FOR_FULL_SCORE, positive=True),
    }
    rows: list[dict[str, object]] = []
    previous: float | None = None
    previous_parts: dict[str, float | None] = {}
    for stamp in index:
        parts: dict[str, float | None] = {}
        available_weight = 0.0
        weighted = 0.0
        for name, weight in weights.items():
            raw = components[name].loc[stamp]
            if raw is None or (isinstance(raw, float) and pd.isna(raw)):
                parts[name] = None
                continue
            parts[name] = float(raw)
            available_weight += weight
            weighted += weight * float(raw)
        total_weight = sum(weights.values())
        if available_weight == 0:
            score = None
            status = "unavailable"
        else:
            score = weighted / available_weight
            status = "complete" if abs(available_weight - total_weight) < 1e-9 else "incomplete"
        completeness = 0.0 if total_weight == 0 else available_weight / total_weight
        trend = None if score is None or previous is None else score - previous
        explanation = _explain(stamp, score, status, completeness, parts, previous_parts, trend)
        rows.append(
            {
                "timestamp_utc": stamp,
                "score": None if score is None else round(score, 2),
                "status": status,
                "completeness": round(completeness, 3),
                "trend": None if trend is None else round(trend, 2),
                "explanation": explanation,
                **{f"component_{name}": value for name, value in parts.items()},
            }
        )
        previous = score
        previous_parts = parts
    return pd.DataFrame(rows)


def _explain(
    stamp: pd.Timestamp,
    score: float | None,
    status: str,
    completeness: float,
    parts: dict[str, float | None],
    previous: dict[str, float | None],
    trend: float | None,
) -> str:
    if score is None:
        return (
            f"At {pd.Timestamp(stamp).isoformat()} the GridSignal Stress Indicator is unavailable. "
            "Every component was missing, and missing inputs were not treated as normal."
        )
    present = [f"{name}={value:.0f}" for name, value in parts.items() if value is not None]
    missing = [name for name, value in parts.items() if value is None]
    text = (
        f"At {pd.Timestamp(stamp).isoformat()} the GridSignal Stress Indicator is {score:.0f}/100 "
        f"({status}, data completeness {completeness:.0%}). Components: {', '.join(present)}."
    )
    if missing:
        text += f" Excluded because the measurement was missing: {', '.join(missing)}."
    if trend is not None and previous:
        deltas = []
        for name, value in parts.items():
            before = previous.get(name)
            if value is None or before is None:
                continue
            deltas.append((abs(value - before), name, value - before))
        if deltas:
            _, name, delta = max(deltas)
            text += f" The largest component change versus the prior interval was {name} ({delta:+.0f})."
    text += " This score is a GridSignal construct, not an official ERCOT rating."
    return text
