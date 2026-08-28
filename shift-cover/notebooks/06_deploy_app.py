# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 06 — Deploy the Shift-Cover App (idempotent)
# MAGIC Deploys the FastAPI+React app against your target resources.
# MAGIC
# MAGIC ### No input needed
# MAGIC The app source ships **inside this package** as `app.zip`. This stage extracts it
# MAGIC automatically and deploys from it — no manual upload, no unzip, no widget to set.
# MAGIC
# MAGIC What it does: generates `app.yaml` (target warehouse + `CATALOG_SCHEMA` + the new Genie id
# MAGIC from Stage 05), creates the app if absent, grants the app **SP before first run** (warehouse
# MAGIC CAN_USE, UC USE/SELECT/MODIFY/EXECUTE — MODIFY because the app writes `cover_decisions` — and
# MAGIC Genie CAN_RUN), then SNAPSHOT-deploys. Re-runs redeploy in place.

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
    genie = manifest_get("genie", {}).get("GENIE_WORKFORCE", {})
    env = [("WAREHOUSE_ID", CFG["WAREHOUSE_ID"]),
           ("CATALOG_SCHEMA", f"{cat}.{sch}"),
           ("GENIE_SPACE_ID", genie.get("space_id", "")),
           ("LLM_ENDPOINT", CFG.get("FM_ENDPOINTS_REQUIRED", "databricks-gpt-oss-120b").split(",")[0])]
    lines = ['command: ["python","-m","uvicorn","app:app","--host","0.0.0.0","--port","8000"]', "env:"]
    for k, v in env:
        lines.append(f'  - name: {k}\n    value: "{v}"')
    return "\n".join(lines) + "\n"


me = w.current_user.me().user_name
ws_root = f"/Workspace/Users/{me}/{name}"

# 1. write app.yaml into the source tree + upload the tree to the app workspace folder
(app_src / "app.yaml").write_text(gen_app_yaml())
ok("generated app.yaml (target warehouse + schema + new Genie id)")
for f in app_src.rglob("*"):
    if f.is_dir():
        continue
    rel = f.relative_to(app_src).as_posix()
    if any(seg in rel for seg in ("node_modules/", "__pycache__/", ".venv/", ".databricks/")):
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
    w.api_client.do("POST", "/api/2.0/apps", {"name": name, "description": "Ramsay Shift-Cover (handover deploy)"})
    ok(f"created app {name}")
    for _ in range(60):
        app = w.api_client.do("GET", f"/api/2.0/apps/{name}")
        if (app.get("compute_status") or {}).get("state") in ("ACTIVE", "RUNNING", "STOPPED"):
            break
        time.sleep(10)
else:
    ok(f"app {name} exists — redeploying")

sp = app.get("service_principal_client_id")

# 3. grant the SP BEFORE deploy
for stmt in [f"GRANT USE CATALOG ON CATALOG {cat} TO `{sp}`",
             f"GRANT USE SCHEMA ON SCHEMA {cat}.{sch} TO `{sp}`",
             f"GRANT SELECT ON SCHEMA {cat}.{sch} TO `{sp}`",
             f"GRANT MODIFY ON SCHEMA {cat}.{sch} TO `{sp}`",
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
_g = manifest_get("genie", {}).get("GENIE_WORKFORCE", {})
if _g.get("space_id"):
    try:
        w.api_client.do("PATCH", f"/api/2.0/permissions/genie/{_g['space_id']}",
                        body={"access_control_list": [{"service_principal_name": sp, "permission_level": "CAN_RUN"}]})
    except Exception as e:
        print(f"    (warn) genie grant: {e}")
ok(f"granted app SP {sp}")

# 4. deploy (SNAPSHOT)
dep = w.api_client.do("POST", f"/api/2.0/apps/{name}/deployments",
                      {"source_code_path": ws_root, "mode": "SNAPSHOT"})
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
if code != 200:
    print(f"  (warn) app URL returned {code} (expected 200) — it may still be warming up; recheck shortly")
else:
    ok(f"app URL returns HTTP {code}")
print("Stage 06 verify: done")
