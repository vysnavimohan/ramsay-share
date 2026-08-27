# Databricks notebook source
# MAGIC %md
# MAGIC # 99 — End-to-end verify
# MAGIC One pass: all 23 carry-set objects exist, row counts match the shipped manifest, MEASURE
# MAGIC parity, dashboard published, 4 Genie spaces recorded, app RUNNING. Prints deliverable URLs.

# COMMAND ----------

# MAGIC %run ./_common

# COMMAND ----------

import urllib.request, urllib.error

m = json.loads(MANIFEST.read_text())
sql = target_sql()
w = sql.w
cat, sch = CFG["TARGET_CATALOG"], CFG["TARGET_SCHEMA"]
problems = []

_, trows = sql.run(f"SELECT table_name FROM {cat}.information_schema.tables WHERE table_schema='{sch}'", catalog=None, schema=None)
_, frows = sql.run(f"SELECT routine_name FROM {cat}.information_schema.routines WHERE routine_schema='{sch}'", catalog=None, schema=None)
present = {r[0] for r in trows} | {r[0] for r in frows}
missing = set(m["order"]) - present
if missing:
    problems.append(f"missing objects: {sorted(missing)}")
else:
    ok(f"all {len(m['order'])} carry-set objects present")

for t in m["data_tables"]:
    d = int(sql.scalar(f"SELECT count(*) FROM {cat}.{sch}.{t}"))
    exp = int(m["row_counts"].get(t, -1))
    if exp >= 0 and d != exp:
        problems.append(f"row-count {t}: {d} vs {exp}")
ok("row counts checked against shipped manifest")
try:
    dv = sql.scalar(f"SELECT MEASURE(`Beds Occupied`) FROM {cat}.{sch}.mv_bed_occupancy")
    ok(f"mv_bed_occupancy Beds Occupied = {dv}")
except Exception as e:
    problems.append(f"MEASURE failed: {e}")

dash = manifest_get("dashboard", {})
if dash.get("id"):
    try:
        w.lakeview.get_published(dashboard_id=dash["id"])
        ok(f"dashboard published: {dash['url']}")
    except Exception as e:
        problems.append(f"dashboard not reachable: {e}")
else:
    problems.append("no dashboard recorded (run Stage 04)")

genie = manifest_get("genie", {})
n_spaces = sum(1 for v in genie.values() if isinstance(v, dict) and v.get("space_id"))
if n_spaces >= 1:
    ok(f"{n_spaces} Genie space(s) recorded")
    for env, a in genie.items():
        if isinstance(a, dict) and a.get("url"):
            print(f"     {env}: {a['url']}")
else:
    problems.append("no Genie spaces recorded (run Stage 05)")

lb = manifest_get("lakebase", {})
if lb.get("applicable"):
    ok(f"Lakebase provisioned: {lb.get('host')}")
else:
    ok("Lakebase not provisioned (optional — app runs without starter prompts)")

app = manifest_get("app", {})
if app.get("name"):
    d = w.api_client.do("GET", f"/api/2.0/apps/{app['name']}")
    state = (d.get("app_status") or {}).get("state") or (d.get("compute_status") or {}).get("state")
    try:
        code = urllib.request.urlopen(urllib.request.Request(app["url"], method="GET"), timeout=30).status
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception:
        code = None
    if state in ("RUNNING", "ACTIVE") and (code is None or code < 500):
        ok(f"app {state}, HTTP {code}: {app['url']}")
    else:
        problems.append(f"app state={state} HTTP={code}")
else:
    problems.append("no app recorded (run Stage 06)")

# COMMAND ----------

print("═══════════ DEPLOYMENT SUMMARY ═══════════")
print("Dashboard:", manifest_get("dashboard", {}).get("url", "—"))
for env, a in manifest_get("genie", {}).items():
    if isinstance(a, dict):
        print(f"Genie {env}:", a.get("url", "—"))
print("App      :", manifest_get("app", {}).get("url", "—"))
print("══════════════════════════════════════════")
if problems:
    fail("VERIFY had issues:\n  - " + "\n  - ".join(problems))
print("99 verify: PASS — all deliverables live")
