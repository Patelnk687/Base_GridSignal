"""Validated internal models. Missing measurements stay null."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SeriesKind(StrEnum):
    ACTUAL = "actual"
    FORECAST = "forecast"
    PRICE = "price"
    CONSTRAINT = "constraint"
    OUTAGE = "outage"
    ADEQUACY = "adequacy"


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observation_id: str
    source_id: str
    source_name: str
    dataset_key: str
    location: str
    series: str
    kind: SeriesKind
    timestamp_utc: datetime
    interval_hours: float | None
    local_time_text: str | None = None
    timezone: str = "America/Chicago"
    dst_flag: bool | None = None
    value: float | None
    unit: str
    unit_note: str = ""
    report_time_utc: datetime | None = None
    ingested_at_utc: datetime
    raw_ref: str | None = None
    is_synthetic: bool = False
    quality_flags: list[str] = Field(default_factory=list)

    @field_validator("timestamp_utc", "ingested_at_utc", "report_time_utc")
    @classmethod
    def _require_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value


class ReportField(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    label: str | None = None
    dataType: str | None = None
    searchable: bool | None = None
    hasRange: bool | None = None


class DataPage(BaseModel):
    """Loose validation of a public-reports data page.

    The row envelope (``fields`` + ``data`` + ``_meta.totalPages``) is the shape
    observed by public clients and checked here. It was not re-fetched live in
    this repository because a subscription key was not available.
    """

    model_config = ConfigDict(extra="allow")

    fields: list[ReportField] | None = None
    data: list[list[Any]] | None = None


class TokenResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    token_type: str
    expires_in: int | str
    id_token: str
    access_token: str | None = None

    @field_validator("expires_in")
    @classmethod
    def _as_int(cls, value: int | str) -> int:
        return int(value)
