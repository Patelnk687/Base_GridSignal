# ERCOT data sources

Research date: 2026-09-25. This file separates what GridSignal verified from what it only saw named in documentation. It does not invent endpoints.

ERCOT does not endorse GridSignal. Public ERCOT data is used under [ERCOT's website terms](https://www.ercot.com/help/terms) and the [Data Access Portal terms](https://www.ercot.com/help/terms/data-portal).

## What was tested from this machine

| Check | Result |
| --- | --- |
| `POST` token endpoint with a registered API Explorer account | HTTP 200. Body contained `token_type=Bearer`, `expires_in=3600`, `id_token`, `access_token`, and `refresh_token`. Tokens were not stored. |
| `GET https://api.ercot.com/api/public-reports` with `Authorization: Bearer <id_token>` and no subscription key | HTTP 401. `WWW-Authenticate: AzureApiManagementKey ... name="Ocp-Apim-Subscription-Key"`. Body: access denied due to missing subscription key. |
| Same call with `access_token` | Same HTTP 401. |
| API Explorer sign-in in the automation browser | Blocked. Azure AD B2C reported that cookies are blocked, so the Profile Primary key was not retrieved. |
| Current Day Reports XSD | Downloaded from the official URL below and parsed locally for element names. |
| Live report rows | Not fetched. No subscription key was available. |

## Authentication

Official guide: [Registration and Authentication](https://developer.ercot.com/applications/pubapi/user-guide/registration-and-authentication/).

1. Create an account at [API Explorer](https://apiexplorer.ercot.com/).
2. Subscribe to the Public API product and copy the **Primary key** from Profile. That value is `ERCOT_SUBSCRIPTION_KEY`. It is not the account password.
3. Obtain an ID token with `POST` and `Content-Type: application/x-www-form-urlencoded`.

| Item | Verified value |
| --- | --- |
| Token URL | `https://ercotb2c.b2clogin.com/ercotb2c.onmicrosoft.com/B2C_1_PUBAPI-ROPC-FLOW/oauth2/v2.0/token` |
| `grant_type` | `password` |
| `scope` | `openid fec253ea-0d06-4272-a5e6-b478baeecd70 offline_access` |
| `client_id` | `fec253ea-0d06-4272-a5e6-b478baeecd70` (published in the guide, not a user secret) |
| `response_type` | `id_token` |
| Lifetime | 3600 seconds. The guide says an ID token cannot be refreshed. GridSignal requests a new token. |
| API header | `Authorization: Bearer <id_token>` |
| Key header | `Ocp-Apim-Subscription-Key: <primary key>` |

The Python sample on that page reads `access_token`. The prose says to send the ID token. GridSignal sends `id_token`. A client secret is not part of this flow, so `ERCOT_CLIENT_SECRET` is not used.

Put credentials in `.env`. Do not commit that file and do not paste the subscription key into chat.

## Limits

Official page: [Known limitations](https://developer.ercot.com/applications/pubapi/known-limits/).

- 30 requests per minute. HTTP 429 body is `{"error_key":"throttled","error_message":"Too Many Requests"}`.
- Historic file downloads: 1,000 files at a time.
- Requests from outside the United States to `*.ercot.com` are blocked.
- API row downloads start at each product's Public API activation date. Older history is historic files, retained at least 7 years.
- [Portal terms](https://www.ercot.com/help/terms/data-portal) limit repeat downloads of the same report. Cache responses and request only missing date ranges.

ERCOT staff on GitHub ([discussion 107](https://github.com/ercot/api-specs/discussions/107)) said the default page size is 1,000 and that `size` and `page` select pages. Staff also described `{field}From` / `{field}To` filters ([discussion 48](https://github.com/ercot/api-specs/discussions/48), [discussion 102](https://github.com/ercot/api-specs/discussions/102)). GridSignal adds a ranged filter only when the report metadata marks that field `hasRange`.

## Catalog, not guessed slugs

| URL | Status |
| --- | --- |
| `GET https://api.ercot.com/api/public-reports` | Official user-guide example |
| `GET https://api.ercot.com/api/public-reports/{emilId}` | Same example, `self` link pattern |
| Artifact href inside `artifacts[]._links.endpoint.href` | Official example for NP3-233-CD |

Published artifact paths GridSignal will use if the catalog call fails:

| Product | Path | Why it is stored |
| --- | --- | --- |
| NP3-233-CD Hourly Resource Outage Capacity | `/np3-233-cd/hourly_res_outage_cap` | Official user-guide response |
| NP4-190-CD DAM Settlement Point Prices | `/np4-190-cd/dam_stlmnt_pnt_prices` | API payload quoted in an ERCOT GitHub thread; staff confirmed `deliveryDateFrom` and `download` |
| RPTESR-M four-second ESR charging | `/rptesr-m/4_sec_esr_charging_mw` | 2025-R5 release notes. Fields not retrieved. Off by default. |

Wind geo path `/np4-742-cd/wpp_hrly_actual_fcast_geo` was posted by ERCOT staff in discussion 102. It is not on the default MVP list.

Community libraries publish other slugs, including NP6-345-CD and NP6-905-CD. Those slugs are **not** hardcoded here. The client reads them from the catalog after a subscription key is present.

## MVP products

The demo runs without these. Live mode resolves them from the catalog.

XSD: [Current-Day-Reporting-CDR-XSD.txt](https://www.ercot.com/files/docs/2026/07/10/Current-Day-Reporting-CDR-XSD.txt), version 8.3, namespace `http://www.ercot.com/schema/2009-01/nodal/cdr`. The XSD types numbers as `xs:decimal` and does not declare a unit facet. `MW` in an element name is explicit. Generation and price units below are labeled from the report title plus ERCOT market convention and are flagged in code as such.

### NP6-345-CD Actual System Load by Weather Zone

- Docs: [EMIL](https://www.ercot.com/mp/data-products/data-product-details?id=NP6-345-CD), [release notes](https://developer.ercot.com/applications/pubapi/relnotes/)
- Report type id 13101. XSD element `ACTUALSYSLOADWZS`.
- Fields: `OperDay`, `HourEnding`, `DSTFlag`, `COAST`, `EAST`, `FAR_WEST`, `NORTH`, `NORTH_C`, `SOUTHERN`, `SOUTH_C`, `WEST`, `TOTAL`.
- Hourly. Weather zones plus ERCOT total. EMIL: Chron - Daily, public, zip/csv/xml.
- Use: load level and ramps.
- Limit: not real-time telemetry. Artifact slug not verified in this repo.

### NP4-732-CD Wind Power Production, hourly actual and forecast

- Release notes (2023 beta and 2024-R9). XSD element includes `DELIVERY_DATE`, `HOUR_ENDING`, `SYSTEM_WIDE_GEN`, `STWPF_SYSTEM_WIDE`, `WGRPP_SYSTEM_WIDE`, plus load-zone twins and `DSTFlag`.
- `SYSTEM_WIDE_GEN` is treated as actual. `STWPF` and `WGRPP` are forecasts.
- Use: wind ramps and forecast divergence.
- Limit: slug not verified here. Unit facet absent from the XSD.

### NP4-737-CD Solar Power Production, hourly actual and forecast

- Same release-note status. Fields: `DELIVERY_DATE`, `HOUR_ENDING`, `SYSTEM_WIDE_GEN`, `STPPF_SYSTEM_WIDE`, `PVGRPP_SYSTEM_WIDE`, `SYSTEM_WIDE_HSL`, `DSTFlag`.
- Regional solar is NP4-745-CD, not this product.

### NP6-905-CD Settlement Point Prices at Resource Nodes, Hubs and Load Zones

- Release notes. XSD `SPPatHubsLoadZones`: `DeliveryDate`, `DeliveryHour`, `DeliveryInterval`, `DSTFlag`, `SettlementPointName`, `SettlementPointType`, `SettlementPointPrice`.
- Use: price level, hub-zone spread, battery economics. Filter to hubs and load zones. Do not pull every resource node.
- Limit: `DeliveryInterval` was not mapped to a 15-minute offset because that meaning was not verified on a live row. The normalizer timestamps the hour and flags `subhour_interval_unresolved` when the column is present. Price unit is labeled USD/MWh by market convention, not by an XSD facet.

### Optional, still registered

| ID | Name | Role | Verified |
| --- | --- | --- | --- |
| NP3-565-CD | Seven-Day Load Forecast by Model and Weather Zone | Forecast vs actual | ID and XSD fields. Slug not verified. |
| NP6-86-CD | SCED Shadow Prices and Binding Transmission Constraints | Congestion context | ID and XSD fields (`ShadowPrice`, `ConstraintName`, `SCEDTimeStamp`, `RepeatedHourFlag`). Slug not verified. |
| NP3-233-CD | Hourly Resource Outage Capacity | Outage context | Official example endpoint. |
| NP4-190-CD | DAM Settlement Point Prices | Day-ahead context | Staff-discussed endpoint. Fields from a quoted metadata payload: `deliveryDate`, `hourEnding`, `settlementPoint`, `settlementPointPrice`, `DSTFlag`. |
| NP3-763-CD | Short-Term System Adequacy | Reserves | Named in 2025-R11 and the XSD. Not in the default score. |
| RPTESR-M | Four-second ESR charging | Actual storage behavior | Path in release notes. Too granular for the demo. BatteryBrain does not control these resources. |

## Hour-ending convention used by GridSignal

Documented in [MODEL_METHODOLOGY.md](MODEL_METHODOLOGY.md). Hour ending 1..24 in `America/Chicago`, with the November repeated hour-ending 2 distinguished by `DSTFlag`. Hour ending 2 on the March spring-forward morning raises an error instead of being shifted.

## Demo data

`SYNTHETIC-STRESS-001` is generated by `gridsignal.data.sample_data`. Every row has `is_synthetic=true`. It is not ERCOT history. A small export can be written under `data/sample/` for inspection. Live responses, tokens, and `.env` stay out of git.
