# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 05b — Provision Lakebase + seed questions (required)
# MAGIC The supervisor app surfaces its 4 starter prompts from a Lakebase (Postgres) `seed_questions`
# MAGIC table, so Lakebase is a **required** part of this demo. The instance name comes from
# MAGIC `00_preflight` (`lakebase_instance`, saved to `deploy_config.json`).
# MAGIC
# MAGIC This stage ensures a Lakebase project, connects to its production branch `databricks_postgres`,
# MAGIC runs `seed_questions.sql` (4 rows), and records host/endpoint in the deployment manifest so
# MAGIC Stage 06 can wire `PGHOST`. It **fails** if `lakebase_instance` was not set in preflight.

# COMMAND ----------

# MAGIC %run ./_common

# COMMAND ----------

# Lakebase is REQUIRED for this demo — the instance name comes from 00_preflight (deploy_config.json).
pid = CFG["LAKEBASE_INSTANCE"].strip()
if not pid:
    fail("lakebase_instance is not set — run 00_preflight and provide a Lakebase instance name. "
         "Lakebase is required for this demo (the supervisor app's serving layer / starter prompts).")

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
