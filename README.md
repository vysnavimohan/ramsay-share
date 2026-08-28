# Ramsay Demo Handover — Notebook-Driven Packages

Two self-contained Ramsay demo packages you deploy with **manual uploads + Databricks notebooks**.
Neither reads any source workspace — every object ships as a captured artefact and is remapped onto
your target catalog/schema at build time.

| Package | What it stands up |
|---|---|
| [`shift-cover/`](shift-cover/00_START_HERE.md) | Shift-Cover demo — 13 UC objects + AI/BI dashboard + Genie space + FastAPI/React app |
| [`ai-supervisor/`](ai-supervisor/00_START_HERE.md) | AI-Supervisor / Group Operations — 23 UC objects + dashboard + 4 Genie agents + optional Lakebase + React/FastAPI supervisor app |

## How to deploy (both packages, same shape)
1. Add this repo as a **Git folder** in your Databricks workspace (or import the package folder).
2. **⚙️ Set the widgets FIRST** — see the next section. This is where you choose the catalog, schema
   and Volume. The notebooks do **not** prompt you; they read these widgets.
3. Run `00_preflight` to confirm your selection + workspace readiness.
4. Run `01_validate_shipped` → `01b_stage_data_to_volume` (copies the shipped `data/` into your
   Volume — no laptop) → `02_create_schema` → `03_load_data` → `04_build_dashboard` →
   `05_build_genie`.
5. **Upload the app**: `app.zip` → a workspace folder, unzip it, set `app_source_path`, run
   `06_deploy_app`.
6. Run `99_verify`. Every stage is **idempotent** and self-verifies.
7. When done, run `99_teardown` to remove everything (the catalog is never dropped).

See each package's **`00_START_HERE.md`** for the click-by-click.

## ⚙️ Set these parameters ONCE in `00_preflight`

Widgets live **only on `00_preflight`**. Set them, run that notebook, and it **saves your choices to
`deploy_config.json`** in the package folder. Every later notebook (`01 → 06`, `99_*`) reads that
file automatically — **you never set widgets again.** To change a value, edit it in `00_preflight`
and re-run that notebook.

| Widget | What to enter | Example |
|---|---|---|
| `target_catalog` | an **existing** catalog (the package creates only a *schema* inside it — it never creates a catalog) | `classic_stable_82ujqz` |
| `target_schema` | the schema to build the demo into (created if absent) | `ramsay_demo_test` |
| `warehouse_id` | a running SQL warehouse id | `7464666eb7d50c27` |
| `staging_volume` | the UC Volume the parquet is staged into, as `catalog.schema.volume` | `classic_stable_82ujqz.ramsay_demo_test.ramsay_demo_test` |
| `data_volume_path` | the `/Volumes/...` path for that Volume (usually auto-derived; set it if your Volume name differs from the default `_staging`) | `/Volumes/classic_stable_82ujqz/ramsay_demo_test/ramsay_demo_test` |
| `app_name` | Databricks App name (≤30 chars) | `ramsay-shift-cover` |
| `app_source_path` | (Stage 06 only) the workspace folder where you unzipped `app.zip` | `/Workspace/Users/you/ramsay-shift-cover-app` |
| `fm_endpoint` | Foundation-model endpoint for the app | `databricks-gpt-oss-120b` |
| `never_touch` | catalogs/ids `99_teardown` must never remove | `ramsay_health` |

> **Create the schema + Volume yourself, or let 01b do it.** `01b_stage_data_to_volume` will
> `CREATE SCHEMA IF NOT EXISTS` + `CREATE VOLUME IF NOT EXISTS` for you and copy the data in. If you
> created them by hand first, just point the widgets at what you made.
> If your Volume name is **not** the default `_staging` (e.g. you named it `ramsay_demo_test`), set
> **both** `staging_volume` and `data_volume_path` explicitly so the notebooks find the data.

## Requirements
- A **target catalog that already exists** (the packages create only a *schema* inside it).
- A running **SQL warehouse**.
- FM endpoint `databricks-gpt-oss-120b` for the apps' LLM (they degrade gracefully without it).

> **Genie One** (the AI-Supervisor's live conversational Q&A) needs a Claude model that is not
> available in every region. The spaces, dashboard, tables and app still build and deploy there;
> only the live answer path degrades — reported as a WARN, never a failure.
