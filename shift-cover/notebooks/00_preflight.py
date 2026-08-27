# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 00 — Preflight
# MAGIC Confirms the notebook identity, Unity Catalog reachability, the target **catalog exists**
# MAGIC (this package creates only the *schema* inside it), the warehouse is usable, and the
# MAGIC Foundation-Model endpoint the app needs is present (else WARN — the app degrades).
# MAGIC
# MAGIC **Set the widgets at the top of `_common` (target_catalog / target_schema / warehouse_id) first.**

# COMMAND ----------

# MAGIC %run ./_common

# COMMAND ----------

sql = target_sql()
w = sql.w
cat = CFG["TARGET_CATALOG"]
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
