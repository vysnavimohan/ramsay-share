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
2. **Upload the data**: the package's `data/` parquet → a target UC Volume.
3. **Upload the app**: `app.zip` → a workspace folder, unzip it.
4. Set the widgets at the top of `notebooks/_common`.
5. Run `notebooks/00 → 06` then `99_verify`. Every stage is **idempotent** and self-verifies.
6. When done, run `notebooks/99_teardown` to remove everything (the catalog is never dropped).

See each package's **`00_START_HERE.md`** for the step-by-step.

## Requirements
- A **target catalog that already exists** (the packages create only a *schema* inside it).
- A running **SQL warehouse**.
- FM endpoint `databricks-gpt-oss-120b` for the apps' LLM (they degrade gracefully without it).

> **Genie One** (the AI-Supervisor's live conversational Q&A) needs a Claude model that is not
> available in every region. The spaces, dashboard, tables and app still build and deploy there;
> only the live answer path degrades — reported as a WARN, never a failure.
