"""Physical battery and fleet assumptions.

Defaults describe a generic residential battery for the demo. They are not
measurements of any vendor fleet, including Base.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class BatterySpec(BaseModel):
    name: str = "assumed-residential"
    capacity_kwh: float = 13.5
    max_charge_kw: float = 5.0
    max_discharge_kw: float = 5.0
    min_soc_fraction: float = 0.10
    max_soc_fraction: float = 1.0
    charge_efficiency: float = 0.95
    discharge_efficiency: float = 0.95
    degradation_usd_per_kwh: float = 0.0
    reserve_fraction: float = 0.20
    initial_soc_fraction: float = 0.50
    assumption_note: str = "Illustrative residential battery. Not a claim about Base's installed fleet."

    @model_validator(mode="after")
    def _check(self) -> BatterySpec:
        if self.capacity_kwh <= 0:
            raise ValueError("capacity_kwh must be positive")
        if self.max_charge_kw < 0 or self.max_discharge_kw < 0:
            raise ValueError("power limits cannot be negative")
        if not 0 < self.charge_efficiency <= 1 or not 0 < self.discharge_efficiency <= 1:
            raise ValueError("efficiencies must be in (0, 1]")
        if not 0 <= self.min_soc_fraction <= self.max_soc_fraction <= 1:
            raise ValueError("state-of-charge bounds are inconsistent")
        if not self.min_soc_fraction <= self.reserve_fraction <= self.max_soc_fraction:
            raise ValueError("reserve fraction must lie inside the state-of-charge bounds")
        if not self.min_soc_fraction <= self.initial_soc_fraction <= self.max_soc_fraction:
            raise ValueError("initial state of charge is outside bounds")
        return self

    @property
    def min_soc_kwh(self) -> float:
        return self.min_soc_fraction * self.capacity_kwh

    @property
    def max_soc_kwh(self) -> float:
        return self.max_soc_fraction * self.capacity_kwh

    @property
    def reserve_kwh(self) -> float:
        return self.reserve_fraction * self.capacity_kwh


class FleetSpec(BaseModel):
    count: int = 1000
    battery: BatterySpec = Field(default_factory=BatterySpec)

    @model_validator(mode="after")
    def _check_count(self) -> FleetSpec:
        if self.count < 1:
            raise ValueError("fleet count must be at least 1")
        return self
