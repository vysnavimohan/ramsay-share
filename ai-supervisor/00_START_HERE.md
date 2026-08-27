# Ramsay AI-Supervisor (Group Operations) — Notebook Deployment (START HERE)

Stand up the AI-Supervisor demo in your Databricks workspace by **uploading two files by hand**
and then **running a set of notebooks**. The package is fully self-contained — it reads **no source
workspace**. Every object (23 UC objects + AI/BI dashboard + 4 Genie agents + supervisor app) ships
as a captured artefact and is remapped onto your target catalog/schema at build time.

## The deliverables
1. **AI-Supervisor App** `ramsay-ai-supervisor` — React + FastAPI. Decompose → route → 4 Genie
   agents → synthesise, with an SSE answer trace.
2. **AI/BI dashboard** "Ramsay Health — Group Operations (5 Hospitals)".
3. **4 Genie agents** — Capacity · Patient Activity & Finance · Throughput & Flow · Workforce.
4. *(optional)* **Lakebase** serving store + `seed_questions` starter prompts.

---

## Prerequisites
- A **target catalog that already exists** (the package creates only a *schema* inside it). Default
  widget: `classic_stable_82ujqz`.
- A **running SQL warehouse** (id → `warehouse_id` widget).
- The Foundation-Model endpoint `databricks-gpt-oss-120b` in your region (the app's LLM).

### ⚠️ Genie One availability
The app's **live conversational Q&A** ("Genie One") needs a Claude model that is **not available in
every region** (including fevm-azure). The 4 Genie spaces, dashboard, tables and app all still
**build and deploy**; only the live conversational answer path degrades where the model is absent.
Nothing in the notebooks hard-fails on this — it is reported as a WARN. Demo the dashboard + Genie
spaces directly there.

---

## Step 1 — Get this package into your workspace
Add this repo as a **Git folder** (`https://github.com/vysnavimohan/ramsay-share`) or import the
`ai-supervisor/` folder. Notebooks resolve sibling `ddl/`, `artefacts/`, `MANIFEST.json` from their
own path — keep the structure intact.

## Step 2 — Manual upload: the data (parquet, ~41 MB)
Upload this package's **`data/`** folder into a target **UC Volume** (e.g.
`<catalog>.<schema>._staging`) so the layout is `/Volumes/<catalog>/<schema>/_staging/<table>/*.parquet`.
Stage 03 creates the staging Volume if it doesn't exist — run it once, upload, re-run. Point the
`data_volume_path` widget at that base if it isn't the default staging Volume.

## Step 3 — Manual upload: the app (zip, ~14 MB)
Upload **`app.zip`** into your workspace and **unzip** it to a folder, e.g.
`/Workspace/Users/<you>/ramsay-ai-supervisor-app`. Set the `app_source_path` widget (Stage 06) to
that folder.

## Step 4 — Set the widgets (top of `notebooks/_common`)
| Widget | Meaning | Example |
|---|---|---|
| `target_catalog` | existing catalog | `classic_stable_82ujqz` |
| `target_schema` | schema to create | `ramsay_ai_supervisor` |
| `warehouse_id` | running SQL warehouse | `7464666eb7d50c27` |
| `staging_volume` / `data_volume_path` | parquet location | |
| `app_name` | app name (≤30) | `ramsay-ai-supervisor` |
| `app_source_path` | unzipped app folder | `/Workspace/Users/you/ramsay-ai-supervisor-app` |
| `fm_endpoint` | app LLM endpoint | `databricks-gpt-oss-120b` |
| `lakebase_instance` | **blank = skip Lakebase** (recommended) | |
| `never_touch` | catalogs/ids teardown must never remove | `ramsay_workforce` |

## Step 5 — Run the notebooks in order
| # | Notebook | Does |
|---|---|---|
| 00 | `00_preflight` | auth, UC, catalog exists, warehouse, FM endpoint |
| 01 | `01_validate_shipped` | confirms shipped DDL + parquet + manifest |
| 02 | `02_create_schema` | creates schema + all 23 objects (idempotent) |
| 03 | `03_load_data` | `COPY INTO` from the uploaded Volume parquet + refresh metric views |
| 04 | `04_build_dashboard` | publishes the Group-Operations dashboard |
| 05 | `05_build_genie` | recreates the 4 Genie agents; smoke-tests Capacity (WARN if Genie One absent) |
| 05b | `05b_provision_lakebase` | optional Lakebase + seed_questions (no-op if `lakebase_instance` blank) |
| 06 | `06_deploy_app` | deploys the supervisor app (4 Genie ids wired, SP grants, SNAPSHOT) |
| 99 | `99_verify` | end-to-end check + prints deliverable URLs |

Every notebook prints `✓` per step. Stages are **idempotent** — safe to re-run.

## Teardown (after your test)
Run **`notebooks/99_teardown`**: deletes the app, the Lakebase project (if any), all 4 Genie spaces,
trashes the dashboard, and `DROP SCHEMA … CASCADE`. **The catalog is never dropped.** Guarded by
`never_touch`; resets `deployment_manifest.json`.

---

### Notes / gotchas
- **Catalog must pre-exist.** The package makes only the schema inside it.
- The 32-hex ids inside `artefacts/*.json` are the **origin** the definitions were captured from;
  they are remapped to your target at build time — no source workspace is contacted.
- Data payload is ~41 MB (`tbwlmds`, `tbreferrals` are the large tables).
