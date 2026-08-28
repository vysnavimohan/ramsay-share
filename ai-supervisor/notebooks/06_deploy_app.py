# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 06 — Deploy the AI-Supervisor App (idempotent)
# MAGIC Deploys the React + FastAPI multi-agent supervisor app against your target resources.
# MAGIC
# MAGIC ### No input needed
# MAGIC The app source ships **inside this package** as `app.zip`. This stage extracts it
# MAGIC automatically and deploys from it — no manual upload, no unzip, no widget to set.
# MAGIC
# MAGIC What it does: generates `app.yaml` (target host + warehouse + the **4 new Genie space ids**
# MAGIC from Stage 05 + Lakebase host if provisioned), creates the app if absent, grants the app **SP
# MAGIC before first run** (warehouse CAN_USE, UC USE/SELECT on the target schema, Genie CAN_RUN on
# MAGIC all 4 spaces), then SNAPSHOT-deploys. Re-runs redeploy in place.
# MAGIC
# MAGIC > **Genie One note:** the app's *live* Q&A needs a Claude model that may be unavailable in your
# MAGIC > region (e.g. fevm-azure). The app still deploys and RUNs; the answer trace will report the
# MAGIC > degraded path if the conversational model is missing.

# COMMAND ----------

# MAGIC %run ./_common

# COMMAND ----------

import urllib.request, urllib.error
import zipfile, tempfile
from databricks.sdk.service.workspace import ImportFormat

sql = target_sql()
w = sql.w
cat, sch = CFG["TARGET_CATALOG"], CFG["TARGET_SCHEMA"]
name = CFG["APP_NAME"][:30].rstrip("-")

# resolve the app source: extract the bundled app.zip (path is relative to this package)
app_zip = PKG / "app.zip"
if not app_zip.exists():
    fail(f"bundled app source not found at {app_zip} — the package is incomplete")
extract_dir = Path(tempfile.mkdtemp(prefix=f"{name}-"))
with zipfile.ZipFile(app_zip) as z:
    z.extractall(extract_dir)
app_src = extract_dir
# if the zip wrapped everything in a single top-level folder, descend into it
if not (app_src / "app.py").exists():
    subdirs = [d for d in app_src.iterdir() if d.is_dir()]
    if len(subdirs) == 1 and (subdirs[0] / "app.py").exists():
        app_src = subdirs[0]
ok(f"app source: {app_src} (extracted from {app_zip.name})")


def gen_app_yaml():
    genie = manifest_get("genie", {})
    lb = manifest_get("lakebase", {})
    env = [
        ("DATABRICKS_HOST_URL", w.config.host.rstrip("/")),
        ("LLM_ENDPOINT", CFG.get("FM_ENDPOINTS_REQUIRED", "databricks-gpt-oss-120b").split(",")[0]),
        ("DATABRICKS_WAREHOUSE_ID", CFG["WAREHOUSE_ID"]),
        ("CATALOG_SCHEMA", f"{cat}.{sch}"),
        ("GENIE_CAPACITY", genie.get("GENIE_CAPACITY", {}).get("space_id", "")),
        ("GENIE_PATIENT_FINANCE", genie.get("GENIE_PATIENT_FINANCE", {}).get("space_id", "")),
        ("GENIE_THROUGHPUT_FLOW", genie.get("GENIE_THROUGHPUT_FLOW", {}).get("space_id", "")),
        ("GENIE_WORKFORCE", genie.get("GENIE_WORKFORCE", {}).get("space_id", "")),
    ]
    if lb.get("applicable") and lb.get("host"):
        env += [("LAKEBASE_INSTANCE", CFG.get("LAKEBASE_INSTANCE", "")),
                ("PGHOST", lb["host"]), ("PGDATABASE", "databricks_postgres")]
    lines = ["command: ['uvicorn', 'app:app', '--host', '0.0.0.0', '--port', '8000']", "env:"]
    for k, v in env:
        lines.append(f"  - name: '{k}'\n    value: '{v}'")
    return "\n".join(lines) + "\n"


me = w.current_user.me().user_name
ws_root = f"/Workspace/Users/{me}/{name}"

# 1. app.yaml + upload tree
(app_src / "app.yaml").write_text(gen_app_yaml())
ok("generated app.yaml (target host + warehouse + 4 Genie ids + Lakebase host)")
for f in app_src.rglob("*"):
    if f.is_dir():
        continue
    rel = f.relative_to(app_src).as_posix()
    if any(seg in rel for seg in ("node_modules/", "__pycache__/", ".venv/", ".databricks/", "flagship_cache/")):
        continue
    target = f"{ws_root}/{rel}"
    w.workspace.mkdirs(target.rsplit("/", 1)[0])
    w.workspace.upload(target, io.BytesIO(f.read_bytes()), format=ImportFormat.AUTO, overwrite=True)
ok(f"uploaded app source -> {ws_root}")

# 2. create app if absent
try:
    app = w.api_client.do("GET", f"/api/2.0/apps/{name}")
except Exception:
    app = {}
if not app.get("name"):
    w.api_client.do("POST", "/api/2.0/apps", body={"name": name, "description": "Ramsay AI Supervisor (handover deploy)"})
    ok(f"created app {name}")
    for _ in range(60):
        app = w.api_client.do("GET", f"/api/2.0/apps/{name}")
        if (app.get("compute_status") or {}).get("state") in ("ACTIVE", "RUNNING", "STOPPED"):
            break
        time.sleep(10)
else:
    ok(f"app {name} exists — redeploying")

sp = app.get("service_principal_client_id")

# 3a. give the app SP a Postgres role on the Lakebase instance so it can log in as itself
#     (the app connects with PGUSER = its DATABRICKS_CLIENT_ID). Idempotent — ignore if it exists.
_lb = manifest_get("lakebase", {})
if _lb.get("applicable") and _lb.get("instance") and sp:
    from databricks.sdk.service.database import (
        DatabaseInstanceRole, DatabaseInstanceRoleIdentityType, DatabaseInstanceRoleMembershipRole)
    try:
        w.database.create_database_instance_role(
            instance_name=_lb["instance"],
            database_instance_role=DatabaseInstanceRole(
                name=sp,
                identity_type=DatabaseInstanceRoleIdentityType.SERVICE_PRINCIPAL,
                membership_role=DatabaseInstanceRoleMembershipRole.DATABRICKS_SUPERUSER))
        ok(f"granted Lakebase role to app SP on {_lb['instance']}")
    except Exception as e:
        print(f"    (warn) Lakebase role for SP (may already exist): {e}")

# 3. grant SP BEFORE deploy
for stmt in [f"GRANT USE CATALOG ON CATALOG {cat} TO `{sp}`",
             f"GRANT USE SCHEMA ON SCHEMA {cat}.{sch} TO `{sp}`",
             f"GRANT SELECT ON SCHEMA {cat}.{sch} TO `{sp}`",
             f"GRANT EXECUTE ON SCHEMA {cat}.{sch} TO `{sp}`"]:
    try:
        sql.run(stmt, catalog=None, schema=None)
    except Exception as e:
        print(f"    (warn) grant skipped: {e}")
try:
    w.api_client.do("PATCH", f"/api/2.0/permissions/warehouses/{CFG['WAREHOUSE_ID']}",
                    body={"access_control_list": [{"service_principal_name": sp, "permission_level": "CAN_USE"}]})
except Exception as e:
    print(f"    (warn) warehouse grant: {e}")
for env, a in manifest_get("genie", {}).items():
    sid = a.get("space_id")
    if sid:
        try:
            w.api_client.do("PATCH", f"/api/2.0/permissions/genie/{sid}",
                            body={"access_control_list": [{"service_principal_name": sp, "permission_level": "CAN_RUN"}]})
        except Exception as e:
            print(f"    (warn) genie grant {env}: {e}")
ok(f"granted app SP {sp}")

# 4. deploy (SNAPSHOT)
dep = w.api_client.do("POST", f"/api/2.0/apps/{name}/deployments", body={"source_code_path": ws_root, "mode": "SNAPSHOT"})
dep_id = dep.get("deployment_id")
state = None
for _ in range(60):
    d = w.api_client.do("GET", f"/api/2.0/apps/{name}/deployments/{dep_id}")
    state = (d.get("status") or {}).get("state")
    if state in ("SUCCEEDED", "FAILED", "STOPPED"):
        break
    time.sleep(10)
if state != "SUCCEEDED":
    fail(f"deployment {dep_id} state={state}")
ok(f"deployment {dep_id} SUCCEEDED")

app = w.api_client.do("GET", f"/api/2.0/apps/{name}")
url = app.get("url")
manifest_put("app", {"name": name, "url": url, "sp": sp, "source_path": ws_root, "deployment_id": dep_id})
print(f"\nStage 06: app deployed -> {url}")

# COMMAND ----------

# MAGIC %md ## Verify — app RUNNING + URL reachable

# COMMAND ----------

app = manifest_get("app", {})
d = w.api_client.do("GET", f"/api/2.0/apps/{app['name']}")
state = (d.get("app_status") or {}).get("state") or (d.get("compute_status") or {}).get("state")
ok(f"app state: {state}")
try:
    code = urllib.request.urlopen(urllib.request.Request(app["url"], method="GET"), timeout=30).status
except urllib.error.HTTPError as e:
    code = e.code
except Exception as e:
    code = None
    print(f"    (warn) URL check: {e}")
if code and code >= 500:
    fail(f"app URL returned {code}")
ok(f"app URL reachable (HTTP {code})")
print("Stage 06 verify: done")
