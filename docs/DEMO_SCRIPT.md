# Demo script (about 4 minutes)

Run `streamlit run app.py` with `GRIDSIGNAL_DATA_MODE=demo`. No API key is required. Leave the SYNTHETIC badge visible.

1. **What this is.** GridSignal finds unusual patterns in ERCOT-style grid series, shows the measurements behind them, and simulates a fleet of home batteries. It does not operate batteries, trade, or claim to move ERCOT prices.
2. **Provenance.** Open Data Quality. The scenario id is `SYNTHETIC-STRESS-001`. Say clearly that the bundled series is constructed. If a live cache exists later, point at the source id and the last fetch time instead, and do not call the synthetic file history.
3. **Replay.** Open Historical Replay and drag the slider to the evening spike (load up, wind down, hub price up, Houston zone wider than the hub). Read the stress score and the sentence under it. Mention that missing inputs are dropped, not treated as normal.
4. **Anomaly.** Open Anomaly Explorer, select the price spike, and read Facts, then Interpretation, then Hypothesis. The hypothesis says the series moved together and that this does not establish a cause.
5. **Fleet.** Open Battery Lab. Show idle, causal price arbitrage, stress response, and hybrid. Point at charge MWh, discharge MWh, losses, and ending SOC. Note violation count is zero. If you show oracle price, say it peeks at later prices and is a benchmark only.
6. **Economics.** The dollar column is simulated energy times the interval price. It is not a settlement statement and not a claim that the fleet reduced prices.
7. **Limits.** Stress is a GridSignal score. The default battery is an assumption, not Base's fleet. Live ERCOT pulls need a subscription key and are cached. The seasonal-naive MAE on the demo series is not a forecast-skill claim.

Stop. Do not imply ERCOT endorsed the project.
