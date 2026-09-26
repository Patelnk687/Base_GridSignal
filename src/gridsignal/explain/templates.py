"""Template explanations. Every number comes from an evidence item or the anomaly record."""

from __future__ import annotations

import math

from gridsignal.explain.evidence import EvidenceItem, Explanation, _fmt


def _find(items: list[EvidenceItem], series: str, location: str) -> EvidenceItem | None:
    for item in items:
        if item.series == series and item.location == location:
            return item
    return None


def explain_anomaly(event: dict[str, object], items: list[EvidenceItem]) -> Explanation:
    by_id = [item.evidence_id for item in items]
    price = _find(items, "spp_usd_per_mwh", str(event["location"])) or _find(items, "spp_usd_per_mwh", "HB_HUBAVG")
    load = _find(items, "load_mw_total", "TOTAL")
    wind = _find(items, "wind_gen_mw", "SYSTEM")
    wind_fcst = _find(items, "wind_forecast_stwpf_mw", "SYSTEM")
    missing = []
    z_value = event["modified_z"]
    z_number = None
    if isinstance(z_value, int | float) and not (isinstance(z_value, float) and math.isnan(z_value)):
        z_number = float(z_value)
    z_text = (
        f"{z_number:.2f}" if z_number is not None else "unavailable because the past MAD was zero"
    )
    facts = [
        (
            f"At {event['timestamp_utc']}, {event['category']} at {event['location']}: "
            f"observed {float(event['observed']):.2f} against a past-only median of "
            f"{float(event['baseline']):.2f} "
            f"(absolute deviation {float(event['deviation']):.2f}, modified z {z_text}). "
            f"Source {event.get('source_id') or 'unspecified'}."
        )
    ]
    if price is not None:
        facts.append(
            f"Settlement price evidence {price.evidence_id}: "
            f"{price.location} was {_fmt(price.value, price.unit)} at {price.timestamp_utc} "
            f"({price.source_id}, kind={price.kind})."
        )
    else:
        missing.append("settlement price at the event location")
    if load is not None:
        facts.append(f"Load evidence {load.evidence_id}: system load was {_fmt(load.value, load.unit)}.")
    else:
        missing.append("system load")
    if wind is not None:
        facts.append(f"Wind evidence {wind.evidence_id}: measured wind generation was {_fmt(wind.value, wind.unit)}.")
    else:
        missing.append("wind generation")
    if wind_fcst is not None and wind is not None and wind.value is not None and wind_fcst.value is not None:
        facts.append(
            f"Wind forecast evidence {wind_fcst.evidence_id}: STWPF was {_fmt(wind_fcst.value, wind_fcst.unit)}. "
            f"The forecast-minus-actual gap is {wind.value - wind_fcst.value:.2f} {wind.unit}."
        )
    interpretation = [
        "The anomaly rule compared the observation with a rolling median computed only from earlier intervals.",
        "A large modified-z score means the point is unusual relative to that baseline. "
        "It is not an ERCOT emergency declaration.",
    ]
    hypotheses = [
        "Load, wind, and price moved in the same interval. Coincidence is not evidence that one caused the others. "
        "No counterfactual dispatch or transmission model is included."
    ]
    if any(item.is_synthetic for item in items):
        facts.append("One or more cited rows are labeled SYNTHETIC and are not ERCOT history.")
    text = " ".join(facts + interpretation + hypotheses)
    if missing:
        text += " Missing: " + ", ".join(missing) + "."
    return Explanation(
        subject_id=str(event["event_id"]),
        facts=facts,
        interpretation=interpretation,
        hypotheses=hypotheses,
        evidence_ids=by_id,
        missing=missing,
        provider="template",
        text=text,
    )
