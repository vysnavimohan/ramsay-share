# Asset Inventory — Ramsay Shift-Cover demo

This package is **self-contained**. It reads no source workspace — every object ships as a captured
artefact (`ddl/`, `artefacts/dashboard.json`, `artefacts/genie.json`, `data/`, `MANIFEST.json`) and
is remapped from its **origin** `ramsay_workforce.allocate` onto your target catalog/schema at build
time.

## ⛔ NEVER TOUCH (teardown/build must never mutate these)

If you deploy alongside the companion Group-Operations demo, keep its catalog out of scope. The
`never_touch` widget guards teardown so it refuses to drop these.

| Asset | Id / name |
|---|---|
| Catalog | `ramsay_health` (the Group-Operations demo) |
| Dashboard | `01f19ed4cd0a…` (Group Operations, 5 Hospitals) |
| Genie — Capacity | `01f19d06b568…` |
| Genie — Patient Activity & Finance | `01f19d067c20…` |
| Genie — Throughput & Flow | `01f19d0660ed…` |
| Genie — Workforce (Group Ops) | `01f19d069acb…` |

## Carry set (13 objects) — built onto your target

6 base tables (`vwah_hoursassignment`, `vwah_unavailability`, `dim_site`, `dim_grade_payrate`,
`dim_site_synonym`, `cover_decisions`), 3 views, 1 materialized view (`mv_gap_candidates`),
2 metric views (`mv_shift_fulfilment`, `mv_absence`), 1 SQL function (`fn_find_replacements`).
Full graph + row counts in `MANIFEST.json`.

## Deliverables (created new on your target; ids written to `deployment_manifest.json`)

| Deliverable | Built by | Recorded as |
|---|---|---|
| App `ramsay-shift-cover` (FastAPI+React) | `06_deploy_app` | `app.name` / `.url` / `.sp` / `.deployment_id` |
| Dashboard "Ramsay Workforce & Absence — Executive" | `04_build_dashboard` | `dashboard.id` / `.url` |
| Genie space "Ramsay Workforce — Nurse Replacement" (24 instructions) | `05_build_genie` | `genie.GENIE_WORKFORCE.space_id` / `.url` |

Serving state is the UC table `cover_decisions` (no Lakebase): `lakebase.applicable = false`.
The app's AI co-worker uses the `databricks-gpt-oss-120b` FM endpoint (rule-based fallback if absent).

## Data payload

`data/<table>/*.parquet` — 6 tables, ~564 KB. Row counts: `vwah_hoursassignment` 26,924 ·
`vwah_unavailability` 862 · `dim_site_synonym` 23 · `dim_site` 8 · `dim_grade_payrate` 6 ·
`cover_decisions` 0.
