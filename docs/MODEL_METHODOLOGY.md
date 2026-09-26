# Model methodology

## Timestamps

Internal timestamps are timezone-aware UTC. The source delivery date, hour ending, and DST flag are kept on the observation.

Hour ending `N` ends at `N:00` in `America/Chicago`. Hour ending 24 ends at midnight at the start of the next civil day.

On the November fallback, `01:00` local is ambiguous and `02:00` local is not. ERCOT still publishes two hour-ending 2 rows. GridSignal maps:

- `DSTFlag` false: end of the first occurrence, equal to 01:00 standard time (`fold=1`)
- `DSTFlag` true: 02:00 standard time

Checked against `zoneinfo` for 2024-11-03: 07:00 UTC, then 08:00 UTC.

On the March spring-forward morning, 02:00 does not exist. Hour ending 2 raises `LocalTimeError`. It is not moved to 03:00.

`DeliveryInterval` on NP6-905-CD is preserved as a quality flag (`subhour_interval_unresolved`) until a live row confirms the quarter-hour convention. Missing numbers stay null.

## Anomalies

For a point at time t, the baseline is the rolling median of values strictly before t. The scale is the rolling median absolute deviation of those past residuals. The modified z-score is `0.6745 * (x - median) / MAD`.

A point is flagged only when the absolute deviation clears a category floor (for example $40/MWh or 1,500 MW) and the modified z clears 3.5. If the past MAD is zero, z is undefined; the point is flagged only when the absolute floor is cleared, and the explanation says the MAD was zero. Severity is `low`, `moderate`, or `high`. None of these words mean an ERCOT emergency.

Isolation Forest is a comparison. It is fit on a prefix and scores only the suffix.

Events inside 90 minutes share a correlation group. The text says the overlap is temporal, not causal.

## GridSignal Stress Indicator

Weights, as a starting point rather than a fit:

| Component | Weight | Definition |
| --- | --- | --- |
| load_level | 0.25 | Positive modified z of system load, clipped at z=4 |
| load_ramp | 0.15 | Positive MW change / 8,000, clipped at 100 |
| renewable_drop | 0.20 | Wind-plus-solar drop / 6,000 MW, clipped at 100 |
| price_level | 0.25 | Positive modified z of HB_HUBAVG, clipped at z=4 |
| price_change | 0.15 | Positive price change / $150 per MWh, clipped at 100 |

The 8,000 MW, 6,000 MW, and $150 scales are display assumptions so a large move maps near 100. They are not ERCOT thresholds.

If a component is missing, its weight is removed and the others are renormalized. Completeness is the share of weight that could be computed. The status is `incomplete` when any component is missing and `unavailable` when none can be computed. Missing is never replaced with zero.

## Forecast

The only price model is seasonal naive: the value 24 intervals earlier. MAE is computed on the last 12 intervals of the series being scored. That number is an in-sample demo diagnostic. It is not evidence that the model predicts future ERCOT prices.

## BatteryBrain

Default device, labeled as an assumption: 13.5 kWh, 5 kW charge, 5 kW discharge, SOC 10–100%, reserve 20%, one-way efficiency 95%, initial SOC 50%. A fleet is that device repeated `count` times. This is not a description of Base hardware.

Grid-side charge energy times charge efficiency is added to SOC. Energy removed from SOC is grid discharge divided by discharge efficiency. Power is clipped to the inverter limits and to the SOC headroom. Discharge stops at the reserve. Charge and discharge are never both positive. Interval length is the UTC gap between timestamps (1 hour for the first point).

Strategies:

| Name | Information used |
| --- | --- |
| idle | None |
| fixed_schedule | Local hour ending only |
| price_arbitrage | Prices through the current interval. Needs a $1/MWh gap between the 30th and 70th percentiles and at least 6 prices. |
| grid_stress | Current GridSignal score. Discharge at or above 70 if above reserve. Charge at or below 25. |
| hybrid | Stress discharge first, otherwise the causal price rule |
| oracle_price | Percentiles of the entire series, including later intervals. Labeled perfect foresight. |

Dollars are the sum of simulated MWh times the interval settlement price, minus an optional degradation term that defaults to zero. There is no price-impact counterfactual.

## Explanations

Template text is assembled from the anomaly record and evidence items. Facts, interpretation, and hypotheses are separate. If `GRIDSIGNAL_LLM_PROVIDER=ollama`, the prompt contains evidence records only. A response is kept only when every claim cites an evidence id that was sent. Otherwise the template is shown.
