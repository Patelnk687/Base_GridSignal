"""Refresh the local 7-day ERCOT snapshot used for offline demos.

Usage:
    python -m gridsignal.tools.refresh_live_snapshot
"""

from __future__ import annotations

from gridsignal.config import load_settings
from gridsignal.data.snapshot import save_snapshot
from gridsignal.services.live_ingest import observations_from_live


def main() -> None:
    settings = load_settings()
    if not settings.live_credentials_ready:
        raise SystemExit(
            "Need ERCOT_USERNAME, ERCOT_PASSWORD, and ERCOT_SUBSCRIPTION_KEY in .env"
        )
    print(f"Pulling last {settings.live_lookback_days} days from ERCOT…", flush=True)
    observations, warnings, scenario_id = observations_from_live(
        settings,
        days=settings.live_lookback_days,
    )
    path = save_snapshot(observations, scenario_id=scenario_id, warnings=warnings)
    print(f"Saved {len(observations)} rows → {path}", flush=True)
    print(f"scenario_id={scenario_id}", flush=True)
    for warning in warnings:
        print(f"  note: {warning}", flush=True)
    print("Set GRIDSIGNAL_DATA_MODE=snapshot to demo from this file without API calls.", flush=True)


if __name__ == "__main__":
    main()
