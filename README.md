# GridSignal

ERCOT grid intelligence and a virtual home-battery fleet, built for the Base AI Talent Hackathon, Track 1: Open Grid Data.

GridSignal loads grid measurements, flags unusual intervals with a past-only baseline, explains them from the numbers that were actually present, and simulates how a configurable battery fleet could have charged or discharged. The simulation is analytical. It does not control hardware, submit bids, or change ERCOT prices.

**Live demo:** [Streamlit Cloud](https://basegridsignaltabreadme-ov-file-mobbixbp7vrkxx7jckakjd.streamlit.app/) · short write-up: [docs/WRITEUP.md](docs/WRITEUP.md)

ERCOT does not endorse this project. Public data remains subject to [ERCOT's terms](https://www.ercot.com/help/terms).

## Features

- Anomaly detection on load, wind, solar, settlement prices, hub-zone spreads, and optional constraint shadow prices
- GridSignal Stress Indicator with published weights and a completeness flag
- BatteryBrain strategies: idle, fixed schedule, causal price arbitrage, stress response, hybrid, and a labeled perfect-foresight oracle
- Evidence-backed explanations that run without an LLM
- Streamlit dashboard with replay and a data-quality page
- Optional ERCOT Public API client with token handling, pacing, retries, and a SQLite cache

The default demo uses `SYNTHETIC-STRESS-001`. That series is constructed. It is not ERCOT history.

## Architecture

```text
Streamlit (app.py)
        |
        v
pipeline: normalize -> anomalies -> stress -> fleet -> explanations
        |
        +-- sample data (demo)
        +-- ERCOT client -> SQLite cache (live, optional)
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Screenshots

Placeholders until a demo capture is added:

- <img width="1532" height="686" alt="image" src="https://github.com/user-attachments/assets/b033e8fc-b756-4b6b-ba21-f0a1a4833dd0" />
` — stress, load, prices

- <img width="1538" height="688" alt="image" src="https://github.com/user-attachments/assets/8e20e757-68d2-474f-af6f-69dd77c1066b" />
 — evidence panel
 
- <img width="1727" height="862" alt="image" src="https://github.com/user-attachments/assets/8882f683-75e1-4896-a124-f6f47fef93dd" />
 — strategy comparison

 <img width="1767" height="987" alt="image" src="https://github.com/user-attachments/assets/601b937f-ef95-416c-8b09-7056565414bc" />
https://basegridsignaltabreadme-ov-file-mobbixbp7vrkxx7jckakjd.streamlit.app/

## How the models work

Anomaly baselines are rolling medians of earlier intervals only. The stress score renormalizes when an input is missing and is not an ERCOT reliability rating. Battery energy balance is enforced in the simulator. Dollars are price times simulated MWh.

Details: [docs/MODEL_METHODOLOGY.md](docs/MODEL_METHODOLOGY.md).

## Install on Windows 11

PowerShell, from this directory:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -e .
copy .env.example .env
streamlit run app.py
```

Python 3.11 or newer works. This repo was exercised on 3.13.

Git Bash is the same flow with `source .venv/Scripts/activate` and `cp .env.example .env`.

## ERCOT API setup

Live pulls are optional. Demo mode does not need them.

1. Register at [API Explorer](https://apiexplorer.ercot.com/).
2. Subscribe to the Public API and copy the Profile **Primary key**.
3. Put the account email, password, and primary key in `.env` as `ERCOT_USERNAME`, `ERCOT_PASSWORD`, and `ERCOT_SUBSCRIPTION_KEY`.
4. Set `GRIDSIGNAL_DATA_MODE=live`.

The published client id is already in `.env.example`. There is no client secret in ERCOT's documented ROPC flow. Tokens last one hour. The client requests a new one. It does not log the password or the key.

Product notes and the list of endpoints that were and were not verified: [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md).

## Demo mode

```powershell
$env:GRIDSIGNAL_DATA_MODE = "demo"
streamlit run app.py
```

A 4-minute walkthrough is in [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md).

## Tests

```powershell
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m ruff check src tests app.py
```

## Limitations

- Without a subscription key, no live ERCOT rows are loaded. The dashboard badge stays on the synthetic scenario.
- Several MVP artifact slugs are discovered from the product catalog at runtime and are not hardcoded, because they were not in the official examples fetched for this repo.
- NP6-905-CD sub-hour `DeliveryInterval` is not converted to a quarter-hour until a live row confirms that convention.
- The seasonal-naive price error is a holdout score on the series in memory. It is not a claim of forecast skill.
- Shadow-price and reserve products are optional. A missing component makes the stress score `incomplete`.
- Optional Ollama explanations are rejected unless each claim cites a provided evidence id.

## License

MIT. See [LICENSE](LICENSE).
