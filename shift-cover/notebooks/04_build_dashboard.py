# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 04 — Publish the AI/BI dashboard (idempotent)
# MAGIC Reads the **shipped** dashboard definition (`artefacts/dashboard.json`, captured once from
# MAGIC the original build), remaps every origin-schema reference to your target, points its
# MAGIC warehouse at the target, and publishes it. **No source workspace is read.**
# MAGIC
# MAGIC **Idempotent:** reuses an existing dashboard by recorded id (else by display name) and
# MAGIC updates it in place; a trashed/missing one falls back to a fresh create.

# COMMAND ----------

# MAGIC %run ./_common

# COMMAND ----------

from databricks.sdk.service.dashboards import Dashboard

ARTEFACT = ARTEFACTS / "dashboard.json"
NAME = "Ramsay Workforce & Absence — Executive"

w = target_sql().w
if not ARTEFACT.exists():
    fail(f"shipped dashboard definition missing: {ARTEFACT}")
src_def = json.loads(ARTEFACT.read_text()).get("serialized_dashboard") or ""
if not src_def:
    fail(f"shipped dashboard definition is empty: {ARTEFACT}")
serialized = remap(src_def)
disp = f"{NAME} [{CFG['TARGET_SCHEMA']}]"

existing_id = manifest_get("dashboard", {}).get("id")
if existing_id:
    try:
        if getattr(w.lakeview.get(dashboard_id=existing_id), "lifecycle_state", "") == "TRASHED":
            existing_id = None
    except Exception:
        existing_id = None
if not existing_id:
    for dd in w.lakeview.list():
        if dd.display_name == disp and not getattr(dd, "trashed", False):
            existing_id = dd.dashboard_id
            break

dash = Dashboard(display_name=disp, warehouse_id=CFG["WAREHOUSE_ID"], serialized_dashboard=serialized)
if existing_id:
    d = w.lakeview.update(dashboard_id=existing_id, dashboard=dash)
    ok(f"updated existing dashboard {d.dashboard_id}")
else:
    d = w.lakeview.create(dashboard=dash)
    ok(f"created dashboard {d.dashboard_id}")
w.lakeview.publish(dashboard_id=d.dashboard_id, warehouse_id=CFG["WAREHOUSE_ID"])
ok("published")
host = w.config.host.rstrip("/")
url = f"{host}/dashboardsv3/{d.dashboard_id}/published"
manifest_put("dashboard", {"id": d.dashboard_id, "url": url})
print(f"\nStage 04: dashboard -> {url}")

# COMMAND ----------

# MAGIC %md ## Verify — references target schema only + published + reachable

# COMMAND ----------

did = manifest_get("dashboard", {}).get("id")
d = w.lakeview.get(dashboard_id=did)
tgt = f'{CFG["TARGET_CATALOG"]}.{CFG["TARGET_SCHEMA"]}.'
origin = f"{ORIGIN_CATALOG}.{ORIGIN_SCHEMA}."
ser = d.serialized_dashboard or ""
if origin in ser and origin != tgt:
    fail("dashboard still references the ORIGIN schema")
if tgt not in ser:
    fail("dashboard does not reference the TARGET schema")
ok(f"dashboard {did} references target schema only")
pub = w.lakeview.get_published(dashboard_id=did)
ok(f"published dashboard reachable ({pub.display_name})")
print("Stage 04 verify: PASS")
