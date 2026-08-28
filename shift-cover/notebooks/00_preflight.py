# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 00 — Preflight
# MAGIC Confirms the notebook identity, Unity Catalog reachability, the target **catalog exists**
# MAGIC (this package creates only the *schema* inside it), the warehouse is usable, and the
# MAGIC Foundation-Model endpoint the app needs is present (else WARN — the app degrades).
# MAGIC
# MAGIC ### 👉 Choose your target catalog & schema HERE
# MAGIC Running `%run ./_common` (next cell) shows widgets **at the top of this notebook**. Set them
# MAGIC before running the rest — this is where you tell the package where to build:
# MAGIC - **`target_catalog`** — an **existing** catalog (the package creates only a schema inside it).
# MAGIC - **`target_schema`** — the schema to create/use for this demo (new or existing).
# MAGIC - **`warehouse_id`** — a running SQL warehouse.
# MAGIC
# MAGIC The confirmation cell below echoes exactly what you selected and validates it before any build.

# COMMAND ----------

# MAGIC %run ./_common

# COMMAND ----------

# MAGIC %md ### Confirm your selection — catalog / schema / warehouse the whole run will use

# COMMAND ----------

cat = CFG["TARGET_CATALOG"]
sch = CFG["TARGET_SCHEMA"]
print("This run will build into:")
print(f"    catalog  (existing) : {cat}")
print(f"    schema   (target)   : {sch}")
print(f"    warehouse           : {CFG['WAREHOUSE_ID']}")
print(f"    staging volume       : {CFG['STAGING_VOLUME']}")
print(f"    data volume path     : {CFG['DATA_VOLUME_PATH']}")
if not cat:
    fail("target_catalog widget is empty — set it to an EXISTING catalog and re-run.")
if not sch:
    fail("target_schema widget is empty — set it to the schema you want to build into and re-run.")
if not CFG["WAREHOUSE_ID"]:
    fail("warehouse_id widget is empty — set it to a running SQL warehouse and re-run.")
print("\n➡️  If the catalog/schema above is not what you want, edit the widgets at the top of this "
      "notebook and re-run this cell before continuing.")

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
