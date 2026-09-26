"""Computed insight cards for the Overview — non-obvious signals from the window."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from gridsignal.analytics.features import pivot_series
from gridsignal.services.pipeline import PipelineResult


@dataclass(frozen=True)
class InsightCard:
    eyebrow: str
    title: str
    body: str
    tone: str  # teal | amber | coral | steel


def build_insight_cards(result: PipelineResult) -> list[InsightCard]:
    cards: list[InsightCard] = []
    hub = pivot_series(result.observations, "spp_usd_per_mwh", "HB_HUBAVG")
    houston = pivot_series(result.observations, "spp_usd_per_mwh", "LZ_HOUSTON")
    west = pivot_series(result.observations, "spp_usd_per_mwh", "LZ_WEST")
    load = pivot_series(result.observations, "load_mw_total", "TOTAL")
    wind = pivot_series(result.observations, "wind_gen_mw", "SYSTEM")

    if not hub.empty and not houston.empty:
        spread = (houston.reindex(hub.index) - hub).dropna()
        if not spread.empty:
            stamp = spread.abs().idxmax()
            value = float(spread.loc[stamp])
            cards.append(
                InsightCard(
                    eyebrow="Congestion tell",
                    title=f"{value:+.1f} $/MWh hub–Houston gap",
                    body=(
                        f"Peak absolute spread at {pd.Timestamp(stamp).strftime('%b %d %H:%MZ')}. "
                        "A single hub chart hides this — zones diverge when the transmission system binds."
                    ),
                    tone="coral",
                )
            )

    if not load.empty and not wind.empty:
        aligned = pd.concat([load.rename("load"), wind.rename("wind")], axis=1).dropna()
        if len(aligned) >= 12:
            load_med = aligned["load"].rolling(12, min_periods=8).median()
            wind_med = aligned["wind"].rolling(12, min_periods=8).median()
            load_std = aligned["load"].rolling(12, min_periods=8).std().replace(0, pd.NA)
            wind_std = aligned["wind"].rolling(12, min_periods=8).std().replace(0, pd.NA)
            load_z = (aligned["load"] - load_med) / load_std
            wind_z = (aligned["wind"] - wind_med) / wind_std
            coincident = aligned[(load_z > 1.5) & (wind_z < -1.5)]
            cards.append(
                InsightCard(
                    eyebrow="Co-move",
                    title=f"{len(coincident)} hour(s): load up + wind down",
                    body=(
                        "Hours where load sits high and wind sits low vs each series' own recent past. "
                        "Most viewers plot one line; the joint oddness is the signal."
                    ),
                    tone="amber",
                )
            )

    if not hub.empty:
        peak_price = float(hub.max())
        trough = float(hub.min())
        cards.append(
            InsightCard(
                eyebrow="Price range",
                title=f"${trough:.0f} → ${peak_price:.0f} /MWh hub",
                body=(
                    f"HB_HUBAVG swung ${peak_price - trough:.0f}/MWh across this window. "
                    "Battery Lab asks whether a constrained fleet could have captured any of that."
                ),
                tone="teal",
            )
        )

    if not result.anomalies.empty:
        counts = result.anomalies["category"].value_counts()
        top = str(counts.index[0])
        cards.append(
            InsightCard(
                eyebrow="Anomaly mix",
                title=f"{top.replace('_', ' ').title()} leads ({int(counts.iloc[0])})",
                body=(
                    f"{len(result.anomalies)} flags total across {len(counts)} categories. "
                    "Open Anomaly Explorer for past-only baselines and evidence IDs."
                ),
                tone="steel",
            )
        )

    idle = result.simulations.get("idle")
    hybrid = result.simulations.get("hybrid")
    oracle = result.simulations.get("oracle_price")
    if idle and hybrid:
        idle_val = idle.summary.get("net_energy_value_usd")
        hybrid_val = hybrid.summary.get("net_energy_value_usd")
        if idle_val is not None and hybrid_val is not None:
            delta = float(hybrid_val) - float(idle_val)
            cards.append(
                InsightCard(
                    eyebrow="Fleet delta",
                    title=f"Hybrid vs idle: {delta:+,.0f} $ ledger",
                    body=(
                        "Illustrative MWh×price only — not market impact. "
                        + (
                            f"Oracle benchmark: ${oracle.summary.get('net_energy_value_usd'):,.0f}."
                            if oracle and oracle.summary.get("net_energy_value_usd") is not None
                            else "Compare strategies in Battery Lab."
                        )
                    ),
                    tone="teal",
                )
            )

    if not west.empty and not hub.empty:
        west_spread = (west.reindex(hub.index) - hub).dropna()
        if not west_spread.empty and not houston.empty:
            h_spread = (houston.reindex(hub.index) - hub).dropna()
            cards.append(
                InsightCard(
                    eyebrow="Zone texture",
                    title="Houston and West disagree with the hub differently",
                    body=(
                        f"Houston mean gap {h_spread.mean():+.1f} $/MWh; West mean gap {west_spread.mean():+.1f}. "
                        "Geography shows up in settlement even when the headline hub looks calm."
                    ),
                    tone="steel",
                )
            )

    return cards[:6]
