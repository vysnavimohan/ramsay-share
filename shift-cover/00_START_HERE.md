# Ramsay Shift-Cover — Notebook Deployment (START HERE)

Stand up the entire Shift-Cover demo in your Databricks workspace by **running a set of
notebooks** — everything (data, app, artefacts) ships inside the package, so there is nothing to
upload by hand. The package is fully self-contained — it reads **no source workspace**. Every
object (13 UC objects + dashboard + Genie space + app) ships as a captured artefact and is remapped
onto your target catalog/schema at build time.

## The three deliverables
1. **App** `ramsay-shift-cover` — FastAPI + React. Positions-to-fill board (ranked internal cover
   options) + Ask-Genie. AI co-worker uses `databricks-gpt-oss-120b`.
2. **AI/BI dashboard** "Ramsay Workforce & Absence — Executive".
3. **Genie space** "Ramsay Workforce — Nurse Replacement" (24 curated instructions).

---

## Prerequisites
- A **target catalog that already exists** (this package creates only a *schema* inside it — some
  workspaces block `CREATE CATALOG` via SQL). Default in the widgets: `classic_stable_82ujqz`.
- A **running SQL warehouse** (its id goes in the `warehouse_id` widget).
- The Foundation-Model endpoint `databricks-gpt-oss-120b` in your region (optional — the app
  degrades to a rule-based fallback without it).

---

## Step 1 — Get this package into your workspace
Add this repo as a **Git folder** in your workspace (Repos → Add Repo →
`https://github.com/vysnavimohan/ramsay-share`), or import the `shift-cover/` folder. The notebooks
resolve their sibling `ddl/`, `artefacts/`, `MANIFEST.json` automatically from their own path — keep
the folder structure intact.

## Step 2 — The data (parquet) — no laptop needed
The tables load from a parquet snapshot that ships **inside this Git folder** at **`shift-cover/data/`**
(6 subfolders, one per table). Because it's in the repo, Databricks already checked it out into your
workspace when you added the Git folder — you do **not** download to a laptop or upload by hand.

Notebook **`01b_stage_data_to_volume`** creates the schema + a UC Volume and copies
`data/<table>/*.parquet` from the Git folder straight into the Volume (where Stage 03's `COPY INTO`
reads it). Just set the widgets (Step 4) and run 01b — that's it.

> Prefer to do it by hand instead? The staging Volume is always `<target_catalog>.<target_schema>._staging`
> (`01b` creates it). Upload the `data/` subfolders there via **Catalog → Volume → Upload** so the
> layout is `/Volumes/<catalog>/<schema>/_staging/<table>/*.parquet`, and skip 01b.

## Step 3 — The app (no manual step)
The app source ships inside this package as **`app.zip`**. **Stage 06 extracts and deploys it
automatically** — nothing to upload, unzip, or configure.

## Step 4 — Set the widgets (top of `00_preflight` — the ONLY notebook with widgets)
Just **3** parameters. Everything else is derived or fixed.
| Widget | Meaning | Example |
|---|---|---|
| `target_catalog` | existing catalog to build into | `classic_stable_82ujqz` |
| `target_schema` | schema to create (new) | `ramsay_shiftcover` |
| `warehouse_id` | running SQL warehouse | `7464666eb7d50c27` |

Fixed / derived (you do NOT set these):
- **app name** = `ramsay-shift-cover` (hard-coded)
- **staging Volume** = derived to `<catalog>.<schema>._staging` (created inside the target schema by `01b`)
- **FM endpoint** = `databricks-gpt-oss-120b`; **teardown guard** = `ramsay_health`
- **app source** — Stage 06 auto-extracts the bundled `app.zip` (no input)

## Step 5 — Run the notebooks in order
| # | Notebook | Does |
|---|---|---|
| 00 | `00_preflight` | auth, UC, catalog exists, warehouse, FM endpoint |
| 01 | `01_validate_shipped` | confirms shipped DDL + parquet + manifest are consistent |
| 01b | `01b_stage_data_to_volume` | creates schema + Volume, copies `data/` from the Git folder into the Volume (no laptop) |
| 02 | `02_create_schema` | creates schema + all 13 objects (idempotent) |
| 03 | `03_load_data` | `COPY INTO` from the staged Volume parquet + refresh MV |
| 04 | `04_build_dashboard` | publishes the dashboard from the shipped definition |
| 05 | `05_build_genie` | recreates the Genie space + 24 instructions, smoke-tests |
| 06 | `06_deploy_app` | deploys the app (grants SP, SNAPSHOT deploy) |
| 99 | `99_verify` | end-to-end check + prints the 3 deliverable URLs |

Every notebook prints `✓` per step and a `PASS`/summary at the end. Stages are **idempotent** — safe
to re-run any of them.

## Teardown (after your test)
Run **`notebooks/99_teardown`**. It deletes the app, trashes the dashboard, deletes the Genie space,
and `DROP SCHEMA … CASCADE` (dropping the 13 objects + the `_staging` volume). **The catalog is never
dropped.** It refuses to run if `target_schema` is empty or your catalog/schema is in `never_touch`,
and it resets `deployment_manifest.json`.

---

### Notes / gotchas
- **Catalog must pre-exist.** Set `target_catalog` to an existing catalog; the package makes only the
  schema inside it.
- **App HTTP 200 also passes on the login page** — a green Stage 06 verify means the shell is
  serving; click through the app URL to confirm the board renders.
- The 32-hex ids inside `artefacts/*.json` are the **origin** the definitions were captured from;
  they are rewritten to your target at build time and no source workspace is ever contacted.
