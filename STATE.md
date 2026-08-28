# STATE — Ramsay demo notebook packages (ramsay-share)

_Last updated: 2026-08-28_

## Goal
Ship two Ramsay demos as **notebook-driven, self-contained** packages a customer deploys with
manual uploads + Databricks notebooks (no source workspace, no laptop CLI). Repo:
https://github.com/vysnavimohan/ramsay-share (branch `main`).

## Target environment (manual test)
- Profile `fevm-azure-82ujqz` → adb-7405604635797033.13.azuredatabricks.net (Azure eastus2).
- Catalog `classic_stable_82ujqz` (EXISTING — package only creates the schema inside it).
- Warehouse `7464666eb7d50c27` (serverless). FM endpoint `databricks-gpt-oss-120b` present.
- Test schema/volume the user created: `classic_stable_82ujqz.ramsay_demo_test` + Volume
  `ramsay_demo_test` (path `/Volumes/classic_stable_82ujqz/ramsay_demo_test/ramsay_demo_test`).
  ShiftCover data already uploaded there (6 table folders) via CLI.

## Decisions locked in
- **Two packages**: `shift-cover/` (13 objects, 1 Genie, no Lakebase) and `ai-supervisor/`
  (23 objects, 4 Genie agents, **Lakebase required**).
- **Source-free**: ships ddl/, artefacts/{dashboard,genie}.json, data/ parquet, app.zip; remaps
  origin (`ramsay_workforce.allocate` / `ramsay_health.ops`) → target at build time.
- **Widgets ONLY in 00_preflight** (child-notebook widgets under %run don't render). Preflight saves
  choices to `deploy_config.json`; `_common` reads it; later notebooks need no widgets.
- **Preflight params (FINAL, minimal)**: shift-cover = target_catalog, target_schema, warehouse_id (3);
  ai-supervisor = those + lakebase_instance (4, required). app_name HARD-CODED (_common APP_NAME const);
  staging_volume DERIVED to `<cat>.<sch>._staging` (not asked). `app_source_path` = Stage-06-only widget.
- **Fixed constants (not widgets)**: FM endpoint = databricks-gpt-oss-120b; never_touch (teardown
  guard) = the other demo's catalog.
- **data_volume_path** dropped — always derived from staging_volume.
- **01b_stage_data_to_volume** copies shipped data/ from the Git folder into the Volume (no laptop).
  AI's 26 MB tbwlmds may exceed Git-folder checkout limit → doc says upload that table by hand if so.
- **Idempotent** everywhere; **99_teardown** removes app/lakebase/genie/dashboard + DROP SCHEMA
  CASCADE (catalog never dropped, never_touch-guarded).
- **Genie One** (live conversational Q&A) unavailable on fevm-azure (no Claude model) → smoke tests
  WARN not fail; documented.

## What's done
- [x] Both packages built, notebooks written, pushed. Latest commit `3813839` (preflight param trim).
- [x] Old script-based `ramsay-shift-cover-test` deployment torn down on fevm-azure (verified clean).
- [x] Widget refactor (preflight-only + saved config), param trim, FM hardcode, Lakebase required.

## What's next (manual test — Phase G, user drives; I do NOT execute on the workspace)
1. In fevm-azure: **Pull** the Git folder to get `65d69d7`.
2. `shift-cover/notebooks/00_preflight` — set widgets: target_catalog=classic_stable_82ujqz,
   target_schema=ramsay_demo_test, warehouse_id=7464666eb7d50c27,
   staging_volume=classic_stable_82ujqz.ramsay_demo_test.ramsay_demo_test,
   app_name=ramsay-shift-cover-test. Run it → expect "Saved deploy_config.json …".
3. Run 01 → 01b → 02 → 03 → 04 → 05 one at a time; report each verify result.
4. Upload+unzip app.zip, set app_source_path on Stage 06, run 06; then 99_verify.
5. Teardown with 99_teardown when done.

## Key context / gotchas
- Build folder: `~/work/ramsay/ramsay-share-build` (git remote → ramsay-share, HTTPS).
- Push works now (user granted access; earlier 403 was vaishnavi-mohan_data not a collaborator).
- Git hooks enforced — never use --no-verify; the `-c user.name=...` flag trips the guard, commit plainly.
- App source (AI): bundled from ~/work/ramsay/new_demo_build/new_demo_build/ramsay-supervisor-app.
  Genie agent defs extracted from that repo's build_health/40_genie_agents.py.
- Source-free base for ShiftCover came from ~/work/ramsay/repro_test_HANDOVER (verified working).
- deploy_config.json + preflight_report.txt are gitignored (per-run outputs).
