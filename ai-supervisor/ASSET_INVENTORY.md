# Asset Inventory — Ramsay AI-Supervisor (Group Operations) demo

This package is **self-contained**. It reads no source workspace — every object ships as a captured
artefact (`ddl/`, `artefacts/dashboard.json`, `artefacts/genie.json`, `data/`, `MANIFEST.json`) and
is remapped from its **origin** `ramsay_health.ops` onto your target catalog/schema at build time.

## ⛔ NEVER TOUCH (teardown/build must never mutate these)

If you deploy alongside the companion Shift-Cover demo, keep its catalog out of scope. The
`never_touch` widget guards teardown so it refuses to drop these.

| Asset | Id / name |
|---|---|
| Catalog | `ramsay_workforce` (the Shift-Cover demo) |
| Dashboard "Workforce & Absence — Executive" | `01f19bd24692…` |
| Genie "Workforce — Nurse Replacement" | `01f19b8fda6e…` |

## Carry set (23 objects) — built onto your target

10 base tables (`dim_site`, `fact_bed_day`, `fact_diagnostic_slot`, `fact_theatre_session`,
`fc_admissions`, `tbbillvisit`, `tbinvoice`, `tbreferrals`, `tbwlmds`, `vwah_hoursassignment`),
8 views (`vw_finance_base`, `vw_bed_occupancy`, `vw_theatre_throughput`, `vw_diagnostic_capacity`,
`vw_capacity_forecast`, `vw_waiting_list`, `vw_readmissions`, `vw_referral_flow`), 5 metric views
(`mv_theatre_util`, `mv_bed_occupancy`, `mv_finance_margin`, `mv_patient_activity`,
`mv_workforce_hours`). Full graph + row counts in `MANIFEST.json`.

## Deliverables (created new on your target; ids written to `deployment_manifest.json`)

| Deliverable | Built by | Recorded as |
|---|---|---|
| App `ramsay-ai-supervisor` (React + FastAPI) | `06_deploy_app` | `app.*` |
| Dashboard "Ramsay Health — Group Operations (5 Hospitals)" | `04_build_dashboard` | `dashboard.id` / `.url` |
| 4 Genie agents (Capacity · Patient Activity & Finance · Throughput & Flow · Workforce) | `05_build_genie` | `genie.GENIE_*.space_id` / `.url` |
| Lakebase instance + seeded chat history (required) | `05b_provision_lakebase` | `lakebase.*` |

### Genie agents (env var → title)
| Env var | Title |
|---|---|
| `GENIE_CAPACITY` | Ramsay Capacity |
| `GENIE_PATIENT_FINANCE` | Ramsay Patient Activity & Finance |
| `GENIE_THROUGHPUT_FLOW` | Ramsay Throughput & Flow |
| `GENIE_WORKFORCE` | Ramsay Workforce |

**Genie One:** the app's live conversational Q&A needs a Claude model that may be unavailable in
your region (e.g. fevm-azure). The spaces still build; the live answer path degrades where absent.

## Data payload

`data/<table>/*.parquet` — 10 tables, ~41 MB. Largest: `tbwlmds` 311,166 · `tbreferrals` 311,166 ·
`vwah_hoursassignment` 83,393 · `tbbillvisit` 72,243 · `tbinvoice` 66,862.
