"""SQLite response cache and coverage planner.

Identical queries are not downloaded twice. Coverage ranges let a caller
request only the missing dates.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS response_cache (
            cache_key TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            params_json TEXT NOT NULL,
            stored_at TEXT NOT NULL,
            body TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS coverage (
            dataset_key TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            PRIMARY KEY (dataset_key, start_date, end_date)
        )
        """
    )
    return conn


def cache_key(url: str, params: dict[str, Any]) -> str:
    payload = json.dumps({"url": url, "params": params}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ResponseCache:
    def __init__(self, path: Path) -> None:
        self.path = path

    def get(self, url: str, params: dict[str, Any]) -> dict[str, Any] | None:
        key = cache_key(url, params)
        with _connect(self.path) as conn:
            row = conn.execute(
                "SELECT body FROM response_cache WHERE cache_key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def put(self, url: str, params: dict[str, Any], body: dict[str, Any]) -> None:
        key = cache_key(url, params)
        now = datetime.now(UTC).isoformat()
        with _connect(self.path) as conn:
            conn.execute(
                """
                INSERT INTO response_cache (cache_key, url, params_json, stored_at, body)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    stored_at = excluded.stored_at,
                    body = excluded.body
                """,
                (key, url, json.dumps(params, sort_keys=True, default=str), now, json.dumps(body)),
            )

    def record_coverage(self, dataset_key: str, start: date, end: date) -> None:
        with _connect(self.path) as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO coverage (dataset_key, start_date, end_date)
                VALUES (?, ?, ?)
                """,
                (dataset_key, start.isoformat(), end.isoformat()),
            )

    def covered(self, dataset_key: str) -> list[tuple[date, date]]:
        with _connect(self.path) as conn:
            rows = conn.execute(
                "SELECT start_date, end_date FROM coverage WHERE dataset_key = ? ORDER BY start_date",
                (dataset_key,),
            ).fetchall()
        return [(date.fromisoformat(a), date.fromisoformat(b)) for a, b in rows]


def _merge(ranges: list[tuple[date, date]]) -> list[tuple[date, date]]:
    if not ranges:
        return []
    ordered = sorted(ranges)
    merged: list[tuple[date, date]] = [ordered[0]]
    for start, end in ordered[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end + timedelta(days=1):
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged


def missing_ranges(
    start: date,
    end: date,
    covered: list[tuple[date, date]],
) -> list[tuple[date, date]]:
    """Return inclusive date gaps inside ``start``..``end`` that are not covered."""
    if end < start:
        raise ValueError("end date is before start date")
    gaps: list[tuple[date, date]] = []
    cursor = start
    for cov_start, cov_end in _merge(covered):
        if cov_end < cursor:
            continue
        if cov_start > end:
            break
        if cov_start > cursor:
            gaps.append((cursor, min(end, cov_start - timedelta(days=1))))
        cursor = max(cursor, cov_end + timedelta(days=1))
        if cursor > end:
            return gaps
    if cursor <= end:
        gaps.append((cursor, end))
    return gaps
