# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 00 — Preflight
# MAGIC Confirms the notebook identity, Unity Catalog reachability, the target **catalog exists**
# MAGIC (this package creates only the *schema* inside it), the warehouse is usable, and the
# MAGIC Foundation-Model endpoint the app needs is present (else WARN — the app degrades).
# MAGIC
# MAGIC ### 👉 This is the ONLY notebook with widgets — set catalog/schema/etc. HERE
# MAGIC The widgets below appear in the bar at the top of this notebook. Set them, run this notebook,
# MAGIC and it **saves your choices to `deploy_config.json`** in the package folder. Every later
# MAGIC notebook (`01 → 06`, `99_*`) reads that file via `%run ./_common` — **you never set widgets
# MAGIC again.** To change a value later, edit it here and re-run this notebook.

# COMMAND ----------

# MAGIC %md ## ⚙️ Set the deployment parameters, then run this notebook top-to-bottom

# COMMAND ----------

dbutils.widgets.text("target_catalog", "classic_stable_82ujqz", "1. Target catalog (must already exist)")
dbutils.widgets.text("target_schema", "ramsay_shiftcover", "2. Target schema (created if absent)")
dbutils.widgets.text("warehouse_id", "7464666eb7d50c27", "3. SQL warehouse id (runs all SQL)")
# Fixed (not widgets): app name = ramsay-shift-cover; LLM endpoint = databricks-gpt-oss-120b;
# teardown safety = ramsay_health. The staging Volume is always derived to <cat>.<sch>._staging.
# app_source_path is asked for in Stage 06 (the only notebook that needs it).

# COMMAND ----------

# MAGIC %run ./_common

# COMMAND ----------

# MAGIC %md ### Save your selection → `deploy_config.json` (read by every later notebook)

# COMMAND ----------

# collect the widget values, persist them, and re-derive CFG from the saved file
_raw = {k: dbutils.widgets.get(k) for k in PARAM_DEFAULTS}
save_config(_raw)
CFG = _derive(_raw)
cat = CFG["TARGET_CATALOG"]
sch = CFG["TARGET_SCHEMA"]
print("Saved deploy_config.json — this run (and all later notebooks) will build into:")
print(f"    catalog  (existing) : {cat}")
print(f"    schema   (target)   : {sch}")
print(f"    warehouse           : {CFG['WAREHOUSE_ID']}")
print(f"    staging volume      : {CFG['STAGING_VOLUME']}")
print(f"    data volume path    : {CFG['DATA_VOLUME_PATH']}")
if not cat:
    fail("target_catalog is empty — set it to an EXISTING catalog and re-run.")
if not sch:
    fail("target_schema is empty — set it to the schema to build into and re-run.")
if not CFG["WAREHOUSE_ID"]:
    fail("warehouse_id is empty — set it to a running SQL warehouse and re-run.")

# COMMAND ----------

sql = target_sql()
w = sql.w
warns = []

me = w.current_user.me().user_name
ok(f"authenticated as {me}")
ok(f"host {w.config.host}")

try:
    ms = sql.scalar("SELECT current_metastore()", catalog=None, schema=None)
    ok(f"Unity Catalog metastore: {ms}")
except Exception as e:
    fail(f"Unity Catalog not reachable: {e}")

# catalog MUST already exist (Default-Storage workspaces reject CREATE CATALOG via SQL)
_, cats = sql.run(f"SHOW CATALOGS LIKE '{cat}'", catalog=None, schema=None)
if any(r[0] == cat for r in cats):
    ok(f"target catalog '{cat}' exists (schema will be created inside it)")
else:
    fail(f"target catalog '{cat}' does not exist — set target_catalog to an EXISTING catalog. "
         f"This package never creates a catalog.")

wid = CFG["WAREHOUSE_ID"]
try:
    wh = w.warehouses.get(id=wid)
    ok(f"warehouse {wid} present (state={wh.state})")
except Exception as e:
    fail(f"warehouse {wid} not found: {e}")

needed = [e.strip() for e in CFG.get("FM_ENDPOINTS_REQUIRED", "").split(",") if e.strip()]
try:
    have = {e.name for e in w.serving_endpoints.list()}
except Exception:
    have = set()
for e in needed:
    if e in have:
        ok(f"FM endpoint present: {e}")
    else:
        warns.append(e)
        print(f"  WARN FM endpoint missing: {e} — app AI co-worker degrades to rule-based fallback")

print(f"\nStage 00: preflight OK ({len(warns)} warning(s), 0 hard failures)")
