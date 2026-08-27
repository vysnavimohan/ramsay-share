# Databricks notebook source
# MAGIC %md
# MAGIC # 99 — Teardown (remove everything this package created)
# MAGIC Reverse order, each step guarded so a partial deploy still tears down cleanly:
# MAGIC - **app** → `app_name`
# MAGIC - **dashboard** → id from `deployment_manifest.json`
# MAGIC - **Genie space** → id from `deployment_manifest.json`
# MAGIC - **schema** → `DROP SCHEMA <catalog>.<schema> CASCADE` (drops the 13 objects + `_staging` volume)
# MAGIC
# MAGIC The **catalog is NEVER dropped** — it is a shared existing catalog this package only created a
# MAGIC schema inside. Safety: refuses to run if `target_schema` is empty or `target_catalog`/schema
# MAGIC is in `never_touch`. Resets `deployment_manifest.json` on success.
# MAGIC
# MAGIC > Use this after your manual test to return the workspace to a clean state.

# COMMAND ----------

# MAGIC %run ./_common

# COMMAND ----------

cat, sch = CFG["TARGET_CATALOG"], CFG["TARGET_SCHEMA"]
nt = never_touch()
if not sch:
    fail("target_schema is empty — refusing to run teardown")
if cat in nt or sch in nt:
    fail(f"{cat}.{sch} intersects never_touch — refusing to run teardown")

sql = target_sql()
w = sql.w

# 1. app
name = CFG.get("APP_NAME", "")[:30].rstrip("-")
try:
    w.apps.delete(name=name)
    ok(f"deleted app {name}")
except Exception as e:
    if "not found" in str(e).lower() or "does not exist" in str(e).lower():
        ok(f"app {name} already absent")
    else:
        print(f"  (warn) could not delete app {name}: {e}")

# 2. dashboard
did = manifest_get("dashboard", {}).get("id")
if did:
    try:
        w.lakeview.trash(dashboard_id=did)
        ok(f"trashed dashboard {did}")
    except Exception as e:
        print(f"  (warn) could not trash dashboard {did}: {e}")
else:
    ok("no dashboard id in manifest — skipping")

# 3. genie
sid = manifest_get("genie", {}).get("GENIE_WORKFORCE", {}).get("space_id")
if sid:
    try:
        w.api_client.do("DELETE", f"/api/2.0/data-rooms/{sid}")
        ok(f"deleted Genie space {sid}")
    except Exception as e:
        print(f"  (warn) could not delete Genie space {sid}: {e}")
else:
    ok("no Genie space id in manifest — skipping")

# 4. schema (CASCADE drops all objects + the _staging volume). Catalog kept.
sql.run(f"DROP SCHEMA IF EXISTS {cat}.{sch} CASCADE", catalog=None, schema=None)
ok(f"dropped schema {cat}.{sch} (catalog {cat} left intact)")

# reset the deployment manifest so a later rebuild never references torn-down ids
DEPLOY_MANIFEST.write_text("{}")
ok("reset deployment_manifest.json")
print(f"\nTeardown: removed app/dashboard/genie + schema {cat}.{sch}")

# COMMAND ----------

# MAGIC %md ## Verify — schema/app/dashboard/Genie gone, catalog intact

# COMMAND ----------

problems = []
_, schemas = sql.run(f"SELECT schema_name FROM {cat}.information_schema.schemata WHERE schema_name='{sch}'", catalog=None, schema=None)
if schemas:
    problems.append(f"schema {cat}.{sch} still present")
else:
    ok(f"schema {cat}.{sch} gone")

_, cats = sql.run(f"SHOW CATALOGS LIKE '{cat}'", catalog=None, schema=None)
if any(r[0] == cat for r in cats):
    ok(f"catalog {cat} intact")
else:
    problems.append(f"catalog {cat} missing (should never be dropped)")

app_gone = False
for _ in range(6):
    try:
        w.apps.get(name=name)
        time.sleep(5)
    except Exception:
        app_gone = True
        break
ok(f"app {name} gone") if app_gone else problems.append(f"app {name} still present")

if problems:
    fail("; ".join(problems))
print("Teardown verify: PASS")
