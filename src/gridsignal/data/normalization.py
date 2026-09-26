"""Map ERCOT rows onto timezone-aware observations.

Hour-ending rules are an explicit GridSignal convention documented in
docs/MODEL_METHODOLOGY.md. Missing values stay null. A spring-forward
hour that does not exist raises instead of being shifted silently.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from gridsignal.data.schemas import Observation, SeriesKind
from gridsignal.data.source_registry import DatasetSpec, ValueColumn

CHICAGO = ZoneInfo("America/Chicago")
UTC = UTC

_DATE_COLUMNS = {
    "deliverydate",
    "operday",
    "operatingday",
    "date",
    "delivery_date",
}
_HOUR_COLUMNS = {"hourending", "hour_ending"}
_DST_COLUMNS = {"dstflag", "repeatedhourflag"}
_POINT_COLUMNS = {
    "settlementpoint",
    "settlementpointname",
    "constraintname",
    "model",
}


class LocalTimeError(ValueError):
    pass


class NormalizationError(ValueError):
    pass


def _fold_utc(naive: datetime, fold: int, tz: ZoneInfo) -> datetime:
    aware = naive.replace(tzinfo=tz, fold=fold)
    return aware.astimezone(UTC)


def _is_ambiguous(naive: datetime, tz: ZoneInfo) -> bool:
    return _fold_utc(naive, 0, tz) != _fold_utc(naive, 1, tz)


def _is_nonexistent(naive: datetime, tz: ZoneInfo) -> bool:
    back = _fold_utc(naive, 0, tz).astimezone(tz).replace(tzinfo=None)
    return back != naive


def hour_ending_interval_end_utc(
    delivery_date: date,
    hour_ending: int,
    dst_flag: bool | None,
    tz: ZoneInfo = CHICAGO,
) -> datetime:
    """Return the UTC instant when an ERCOT hour-ending interval ends.

    Fallback (November): ERCOT publishes two rows with hour ending 2.
    ``dst_flag`` false is the first, daylight occurrence (ends at 01:00
    standard time). ``dst_flag`` true is the repeated standard-time hour
    (ends at 02:00 standard time).

    Spring forward: hour ending 2 does not exist and raises ``LocalTimeError``.
    """
    if hour_ending < 1 or hour_ending > 24:
        raise LocalTimeError(f"hour ending must be 1..24, got {hour_ending}")
    flag = bool(dst_flag)
    if hour_ending == 24:
        naive = datetime.combine(delivery_date + timedelta(days=1), time(0, 0))
    else:
        naive = datetime.combine(delivery_date, time(hour_ending, 0))

    one_am = datetime.combine(delivery_date, time(1, 0))
    if hour_ending == 2 and _is_ambiguous(one_am, tz):
        if not flag:
            return _fold_utc(one_am, 1, tz)
        return _fold_utc(naive, 0, tz)

    if _is_nonexistent(naive, tz):
        raise LocalTimeError(
            f"{naive.isoformat()} does not exist in {tz.key} (hour_ending={hour_ending}, dst_flag={flag})"
        )
    if _is_ambiguous(naive, tz):
        return _fold_utc(naive, 1 if flag else 0, tz)
    return _fold_utc(naive, 0, tz)


def _lookup(row: dict[str, object], *names: str) -> object | None:
    lowered = {str(key).lower(): value for key, value in row.items()}
    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()]
    return None


def _as_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        raise NormalizationError("delivery date is missing")
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(text[:10] if fmt == "%Y-%m-%d" else text, fmt).date()
        except ValueError:
            continue
    try:
        return date.fromisoformat(text[:10])
    except ValueError as exc:
        raise NormalizationError(f"unrecognized delivery date {value!r}") from exc


def _as_int(value: object, label: str) -> int:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        raise NormalizationError(f"{label} is missing")
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "null"}:
        raise NormalizationError(f"{label} is missing")
    try:
        return int(float(text))
    except ValueError as exc:
        raise NormalizationError(f"{label} is not an integer: {value!r}") from exc


def _as_bool(value: object) -> bool | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"", "nan", "none", "null"}:
        return None
    if text in {"y", "yes", "true", "1", "t"}:
        return True
    if text in {"n", "no", "false", "0", "f"}:
        return False
    raise NormalizationError(f"DST flag is not boolean: {value!r}")


def _as_float(value: object) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "null"}:
        return None
    try:
        return float(text)
    except ValueError as exc:
        raise NormalizationError(f"value is not numeric: {value!r}") from exc


def _column_value(row: dict[str, object], column: ValueColumn) -> object | None:
    names = [column.column, *column.aliases]
    return _lookup(row, *names)


def _location(row: dict[str, object], column: ValueColumn) -> str:
    if column.location:
        return column.location
    if column.location_column:
        raw = _lookup(row, column.location_column, column.location_column.lower())
        if raw is None or str(raw).strip().lower() in {"", "nan", "none"}:
            raise NormalizationError(f"location column {column.location_column} is empty")
        return str(raw).strip()
    raw_point = None
    lowered = {str(key).lower(): value for key, value in row.items()}
    for name in _POINT_COLUMNS:
        if name in lowered and lowered[name] not in (None, ""):
            raw_point = lowered[name]
            break
    if raw_point is None:
        raise NormalizationError("row has no location")
    return str(raw_point).strip()


def timestamp_from_row(row: dict[str, object]) -> tuple[datetime, bool | None, list[str]]:
    flags: list[str] = []
    date_value = None
    for key, value in row.items():
        if str(key).lower() in _DATE_COLUMNS:
            date_value = value
            break
    hour_value = None
    for key, value in row.items():
        if str(key).lower() in _HOUR_COLUMNS:
            hour_value = value
            break
    dst_value = None
    for key, value in row.items():
        if str(key).lower() in _DST_COLUMNS:
            dst_value = value
            break
    if date_value is None or hour_value is None:
        raise NormalizationError("row is missing a delivery date or hour ending")
    dst_flag = _as_bool(dst_value)
    delivery = _as_date(date_value)
    hour_ending = _as_int(hour_value, "hour ending")
    # DeliveryHour is a different XSD element. Do not silently treat it as hour ending.
    if any(str(key).lower() == "deliveryhour" for key in row) and hour_value is None:
        raise NormalizationError("DeliveryHour was present without HourEnding; mapping is unverified")
    interval_raw = _lookup(row, "DeliveryInterval", "deliveryInterval")
    if interval_raw not in (None, "") and not (isinstance(interval_raw, float) and pd.isna(interval_raw)):
        flags.append("subhour_interval_unresolved")
    stamp = hour_ending_interval_end_utc(delivery, hour_ending, dst_flag)
    return stamp, dst_flag, flags


def normalize_rows(
    rows: list[dict[str, object]],
    spec: DatasetSpec,
    *,
    ingested_at: datetime | None = None,
    is_synthetic: bool = False,
    raw_ref: str | None = None,
) -> list[Observation]:
    ingested = ingested_at or datetime.now(UTC)
    if ingested.tzinfo is None:
        raise NormalizationError("ingested_at must be timezone-aware")
    observations: list[Observation] = []
    for index, row in enumerate(rows):
        try:
            stamp, dst_flag, row_flags = timestamp_from_row(row)
        except (NormalizationError, LocalTimeError) as exc:
            raise NormalizationError(f"{spec.emil_id} row {index}: {exc}") from exc
        local_text = None
        for key, value in row.items():
            if str(key).lower() in _DATE_COLUMNS:
                local_text = f"{value} HE={_lookup(row, 'HourEnding', 'hourEnding')}"
                break
        for column in spec.value_columns:
            try:
                raw_value = _column_value(row, column)
                value = _as_float(raw_value)
                location = _location(row, column)
            except NormalizationError as exc:
                raise NormalizationError(f"{spec.emil_id} row {index}: {exc}") from exc
            obs_flags = list(row_flags)
            if raw_value is None or (isinstance(raw_value, float) and pd.isna(raw_value)):
                obs_flags.append("missing_value")
            if column.kind == SeriesKind.FORECAST:
                obs_flags.append("forecast_not_actual")
            observations.append(
                Observation(
                    observation_id=(f"{spec.emil_id}:{column.series}:{location}:{stamp.isoformat()}"),
                    source_id=spec.emil_id,
                    source_name=spec.name,
                    dataset_key=spec.key,
                    location=location,
                    series=column.series,
                    kind=column.kind,
                    timestamp_utc=stamp,
                    interval_hours=1.0 if "subhour_interval_unresolved" not in obs_flags else None,
                    local_time_text=local_text,
                    dst_flag=dst_flag,
                    value=value,
                    unit=column.unit,
                    unit_note=column.unit_note,
                    ingested_at_utc=ingested,
                    raw_ref=raw_ref,
                    is_synthetic=is_synthetic,
                    quality_flags=obs_flags,
                )
            )
    return observations


def observations_frame(observations: list[Observation]) -> pd.DataFrame:
    if not observations:
        return pd.DataFrame()
    frame = pd.DataFrame([item.model_dump() for item in observations])
    frame["timestamp_utc"] = pd.to_datetime(frame["timestamp_utc"], utc=True)
    frame["ingested_at_utc"] = pd.to_datetime(frame["ingested_at_utc"], utc=True)
    return frame


def duplicate_report(frame: pd.DataFrame) -> pd.DataFrame:
    """Rows that share source, series, location, and timestamp.

    Equal values are duplicates. Unequal values are conflicting revisions.
    """
    if frame.empty:
        return frame
    keys = ["source_id", "series", "location", "timestamp_utc"]
    grouped = frame.groupby(keys, dropna=False)["value"]
    rows = []
    for key, values in grouped:
        unique = {None if pd.isna(item) else item for item in values}
        if len(values) <= 1:
            continue
        rows.append(
            {
                "source_id": key[0],
                "series": key[1],
                "location": key[2],
                "timestamp_utc": key[3],
                "copies": int(len(values)),
                "distinct_values": len(unique),
                "status": "conflict" if len(unique) > 1 else "duplicate",
            }
        )
    return pd.DataFrame(rows)


def missing_hourly_timestamps(stamps: pd.Series) -> list[pd.Timestamp]:
    """Hourly gaps. Does not invent values for the missing hours."""
    if stamps.empty:
        return []
    ordered = pd.to_datetime(stamps, utc=True).drop_duplicates().sort_values()
    full = pd.date_range(ordered.iloc[0], ordered.iloc[-1], freq="h", tz="UTC")
    present = set(ordered)
    return [item for item in full if item not in present]
