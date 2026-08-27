# AI-Supervisor Demo Handover Package — Specification (notebook-driven, self-contained)

**This demo:** Ramsay AI-Supervisor / Group Operations (5 hospitals).
**Package:** `ai-supervisor/` — `notebooks/00..06 + 05b + 99_verify + 99_teardown` + shipped `ddl/`,
`artefacts/`, `data/`, `app.zip`, `MANIFEST.json`, `seed_questions.sql`.

> The package stands up the entire demo in a Databricks workspace from **manual uploads +
> notebooks**. It is **self-contained**: it reads **no source workspace**. Every object ships as a
> captured artefact and is remapped from its **origin** `ramsay_health.ops` onto your
> `target_catalog.target_schema` at build time. Deploy / manual steps are in `00_START_HERE.md`.

## 1. Purpose

Let any engineer stand up the AI-Supervisor demo in their own workspace by (a) **uploading two
files** — the parquet `data/` payload to a UC Volume and `app.zip` to a workspace folder — and (b)
running a sequence of **Databricks notebooks** that create the schema, load the 10 base tables,
build the 8 views + 5 metric views, publish the dashboard, recreate the 4 Genie agents, optionally
provision Lakebase, and deploy the supervisor app. Every stage is **idempotent** with an inline
verify. A `99_teardown` notebook removes everything cleanly.

## 2. Design principles

- **Self-contained** — no source workspace read; ships DDL + parquet + dashboard/Genie JSON.
- **Remap, don't reuse** — origin `ramsay_health.ops` → your target everywhere (unquoted,
  backtick-quoted, and bare-schema forms).
- **IDs are outputs** — new dashboard/Genie/app/Lakebase ids → `deployment_manifest.json`.
- **Idempotent** — `CREATE OR REPLACE` for tables/views/metric-views; `DROP … IF EXISTS` + `CREATE`
  for materialized views; `TRUNCATE` + `COPY INTO … force=true` for data; reuse-or-update the
  dashboard; delete-then-recreate the 4 Genie spaces; GET-then-redeploy the app.
- **Non-destructive** — teardown never drops the catalog; refuses to run against `never_touch`.
- **Catalog pre-exists** — the package creates only the *schema* inside an existing catalog.

## 3. Carry set — 23 objects

10 base tables · 8 views · 5 metric views. Data-bearing tables (parquet, 10, ~41 MB) ship in
`data/`; views + metric views recompute. Full graph + row counts in `MANIFEST.json`.

## 4. Package layout

```
ai-supervisor/
├── 00_START_HERE.md            manual upload steps + notebook run order
├── SPEC.md · ASSET_INVENTORY.md · DEMO_SCRIPT.md · screenshots/
├── MANIFEST.json               carry set + types + dependency edges + row counts
├── deployment_manifest.json    OUTPUT: new target ids (starts empty)
├── ddl/                        23 captured CREATE statements (origin-qualified; remapped at build)
├── artefacts/
│   ├── dashboard.json          captured serialized dashboard
│   └── genie.json              4 agents — tables + instructions + sample questions
├── data/                       parquet payload (~41 MB) — upload to your Volume
├── seed_questions.sql          Lakebase starter prompts (optional Stage 05b)
├── app.zip                     supervisor app source (React + FastAPI) — upload + unzip
└── notebooks/
    ├── _common                 widgets + WorkspaceClient auth + SQL(warehouse) + remap/idempotency
    ├── 00_preflight            auth, UC, catalog-exists, warehouse, FM endpoint
    ├── 01_validate_shipped     confirm shipped ddl/parquet/manifest are consistent
    ├── 02_create_schema        create schema + all 23 objects (idempotent)
    ├── 03_load_data            COPY INTO from the uploaded Volume parquet + refresh metric views
    ├── 04_build_dashboard      publish dashboard from artefacts/dashboard.json
    ├── 05_build_genie          recreate the 4 Genie agents from artefacts/genie.json
    ├── 05b_provision_lakebase  optional Lakebase + seed_questions (no-op if lakebase_instance blank)
    ├── 06_deploy_app           app.yaml (4 Genie ids + Lakebase host) + apps deploy + SP grants
    ├── 99_verify               end-to-end check + prints deliverable URLs
    └── 99_teardown             remove app/lakebase/genie/dashboard + DROP SCHEMA CASCADE (catalog kept)
```

## 5. Stages (each has an inline verify)

| # | Notebook | Does | Verify |
|---|---|---|---|
| 00 | `00_preflight` | identity; UC; **catalog exists**; warehouse; FM endpoint. | no hard failures |
| 01 | `01_validate_shipped` | shipped carry set present + consistent. | dependency-closed; DDL non-empty; parquet present |
| 02 | `02_create_schema` | schema inside existing catalog; remap + run DDL for 23 objects. | all 23 present |
| 03 | `03_load_data` | `COPY INTO` from uploaded Volume parquet; refresh metric views. | row counts == manifest; MEASURE on `mv_bed_occupancy` |
| 04 | `04_build_dashboard` | publish dashboard (reuse-or-update). | target schema only + published + reachable |
| 05 | `05_build_genie` | recreate 4 agents (delete-then-recreate). | instructions applied; Capacity smoke test (WARN if Genie One absent) |
| 05b | `05b_provision_lakebase` | optional Lakebase + 4 seed questions. | seed_questions has 4 rows (skipped if blank) |
| 06 | `06_deploy_app` | app.yaml (4 Genie ids + Lakebase host) + create + grant SP + SNAPSHOT deploy. | app RUNNING + URL < 500 |
| 99 | `99_verify` / `99_teardown` | end-to-end verify; or full teardown (catalog kept). | all live / all gone, catalog intact |

## 6. Serving

Optional Lakebase (Autoscaling Postgres) holds a `seed_questions` table (4 starter prompts). Blank
`lakebase_instance` ⇒ Stage 05b is a no-op and the app runs without starter prompts.

## 7. Genie One caveat

The supervisor's live conversational Q&A ("Genie One") needs a Claude model that is not available in
every region (e.g. fevm-azure). The 4 spaces + dashboard + tables + app still build and deploy; only
the live answer path degrades where the model is absent. This is reported as a WARN, never a failure.

## 8. Configuration (widgets in `notebooks/_common`)

`target_catalog` (existing), `target_schema` (new), `warehouse_id`, `staging_volume`,
`data_volume_path`, `app_name`, `app_source_path`, `fm_endpoint`, `lakebase_instance` (blank=skip),
`never_touch`. No profile and no source keys.
