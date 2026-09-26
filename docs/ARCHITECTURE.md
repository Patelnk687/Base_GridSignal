# Architecture

GridSignal is one Python package and a Streamlit app. There is no separate API service.

```text
app.py
  ui/dashboard.py
    pages: overview, anomalies, battery lab, replay, data quality
  services/pipeline.py
    data/sample_data.py or data/ercot_client.py
    data/normalization.py
    analytics/anomaly_detection.py
    analytics/grid_stress.py
    analytics/forecasting.py
    battery/fleet.py
    explain/templates.py
```

## Modes

- `demo` (default): bundled synthetic scenario. No network.
- `live`: used only when `ERCOT_USERNAME`, `ERCOT_PASSWORD`, and `ERCOT_SUBSCRIPTION_KEY` are all set. Otherwise the pipeline stays on the demo series and says so.

## Data flow

1. Rows arrive either from the sample builder or from a cached ERCOT page (`fields` + `data`).
2. Normalization emits long-form observations: UTC timestamp, original local text, source id, location, series, kind (`actual`, `forecast`, `price`, `constraint`), unit, and quality flags.
3. Anomaly rules and the stress score read past-only rolling statistics.
4. Battery strategies see the current interval and, except the labeled oracle, no later prices.
5. Explanations cite evidence ids drawn from those rows.

## Persistence

SQLite at `data/cache/ercot.sqlite` stores response bodies and covered date ranges. Auth tokens stay in memory. The cache directory is gitignored.

## What is measured, modeled, and generated

| Kind | Examples |
| --- | --- |
| Measured | ERCOT report fields, once a live pull succeeds |
| Constructed | `SYNTHETIC-STRESS-001` |
| Modeled | GridSignal stress score, battery SOC, illustrative dollars |
| Generated | Template sentences. Optional Ollama text is kept only if every claim cites a known evidence id |

The stress score is not an ERCOT reliability rating. Simulated dispatch does not change ERCOT prices and is not sent to any battery.
