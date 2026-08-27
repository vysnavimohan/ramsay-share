# Databricks notebook source
# MAGIC %md
# MAGIC # 99 — End-to-end verify
# MAGIC One pass over everything the package built: all carry-set objects exist, row counts match
# MAGIC the shipped manifest, MEASURE parity, dashboard published, Genie recorded, app RUNNING.
# MAGIC Run after Stages 00→06. Prints the three deliverable URLs.

# COMMAND ----------

# MAGIC %run ./_common

# COMMAND ----------

import urllib.request, urllib.error

m = json.loads(MANIFEST.read_text())
sql = target_sql()
w = sql.w
cat, sch = CFG["TARGET_CATALOG"], CFG["TARGET_SCHEMA"]
problems = []

# 1. objects present
_, trows = sql.run(f"SELECT table_name FROM {cat}.information_schema.tables WHERE table_schema='{sch}'", catalog=None, schema=None)
_, frows = sql.run(f"SELECT routine_name FROM {cat}.information_schema.routines WHERE routine_schema='{sch}'", catalog=None, schema=None)
present = {r[0] for r in trows} | {r[0] for r in frows}
missing = set(m["order"]) - present
if missing:
    problems.append(f"missing objects: {sorted(missing)}")
else:
    ok(f"all {len(m['order'])} carry-set objects present")

# 2. row counts + MEASURE
for t in m["data_tables"]:
    d = int(sql.scalar(f"SELECT count(*) FROM {cat}.{sch}.{t}"))
    exp = int(m["row_counts"].get(t, -1))
    if exp >= 0 and d != exp:
        problems.append(f"row-count {t}: {d} vs {exp}")
ok("row counts checked against shipped manifest")
try:
    dv = sql.scalar(f"SELECT MEASURE(total_shifts) FROM {cat}.{sch}.mv_shift_fulfilment")
    ok(f"mv_shift_fulfilment total_shifts = {dv}")
except Exception as e:
    problems.append(f"MEASURE failed: {e}")

# 3. dashboard
dash = manifest_get("dashboard", {})
if dash.get("id"):
    try:
        w.lakeview.get_published(dashboard_id=dash["id"])
        ok(f"dashboard published: {dash['url']}")
    except Exception as e:
        problems.append(f"dashboard not reachable: {e}")
else:
    problems.append("no dashboard recorded (run Stage 04)")

# 4. genie
genie = manifest_get("genie", {}).get("GENIE_WORKFORCE", {})
if genie.get("space_id"):
    ok(f"Genie space: {genie['url']} ({genie.get('instruction_count')} instructions)")
else:
    problems.append("no Genie space recorded (run Stage 05)")

# 5. app
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
    if state in ("RUNNING", "ACTIVE") and code == 200:
        ok(f"app {state}, HTTP {code}: {app['url']}")
    else:
        problems.append(f"app state={state} HTTP={code}")
else:
    problems.append("no app recorded (run Stage 06)")

# COMMAND ----------

print("═══════════ DEPLOYMENT SUMMARY ═══════════")
print("Dashboard:", manifest_get("dashboard", {}).get("url", "—"))
print("Genie    :", manifest_get("genie", {}).get("GENIE_WORKFORCE", {}).get("url", "—"))
print("App      :", manifest_get("app", {}).get("url", "—"))
print("══════════════════════════════════════════")
if problems:
    fail("VERIFY FAILED:\n  - " + "\n  - ".join(problems))
print("99 verify: PASS — all deliverables live")
