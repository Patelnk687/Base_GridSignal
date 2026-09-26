"""Bundled demo scenario.

Every row is labeled SYNTHETIC. These are not ERCOT historical observations.
The shape is realistic enough to exercise anomaly detection and battery dispatch:
an evening load ramp, a wind drop the forecast does not catch, and a hub-zone
price spread. The clock uses ERCOT hour-ending timestamps in America/Chicago.
"""

from __future__ import annotations

import math
from datetime import UTC, date, datetime, timedelta

from gridsignal.data.normalization import normalize_rows, observations_frame
from gridsignal.data.schemas import Observation
from gridsignal.data.source_registry import by_key

SCENARIO_ID = "SYNTHETIC-STRESS-001"
START = date(2024, 7, 15)
HOURS = 48
SPIKE_INDEX = 18
INGESTED_AT = datetime(2024, 7, 17, 12, 0, tzinfo=UTC)


def _hours() -> list[tuple[int, date, int]]:
    day = START
    hour_ending = 1
    rows = []
    for index in range(HOURS):
        rows.append((index, day, hour_ending))
        hour_ending += 1
        if hour_ending == 25:
            hour_ending = 1
            day += timedelta(days=1)
    return rows


def _load_total(index: int, hour_ending: int) -> float:
    diurnal = 7000 * math.sin((hour_ending - 6) / 24 * 2 * math.pi)
    total = 52000 + diurnal
    if index == SPIKE_INDEX:
        total += 11000
    return round(total, 1)


def build_raw_tables() -> dict[str, list[dict[str, object]]]:
    load_rows: list[dict[str, object]] = []
    wind_rows: list[dict[str, object]] = []
    solar_rows: list[dict[str, object]] = []
    price_rows: list[dict[str, object]] = []
    forecast_rows: list[dict[str, object]] = []
    shadow_rows: list[dict[str, object]] = []
    shares = {
        "COAST": 0.28,
        "EAST": 0.08,
        "FAR_WEST": 0.04,
        "NORTH": 0.06,
        "NORTH_C": 0.22,
        "SOUTHERN": 0.07,
        "SOUTH_C": 0.18,
        "WEST": 0.07,
    }
    for index, day, hour_ending in _hours():
        total = _load_total(index, hour_ending)
        load_rows.append(
            {
                "OperDay": day.isoformat(),
                "HourEnding": hour_ending,
                "DSTFlag": "N",
                **{name: round(total * share, 1) for name, share in shares.items()},
                "TOTAL": total,
                "data_label": "SYNTHETIC",
                "scenario_id": SCENARIO_ID,
            }
        )
        wind = 15000.0 if index < SPIKE_INDEX or index > SPIKE_INDEX + 2 else 3200.0
        wind_forecast = 14800.0
        wind_row: dict[str, object] = {
            "DELIVERY_DATE": day.isoformat(),
            "HOUR_ENDING": hour_ending,
            "DSTFlag": "N",
            "SYSTEM_WIDE_GEN": None if index == 4 else wind,
            "STWPF_SYSTEM_WIDE": wind_forecast,
            "WGRPP_SYSTEM_WIDE": wind_forecast - 400,
            "data_label": "SYNTHETIC",
        }
        wind_rows.append(wind_row)
        daylight = max(0.0, math.sin((hour_ending - 6) / 14 * math.pi))
        solar = round(9000 * daylight, 1) if 7 <= hour_ending <= 20 else 0.0
        solar_rows.append(
            {
                "DELIVERY_DATE": day.isoformat(),
                "HOUR_ENDING": hour_ending,
                "DSTFlag": "N",
                "SYSTEM_WIDE_GEN": solar,
                "STPPF_SYSTEM_WIDE": solar,
                "PVGRPP_SYSTEM_WIDE": max(solar - 200, 0),
                "data_label": "SYNTHETIC",
            }
        )
        hub = 32.0
        houston_extra = 6.0
        if index == SPIKE_INDEX:
            hub = 340.0
            houston_extra = 160.0
        elif index == SPIKE_INDEX + 1:
            hub = 180.0
            houston_extra = 40.0
        for point, price in (
            ("HB_HUBAVG", hub),
            ("LZ_HOUSTON", hub + houston_extra),
            ("LZ_WEST", hub - 5.0),
            ("HB_NORTH", hub + 3.0),
        ):
            price_rows.append(
                {
                    "DeliveryDate": day.isoformat(),
                    "HourEnding": f"{hour_ending:02d}",
                    "DSTFlag": False,
                    "SettlementPointName": point,
                    "SettlementPointType": "HU" if point.startswith("HB_") else "LZ",
                    "SettlementPointPrice": round(price, 2),
                    "data_label": "SYNTHETIC",
                }
            )
        forecast_rows.append(
            {
                "DeliveryDate": day.isoformat(),
                "HourEnding": hour_ending,
                "DSTFlag": "N",
                "SystemTotal": round(_load_total(index, hour_ending) - (11000 if index == SPIKE_INDEX else 0), 1),
                "Model": "SYNTHETIC_IN_USE",
                "InUseFlag": "Y",
                "data_label": "SYNTHETIC",
            }
        )
        shadow_rows.append(
            {
                "DeliveryDate": day.isoformat(),
                "HourEnding": hour_ending,
                "DSTFlag": "N",
                "ConstraintName": "SYNTHETIC_CONSTRAINT",
                "ShadowPrice": 90.0 if index == SPIKE_INDEX else 4.0,
                "data_label": "SYNTHETIC",
            }
        )
    return {
        "load_weather_zone": load_rows,
        "wind_hourly": wind_rows,
        "solar_hourly": solar_rows,
        "rt_spp": price_rows,
        "load_forecast_weather": forecast_rows,
        "sced_shadow": shadow_rows,
    }


def load_synthetic_observations() -> list[Observation]:
    tables = build_raw_tables()
    observations: list[Observation] = []
    for key, rows in tables.items():
        observations.extend(
            normalize_rows(
                rows,
                by_key(key),
                ingested_at=INGESTED_AT,
                is_synthetic=True,
                raw_ref=SCENARIO_ID,
            )
        )
    return observations


def load_synthetic_frame():
    return observations_frame(load_synthetic_observations())
