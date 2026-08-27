# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 05b — Provision Lakebase + seed questions (optional)
# MAGIC The supervisor app can surface 4 starter prompts from a Lakebase (Postgres) `seed_questions`
# MAGIC table. This is **optional** — the app runs without it (it degrades to no starter prompts).
# MAGIC
# MAGIC - **`lakebase_instance` widget blank (default)** → this stage is a **no-op**. Recommended if
# MAGIC   Lakebase isn't enabled in your workspace/region.
# MAGIC - **`lakebase_instance` set** → ensures a Lakebase project, connects to its production branch
# MAGIC   `databricks_postgres`, runs `seed_questions.sql` (4 rows), records host/endpoint in the
# MAGIC   deployment manifest so Stage 06 can wire `PGHOST`.

# COMMAND ----------

# MAGIC %run ./_common

# COMMAND ----------

pid = CFG.get("LAKEBASE_INSTANCE", "").strip()
if not pid:
    manifest_put("lakebase", {"applicable": False,
                              "note": "lakebase_instance blank — no Postgres serving layer; app starter "
                                      "prompts disabled. Set the widget to provision."})
    ok("no Lakebase requested — skipping (app runs without starter prompts)")
    dbutils.notebook.exit("Stage 05b: no-op (lakebase_instance blank)")

# COMMAND ----------

# MAGIC %md ### Provision (only runs when lakebase_instance is set)

# COMMAND ----------

import psycopg
w = target_sql().w
SEED_SQL = (PKG / "seed_questions.sql").read_text()

db = w.database  # SDK database (Lakebase) API

# 1. ensure project
projects = {p.name for p in db.list_database_instances()} if hasattr(db, "list_database_instances") else set()
# The SDK surface for Lakebase Autoscaling projects evolves; we use the REST fallback for portability.
def _rest(method, path, body=None):
    return w.api_client.do(method, path, body=body)

existing = _rest("GET", "/api/2.0/database/projects").get("projects", [])
names = {p.get("name") for p in existing}
if f"projects/{pid}" in names:
    ok(f"reusing existing project projects/{pid}")
else:
    _rest("POST", "/api/2.0/database/projects",
          {"project_id": pid, "spec": {"display_name": f"Ramsay serving ({pid})"}})
    ok(f"created project projects/{pid}")
proj = f"projects/{pid}"
branch = f"{proj}/branches/production"

# 2. endpoint
eps = _rest("GET", f"/api/2.0/database/{branch}/endpoints").get("endpoints", [])
if not eps:
    fail(f"no endpoint on {branch} — provisioning may still be starting; re-run shortly")
ep = eps[0]["name"]
host = _rest("GET", f"/api/2.0/database/{ep}")["status"]["hosts"]["host"]
tok = _rest("POST", f"/api/2.0/database/{ep}/credentials")["token"]
user = w.current_user.me().user_name

# 3. seed
conn = psycopg.connect(host=host, user=user, password=tok, dbname="databricks_postgres", sslmode="require")
with conn, conn.cursor() as cur:
    cur.execute(SEED_SQL)
    cur.execute("SELECT count(*) FROM seed_questions")
    n = cur.fetchone()[0]
if n != 4:
    fail(f"seed_questions has {n} rows, expected 4")
ok(f"seeded seed_questions ({n} rows)")
manifest_put("lakebase", {"applicable": True, "project": proj, "branch": branch, "endpoint": ep, "host": host})
print(f"\nStage 05b: Lakebase ready at {proj} ({host})")
