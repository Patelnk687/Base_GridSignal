"""Persist a local ERCOT week snapshot for offline demos."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

DEFAULT_SNAPSHOT_DIR = Path("data/live")
OBSERVATIONS_NAME = "week_observations.csv"
META_NAME = "week_meta.json"


def snapshot_paths(root: Path | None = None) -> tuple[Path, Path]:
    base = root or DEFAULT_SNAPSHOT_DIR
    return base / OBSERVATIONS_NAME, base / META_NAME


def snapshot_exists(root: Path | None = None) -> bool:
    obs_path, meta_path = snapshot_paths(root)
    return obs_path.is_file() and meta_path.is_file()


def save_snapshot(
    observations: pd.DataFrame,
    *,
    scenario_id: str,
    warnings: list[str],
    root: Path | None = None,
) -> Path:
    if observations.empty:
        raise ValueError("refusing to save an empty snapshot")
    obs_path, meta_path = snapshot_paths(root)
    obs_path.parent.mkdir(parents=True, exist_ok=True)
    frame = observations.copy()
    frame.to_csv(obs_path, index=False)
    stamps = pd.to_datetime(frame["timestamp_utc"], utc=True)
    meta = {
        "scenario_id": scenario_id,
        "saved_at_utc": datetime.now(UTC).isoformat(),
        "row_count": int(len(frame)),
        "timestamp_start_utc": stamps.min().isoformat(),
        "timestamp_end_utc": stamps.max().isoformat(),
        "sources": sorted(frame["source_id"].dropna().unique().tolist()),
        "series": sorted(frame["series"].dropna().unique().tolist()),
        "warnings": warnings,
        "synthetic": False,
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return obs_path


def load_snapshot(root: Path | None = None) -> tuple[pd.DataFrame, dict[str, object]]:
    obs_path, meta_path = snapshot_paths(root)
    if not obs_path.is_file() or not meta_path.is_file():
        raise FileNotFoundError(
            f"No live snapshot at {obs_path}. Run: python -m gridsignal.tools.refresh_live_snapshot"
        )
    frame = pd.read_csv(obs_path)
    frame["timestamp_utc"] = pd.to_datetime(frame["timestamp_utc"], utc=True)
    if "ingested_at_utc" in frame.columns:
        frame["ingested_at_utc"] = pd.to_datetime(frame["ingested_at_utc"], utc=True)
    if "quality_flags" in frame.columns:
        frame["quality_flags"] = frame["quality_flags"].map(_parse_flags)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return frame, meta


def _parse_flags(value: object) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    text = str(value).strip()
    if not text or text == "[]":
        return []
    # CSV round-trip of a Python list literal.
    if text.startswith("[") and text.endswith("]"):
        try:
            import ast

            parsed = ast.literal_eval(text)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except (SyntaxError, ValueError):
            pass
    return [text]
