# Shift-Cover Demo Handover Package — Specification (notebook-driven, self-contained)

**Status:** BUILT · notebook conversion of the verified source-free package
**This demo:** Ramsay Shift-Cover — nurse/temp-staff replacement.
**Package:** `shift-cover/` — `notebooks/00..06 + 99_verify + 99_teardown` + shipped `ddl/`,
`artefacts/`, `data/`, `app.zip`, `MANIFEST.json`.

> **How to read this doc.** The package stands up the entire Shift-Cover demo in a Databricks
> workspace from **manual uploads + notebooks**. It is **self-contained**: it reads **no source
> workspace**. Every object ships as a captured artefact and is remapped from its **origin**
> `ramsay_workforce.allocate` onto your `target_catalog.target_schema` at build time. Deploy /
> manual steps are in `00_START_HERE.md`.

---

## 1. Purpose

Let any engineer stand up the demo in their own workspace by (a) **uploading two files** — the
parquet `data/` payload to a UC Volume and `app.zip` to a workspace folder — and (b) running a
sequence of **Databricks notebooks** that create the schema, load the tables, publish the
dashboard, recreate the Genie space, and deploy the app. Every stage is **idempotent** and has an
inline verify. A `99_teardown` notebook removes everything cleanly.

## 2. Design principles

- **Self-contained** — no source workspace read; ships DDL + parquet + dashboard/Genie JSON.
- **Remap, don't reuse** — origin `ramsay_workforce.allocate` → your target everywhere (handles the
  unquoted `cat.sch.obj`, backtick-quoted `` `cat`.`sch`.`obj` ``, and bare `sch.obj` forms).
- **IDs are outputs** — new dashboard/Genie/app ids are written to `deployment_manifest.json`; no
  source id crosses into a target-built object.
- **Idempotent** — `CREATE OR REPLACE` for tables/views/metric-views/functions; `DROP … IF EXISTS`
  + `CREATE` for the materialized view (Spark rejects `OR REPLACE MATERIALIZED VIEW`, and DROP
  releases prior pipeline ownership); `TRUNCATE` + `COPY INTO … force=true` for data; reuse-or-update
  the dashboard; delete-then-recreate the Genie space; GET-then-redeploy the app.
- **Non-destructive** — teardown never drops the catalog and refuses to run against `never_touch`.
- **Catalog pre-exists** — the package creates only the *schema* inside an existing catalog (some
  Default-Storage workspaces reject `CREATE CATALOG` via SQL).

## 3. Carry set — the 13 objects (dependency-closed)

| Layer | Objects |
|---|---|
| Base tables — initial list | `vwah_hoursassignment` (26,924), `vwah_unavailability` (862) |
| Base tables — added | `dim_site` (8), `dim_grade_payrate` (6), `dim_site_synonym` (23), `cover_decisions` (0) |
| Views | `enriched_hoursassignment`, `enriched_unavailability`, `vw_open_gaps` |
| Materialized view | `mv_gap_candidates` |
| Metric views | `mv_shift_fulfilment`, `mv_absence` |
| SQL function | `fn_find_replacements(gap_id BIGINT)` |

Data-bearing tables (parquet, 6, ~564 KB) ship in `data/`; views/MVs/metric-views/function
recompute. The full graph + row counts are in `MANIFEST.json`.

## 4. Package layout

```
shift-cover/
├── 00_START_HERE.md            manual upload steps + notebook run order
├── SPEC.md                     this document
├── ASSET_INVENTORY.md          carry set, deliverables, NEVER-TOUCH
├── MANIFEST.json               carry set + types + dependency edges + row counts
├── deployment_manifest.json    OUTPUT: new target ids (starts empty)
├── ddl/                        13 captured CREATE statements (origin-qualified; remapped at build)
├── artefacts/
│   ├── dashboard.json          captured serialized dashboard
│   └── genie.json              captured Genie tables + 24 instructions
├── data/  (+ data.zip)         parquet payload — upload to your Volume
├── app.zip                     app source (FastAPI + React, prebuilt frontend) — upload + unzip
└── notebooks/
    ├── _common                 widgets + WorkspaceClient auth + SQL(warehouse) + remap/idempotency helpers
    ├── 00_preflight            auth, UC, catalog-exists, warehouse, FM endpoint
    ├── 01_validate_shipped     confirm shipped ddl/parquet/manifest are consistent
    ├── 02_create_schema        create schema + all 13 objects (idempotent)
    ├── 03_load_data            COPY INTO from the uploaded Volume parquet + refresh MV
    ├── 04_build_dashboard      publish dashboard from artefacts/dashboard.json
    ├── 05_build_genie          recreate Genie space + 24 instructions from artefacts/genie.json
    ├── 06_deploy_app           app.yaml + apps deploy + SP grants (from app.zip)
    ├── 99_verify               end-to-end check + prints the 3 deliverable URLs
    └── 99_teardown             remove app/dashboard/genie + DROP SCHEMA CASCADE (catalog kept)
```

## 5. Stages (each has an inline verify)

| # | Notebook | Does | Verify |
|---|---|---|---|
| 00 | `00_preflight` | notebook identity; UC reachable; **target catalog exists**; warehouse present; FM endpoint present else WARN. | no hard failures |
| 01 | `01_validate_shipped` | confirm the shipped carry set (ddl + parquet + manifest) is present + consistent. | dependency-closed; DDL non-empty; parquet present |
| 02 | `02_create_schema` | create the schema inside the existing catalog; remap + run DDL for all 13 objects (idempotent). | all 13 objects present |
| 03 | `03_load_data` | `COPY INTO` from the uploaded Volume parquet; refresh the MV. | row counts == manifest; `MEASURE(total_shifts)` on `mv_shift_fulfilment` |
| 04 | `04_build_dashboard` | publish the dashboard from the shipped definition (reuse-or-update). | references target schema only + published + reachable |
| 05 | `05_build_genie` | recreate the space + 24 instructions (delete-then-recreate). | instructions applied; Conversation-API smoke test answers against target |
| 06 | `06_deploy_app` | `app.yaml` (target warehouse/schema + new Genie id) + create app + grant SP + SNAPSHOT deploy. | app RUNNING + URL HTTP 200 |
| 99 | `99_verify` / `99_teardown` | end-to-end verify; or full teardown (catalog kept). | all deliverables live / all gone, catalog intact |

## 6. Serving

Shift-Cover has **no Lakebase**. Its only stateful surface is the `cover_decisions` UC table (the
outreach/decision ledger), carried as data in Stage 03. Canonical Genie questions live inside the
Genie space's 24 instructions (carried in Stage 05) — there is no separate `seed_questions` table.

## 7. Configuration (widgets in `00_preflight` only)

Just **3** parameters: `target_catalog` (existing), `target_schema` (new), `warehouse_id`. Set in
`00_preflight`, saved to `deploy_config.json`, reused by every later notebook. **Fixed / derived
(not asked):** app name = `ramsay-shift-cover`; staging Volume derived to `<catalog>.<schema>._staging`;
FM endpoint = `databricks-gpt-oss-120b`; teardown guard = `ramsay_health`. `app_source_path` is a
Stage-06-only widget. No profile, no source keys — the notebook authenticates as its own runtime identity.
