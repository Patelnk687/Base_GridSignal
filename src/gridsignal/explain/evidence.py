"""Evidence records built only from measured fields."""

from __future__ import annotations

import pandas as pd
from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    evidence_id: str
    source_id: str
    series: str
    location: str
    timestamp_utc: str
    value: float | None
    unit: str
    kind: str
    is_synthetic: bool = False


class Explanation(BaseModel):
    subject_id: str
    facts: list[str]
    interpretation: list[str]
    hypotheses: list[str]
    evidence_ids: list[str]
    missing: list[str] = Field(default_factory=list)
    provider: str = "template"
    text: str = ""


def _fmt(value: float | None, unit: str) -> str:
    if value is None:
        return f"missing {unit}"
    return f"{value:.2f} {unit}"


def evidence_from_row(frame: pd.DataFrame, series: str, location: str, stamp: pd.Timestamp) -> EvidenceItem | None:
    subset = frame[
        (frame["series"] == series)
        & (frame["location"] == location)
        & (pd.to_datetime(frame["timestamp_utc"], utc=True) == stamp)
    ]
    if subset.empty:
        return None
    row = subset.iloc[0]
    value = None if pd.isna(row["value"]) else float(row["value"])
    evidence_id = f"ev-{series}-{location}-{stamp.isoformat()}"
    return EvidenceItem(
        evidence_id=evidence_id,
        source_id=str(row["source_id"]),
        series=series,
        location=location,
        timestamp_utc=stamp.isoformat(),
        value=value,
        unit=str(row["unit"]),
        kind=str(row["kind"]),
        is_synthetic=bool(row["is_synthetic"]),
    )


def bundle_for_event(event: pd.Series, frame: pd.DataFrame) -> list[EvidenceItem]:
    stamp = pd.Timestamp(event["timestamp_utc"])
    wanted = [
        ("spp_usd_per_mwh", "HB_HUBAVG"),
        ("spp_usd_per_mwh", "LZ_HOUSTON"),
        ("spp_usd_per_mwh", "LZ_WEST"),
        ("load_mw_total", "TOTAL"),
        ("wind_gen_mw", "SYSTEM"),
        ("wind_forecast_stwpf_mw", "SYSTEM"),
        ("solar_gen_mw", "SYSTEM"),
        ("shadow_price", "SYNTHETIC_CONSTRAINT"),
        ("load_forecast_mw", "SYSTEM"),
    ]
    items: list[EvidenceItem] = []
    for series, location in wanted:
        item = evidence_from_row(frame, series, location, stamp)
        if item is not None:
            items.append(item)
    return items
