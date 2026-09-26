# Offline ERCOT week snapshot

`week_observations.csv` + `week_meta.json` are a real Public API pull
(scenario id like `LIVE-2026-09-19_to_2026-09-26`).

Set `GRIDSIGNAL_DATA_MODE=snapshot` (local `.env` or Streamlit Cloud Secrets)
so the app loads this week instead of `SYNTHETIC-STRESS-001`.

Refresh locally:

```bash
python -m gridsignal.tools.refresh_live_snapshot
```
