"""ERCOT product registry.

Artifact URL slugs are stored only when an official page or an ERCOT staff
reply published them. Everything else is resolved at runtime from the product
catalog (``GET /api/public-reports/{emilId}``), which is the documented discovery
flow. A missing optional product does not stop the app.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from gridsignal.data.schemas import SeriesKind

OFFICIAL_GUIDE = "https://developer.ercot.com/applications/pubapi/user-guide/using-api/"
RELEASE_NOTES = "https://developer.ercot.com/applications/pubapi/relnotes/"
KNOWN_LIMITS = "https://developer.ercot.com/applications/pubapi/known-limits/"
XSD_URL = "https://www.ercot.com/files/docs/2026/07/10/Current-Day-Reporting-CDR-XSD.txt"
EMIL_HOME = "https://www.ercot.com/mp/data-products"


class ValueColumn(BaseModel):
    column: str
    aliases: list[str] = Field(default_factory=list)
    series: str
    kind: SeriesKind
    unit: str
    unit_note: str
    location: str | None = None
    location_column: str | None = None


class DatasetSpec(BaseModel):
    key: str
    emil_id: str
    name: str
    required_for_mvp: bool
    mvp: bool
    verification: str
    documentation_url: str
    candidate_path: str | None = None
    candidate_status: str = "not_verified"
    granularity: str
    geographic: str
    frequency_note: str
    auth: str = "Subscription key + Bearer ID token"
    file_formats: str = "JSON via API; product metadata also lists zip, csv, xml"
    contributes: str
    limitations: str
    value_columns: list[ValueColumn]


def _emil(product_id: str) -> str:
    return f"https://www.ercot.com/mp/data-products/data-product-details?id={product_id}"


def datasets() -> list[DatasetSpec]:
    mw_note = (
        "XSD types the value as xs:decimal and does not declare a unit facet. "
        "GridSignal labels MW because the official element name or report title "
        "describes power or load. Confirm against the live field list before publishing numbers."
    )
    price_note = (
        "XSD types SettlementPointPrice as xs:decimal with no currency facet. "
        "Labeled USD/MWh as the ERCOT nodal settlement-price convention. "
        "Not reconfirmed against a live row in this repo."
    )
    return [
        DatasetSpec(
            key="load_weather_zone",
            emil_id="NP6-345-CD",
            name="Actual System Load by Weather Zone",
            required_for_mvp=True,
            mvp=True,
            verification=(
                "EMIL id and name are in the 2023 beta release notes. "
                "XSD element ACTUALSYSLOADWZS (report type 13101) was parsed from the "
                "official Current Day Reports XSD. Artifact slug was NOT in the official "
                "pages fetched for this project; resolve it from the product catalog."
            ),
            documentation_url=_emil("NP6-345-CD"),
            candidate_path=None,
            candidate_status="discover_from_catalog",
            granularity="Hourly, hour-ending",
            geographic="Weather zones plus ERCOT total",
            frequency_note="EMIL page: Chron - Daily. Public audience.",
            contributes="Load level, load ramps, and the load component of grid stress.",
            limitations="Posted after the operating day. Not a real-time telemetry feed.",
            value_columns=[
                ValueColumn(
                    column=name,
                    aliases=[name.lower(), name.replace("_", ""), camel],
                    series=f"load_mw_{name.lower()}",
                    kind=SeriesKind.ACTUAL,
                    unit="MW",
                    unit_note=mw_note,
                    location=name,
                )
                for name, camel in (
                    ("COAST", "coast"),
                    ("EAST", "east"),
                    ("FAR_WEST", "farWest"),
                    ("NORTH", "north"),
                    ("NORTH_C", "northC"),
                    ("SOUTHERN", "southern"),
                    ("SOUTH_C", "southC"),
                    ("WEST", "west"),
                    ("TOTAL", "total"),
                )
            ],
        ),
        DatasetSpec(
            key="wind_hourly",
            emil_id="NP4-732-CD",
            name="Wind Power Production - Hourly Averaged Actual and Forecasted Values",
            required_for_mvp=True,
            mvp=True,
            verification=(
                "EMIL id is in the 2023 beta release notes and the 2024-R9 artifact update. "
                "XSD element names were parsed. Live catalog resolved "
                "np4-732-cd/wpp_hrly_avrg_actl_fcast; live fields use genSystemWide."
            ),
            documentation_url=_emil("NP4-732-CD"),
            granularity="Hourly",
            geographic="System-wide and load zones (South-Houston, West, North)",
            frequency_note="Current-day public report. See EMIL for the posting clock.",
            contributes="Wind ramps, forecast-versus-actual divergence, renewable stress.",
            limitations=(
                "STWPF and WGRPP are forecasts published in the same report as actuals. "
                "Do not treat a forecast column as metered generation."
            ),
            value_columns=[
                ValueColumn(
                    column="SYSTEM_WIDE_GEN",
                    aliases=["genSystemWide", "SYSTEMWIDEGEN"],
                    series="wind_gen_mw",
                    kind=SeriesKind.ACTUAL,
                    unit="MW",
                    unit_note=mw_note,
                    location="SYSTEM",
                ),
                ValueColumn(
                    column="STWPF_SYSTEM_WIDE",
                    aliases=["STWPFSystemWide"],
                    series="wind_forecast_stwpf_mw",
                    kind=SeriesKind.FORECAST,
                    unit="MW",
                    unit_note=mw_note + " STWPF is a forecast field in the XSD, not an actual.",
                    location="SYSTEM",
                ),
                ValueColumn(
                    column="WGRPP_SYSTEM_WIDE",
                    aliases=["WGRPPSystemWide"],
                    series="wind_forecast_wgrpp_mw",
                    kind=SeriesKind.FORECAST,
                    unit="MW",
                    unit_note=mw_note,
                    location="SYSTEM",
                ),
            ],
        ),
        DatasetSpec(
            key="solar_hourly",
            emil_id="NP4-737-CD",
            name="Solar Power Production - Hourly Averaged Actual and Forecasted Values",
            required_for_mvp=True,
            mvp=True,
            verification=(
                "EMIL id in release notes. Live catalog resolved "
                "np4-737-cd/spp_hrly_avrg_actl_fcast; live fields use genSystemWide."
            ),
            documentation_url=_emil("NP4-737-CD"),
            granularity="Hourly",
            geographic="System-wide in the base hourly report",
            frequency_note="Current-day public report.",
            contributes="Solar shape, renewable ramps, forecast divergence.",
            limitations="Regional solar is a different product (NP4-745-CD), not this one.",
            value_columns=[
                ValueColumn(
                    column="SYSTEM_WIDE_GEN",
                    aliases=["genSystemWide", "SYSTEMWIDEGEN"],
                    series="solar_gen_mw",
                    kind=SeriesKind.ACTUAL,
                    unit="MW",
                    unit_note=mw_note,
                    location="SYSTEM",
                ),
                ValueColumn(
                    column="STPPF_SYSTEM_WIDE",
                    aliases=["STPPFSystemWide"],
                    series="solar_forecast_stppf_mw",
                    kind=SeriesKind.FORECAST,
                    unit="MW",
                    unit_note=mw_note + " STPPF is a forecast field.",
                    location="SYSTEM",
                ),
                ValueColumn(
                    column="PVGRPP_SYSTEM_WIDE",
                    aliases=["PVGRPPSystemWide"],
                    series="solar_forecast_pvgrpp_mw",
                    kind=SeriesKind.FORECAST,
                    unit="MW",
                    unit_note=mw_note,
                    location="SYSTEM",
                ),
            ],
        ),
        DatasetSpec(
            key="rt_spp",
            emil_id="NP6-905-CD",
            name="Settlement Point Prices at Resource Nodes, Hubs and Load Zones",
            required_for_mvp=True,
            mvp=True,
            verification=(
                "EMIL id and name are in the 2023 beta release notes. Live catalog resolved "
                "np6-905-cd/spp_node_zone_hub. settlementPoint equality filter confirmed live."
            ),
            documentation_url=_emil("NP6-905-CD"),
            granularity="Settlement interval. XSD includes DeliveryHour and DeliveryInterval.",
            geographic="Resource nodes, hubs, and load zones. Filter before download.",
            frequency_note="Real-time settlement prices. High cardinality if unfiltered.",
            contributes="Price level, ramps, hub-zone spreads, battery economics.",
            limitations=(
                "Live pulls average the four DeliveryInterval prices within each hour. "
                "Unfiltered node files are large; GridSignal requests named hubs/zones only."
            ),
            value_columns=[
                ValueColumn(
                    column="SettlementPointPrice",
                    aliases=["settlementPointPrice"],
                    series="spp_usd_per_mwh",
                    kind=SeriesKind.PRICE,
                    unit="USD/MWh",
                    unit_note=price_note,
                    location_column="SettlementPointName",
                )
            ],
        ),
        DatasetSpec(
            key="dam_spp",
            emil_id="NP4-190-CD",
            name="DAM Settlement Point Prices",
            required_for_mvp=False,
            mvp=False,
            verification=(
                "Endpoint published in an ERCOT GitHub discussion that quotes the API, "
                "and the download parameter was confirmed by ERCOT staff (mackermann-ercot). "
                "Not re-fetched by GridSignal."
            ),
            documentation_url=_emil("NP4-190-CD"),
            candidate_path="/np4-190-cd/dam_stlmnt_pnt_prices",
            candidate_status="staff_discussion",
            granularity="Hourly day-ahead",
            geographic="Resource nodes, load zones, trading hubs",
            frequency_note="Event - Per DAM Run, from the quoted product payload.",
            contributes="Optional day-ahead price context. Not used by the default demo.",
            limitations="Day-ahead prices are not a substitute for real-time settlement prices.",
            value_columns=[
                ValueColumn(
                    column="SettlementPointPrice",
                    aliases=["settlementPointPrice"],
                    series="dam_spp_usd_per_mwh",
                    kind=SeriesKind.PRICE,
                    unit="USD/MWh",
                    unit_note=price_note,
                    location_column="SettlementPoint",
                )
            ],
        ),
        DatasetSpec(
            key="load_forecast_weather",
            emil_id="NP3-565-CD",
            name="Seven-Day Load Forecast by Model and Weather Zone",
            required_for_mvp=False,
            mvp=True,
            verification="EMIL id in the 2023 beta release notes. XSD fields parsed. Slug not verified.",
            documentation_url=_emil("NP3-565-CD"),
            granularity="Hourly, by forecast model",
            geographic="Weather zones plus system total",
            frequency_note="Seven-day forecast. Multiple models; honor InUseFlag when present.",
            contributes="Forecast-versus-actual load divergence.",
            limitations="A forecast is not an actual. Models can disagree.",
            value_columns=[
                ValueColumn(
                    column="SystemTotal",
                    series="load_forecast_mw",
                    kind=SeriesKind.FORECAST,
                    unit="MW",
                    unit_note=mw_note,
                    location="SYSTEM",
                )
            ],
        ),
        DatasetSpec(
            key="sced_shadow",
            emil_id="NP6-86-CD",
            name="SCED Shadow Prices and Binding Transmission Constraints",
            required_for_mvp=False,
            mvp=True,
            verification="EMIL id in the 2023 beta release notes. XSD fields parsed. Slug not verified.",
            documentation_url=_emil("NP6-86-CD"),
            granularity="SCED timestamp",
            geographic="Constraint (from/to station), not a load zone",
            frequency_note="SCED-interval constraints. Can be wide.",
            contributes="Binding-constraint and shadow-price anomalies when the pull succeeds.",
            limitations=(
                "Optional. If the catalog lookup fails, stress is computed without congestion "
                "and marked incomplete for that component."
            ),
            value_columns=[
                ValueColumn(
                    column="ShadowPrice",
                    series="shadow_price",
                    kind=SeriesKind.CONSTRAINT,
                    unit="USD/MWh",
                    unit_note=price_note + " Shadow-price unit facet is also absent from the XSD.",
                    location_column="ConstraintName",
                )
            ],
        ),
        DatasetSpec(
            key="outage_capacity",
            emil_id="NP3-233-CD",
            name="Hourly Resource Outage Capacity",
            required_for_mvp=False,
            mvp=False,
            verification=(
                "Official user-guide example. Endpoint "
                "https://api.ercot.com/api/public-reports/np3-233-cd/hourly_res_outage_cap"
            ),
            documentation_url=OFFICIAL_GUIDE,
            candidate_path="/np3-233-cd/hourly_res_outage_cap",
            candidate_status="official_user_guide",
            granularity="Hourly, next 168 hours",
            geographic="Load zones",
            frequency_note="Chron - Hourly, from the official example payload.",
            contributes="Optional outage context. Not required for the demo.",
            limitations="Outage Scheduler aggregate. The report says it does not use telemetry.",
            value_columns=[
                ValueColumn(
                    column="TotalResourceMWZoneHouston",
                    series="outage_mw",
                    kind=SeriesKind.OUTAGE,
                    unit="MW",
                    unit_note="Element name includes MW.",
                    location="HOUSTON",
                )
            ],
        ),
        DatasetSpec(
            key="system_adequacy",
            emil_id="NP3-763-CD",
            name="Short-Term System Adequacy",
            required_for_mvp=False,
            mvp=False,
            verification="Listed in the 2025-R11 release notes and present in the XSD. Slug not verified.",
            documentation_url=RELEASE_NOTES,
            granularity="Hourly adequacy snapshot",
            geographic="South, North, West, Houston plus totals",
            frequency_note="Re-released with RTC+B in December 2025.",
            contributes="Optional reserve context. Excluded from the default score until a live pull is mapped.",
            limitations="Do not describe this as an official GridSignal reliability rating.",
            value_columns=[
                ValueColumn(
                    column="AvailCapReserve",
                    series="available_reserve_mw",
                    kind=SeriesKind.ADEQUACY,
                    unit="MW",
                    unit_note=mw_note,
                    location="SYSTEM",
                )
            ],
        ),
        DatasetSpec(
            key="esr_4sec",
            emil_id="RPTESR-M",
            name="Energy Storage Resource Four Second Data",
            required_for_mvp=False,
            mvp=False,
            verification=("2025-R5 release notes: Get /rptesr-m/4_sec_esr_charging_mw. Field list was not retrieved."),
            documentation_url=RELEASE_NOTES,
            candidate_path="/rptesr-m/4_sec_esr_charging_mw",
            candidate_status="official_release_notes",
            granularity="4 seconds",
            geographic="Not verified in this repo",
            frequency_note="Very high volume. Off by default.",
            contributes="Context for how storage actually behaved. Not used by BatteryBrain.",
            limitations=(
                "Four-second data will blow the rate limit if pulled carelessly. "
                "BatteryBrain is a simulation and does not read or send setpoints to ESRs."
            ),
            value_columns=[],
        ),
    ]


def mvp_datasets() -> list[DatasetSpec]:
    return [item for item in datasets() if item.mvp]


def by_key(key: str) -> DatasetSpec:
    for item in datasets():
        if item.key == key:
            return item
    raise KeyError(key)
