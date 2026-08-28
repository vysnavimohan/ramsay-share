# Ramsay AI-Supervisor (Group Operations) — Notebook Deployment (START HERE)

Stand up the AI-Supervisor demo in your Databricks workspace by **running a set of notebooks** —
everything (data, app, artefacts) ships inside the package, so there is nothing to upload by hand.
The package is fully self-contained — it reads **no source workspace**. Every object (23 UC objects
+ AI/BI dashboard + 4 Genie agents + supervisor app) ships as a captured artefact and is remapped
onto your target catalog/schema at build time.

## The deliverables
1. **AI-Supervisor App** `ramsay-ai-supervisor` — React + FastAPI. Decompose → route → 4 Genie
   agents → synthesise, with an SSE answer trace.
2. **AI/BI dashboard** "Ramsay Health — Group Operations (5 Hospitals)".
3. **4 Genie agents** — Capacity · Patient Activity & Finance · Throughput & Flow · Workforce.
4. **Lakebase** serving store + seeded chat history (**required** — the app reads its
   conversation sidebar + starter prompts from Postgres; seeded to mirror UK-South).

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

## Step 2 — The data (parquet, ~41 MB)
The parquet payload ships **inside this Git folder** at **`ai-supervisor/data/`** (10 subfolders,
one per table). Notebook **`01b_stage_data_to_volume`** creates the schema + a UC Volume and copies
it from the Git folder into the Volume — no laptop, no manual upload.

> **Large-file caveat:** this package's data is ~41 MB with a ~26 MB `tbwlmds` parquet. Databricks
> Git folders enforce a per-file size limit, so a large table may not check out. If `01b` reports a
> missing/empty table, upload that table's parquet to the Volume via **Catalog → Volume → Upload**
> (or `databricks fs cp`) so the layout is `/Volumes/<catalog>/<schema>/<volume>/<table>/*.parquet`,
> then re-run 01b (its verify only checks the parquet is on the Volume, however it got there).

## Step 3 — The app (no manual step)
The app source ships inside this package as **`app.zip`**. **Stage 06 extracts and deploys it
automatically** — nothing to upload, unzip, or configure.

## Step 4 — Set the widgets (top of `00_preflight` — the ONLY notebook with widgets)
Just **4** parameters. Everything else is derived or fixed.
| Widget | Meaning | Example |
|---|---|---|
| `target_catalog` | existing catalog | `classic_stable_82ujqz` |
| `target_schema` | schema to create | `ramsay_ai_supervisor` |
| `warehouse_id` | running SQL warehouse | `7464666eb7d50c27` |
| `lakebase_instance` | **required** — Lakebase instance name (app's serving layer) | `ramsay-serving` |

Fixed / derived (you do NOT set these):
- **app name** = `ramsay-ai-supervisor` (hard-coded)
- **staging Volume** = derived to `<catalog>.<schema>._staging` (created inside the target schema)
- **FM endpoint** = `databricks-gpt-oss-120b`; **teardown guard** = `ramsay_workforce`
- **app source** — Stage 06 auto-extracts the bundled `app.zip` (no input)

## Step 5 — Run the notebooks in order
| # | Notebook | Does |
|---|---|---|
| 00 | `00_preflight` | auth, UC, catalog exists, warehouse, FM endpoint |
| 01 | `01_validate_shipped` | confirms shipped DDL + parquet + manifest |
| 01b | `01b_stage_data_to_volume` | creates schema + Volume, copies `data/` from the Git folder into the Volume (no laptop) |
| 02 | `02_create_schema` | creates schema + all 23 objects (idempotent) |
| 03 | `03_load_data` | `COPY INTO` from the staged Volume parquet + refresh metric views |
| 04 | `04_build_dashboard` | publishes the Group-Operations dashboard |
| 05 | `05_build_genie` | recreates the 4 Genie agents; smoke-tests Capacity (WARN if Genie One absent) |
| 05b | `05b_provision_lakebase` | **required** — creates Lakebase instance + seeds chat history from `seed_lakebase.sql` (fails if `lakebase_instance` unset) |
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
