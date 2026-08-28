# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 05b — Provision Lakebase + seed questions (required)
# MAGIC The supervisor app surfaces its 4 starter prompts from a Lakebase (Postgres) `seed_questions`
# MAGIC table, so Lakebase is a **required** part of this demo. The instance name comes from
# MAGIC `00_preflight` (`lakebase_instance`, saved to `deploy_config.json`).
# MAGIC
# MAGIC This stage **creates the Lakebase Database Instance** (autoscaling) if it doesn't exist,
# MAGIC connects to its `databricks_postgres` database, runs `seed_questions.sql` (4 rows), and records
# MAGIC the instance name + host in the deployment manifest so Stage 06 can wire `PGHOST` /
# MAGIC `LAKEBASE_INSTANCE`. It **fails** if `lakebase_instance` was not set in preflight.

# COMMAND ----------

# MAGIC %pip install "psycopg[binary]" --quiet
# MAGIC %restart_python

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
from databricks.sdk.service.database import DatabaseInstance

w = target_sql().w
SEED_SQL = (PKG / "seed_questions.sql").read_text()

# The supervisor app (server/db.py) connects to a Lakebase **Database Instance** by name:
# it mints creds via generate_database_credential(instance_names=[<name>]) and connects to the
# instance's read-write DNS. So provision an autoscaling Database Instance named <pid> here.
# (Autoscaling is a capacity mode of a Database Instance, not a separate API.)
db = w.database

# 1. create the instance if it doesn't exist (idempotent — reuse when present)
try:
    inst = db.get_database_instance(name=pid)
    ok(f"reusing existing Lakebase instance '{pid}' (state={inst.state})")
except Exception:
    ok(f"creating Lakebase instance '{pid}' (this can take a few minutes) …")
    inst = db.create_database_instance_and_wait(
        DatabaseInstance(name=pid, capacity="CU_1"))
    ok(f"created Lakebase instance '{pid}' (state={inst.state})")

host = inst.read_write_dns
if not host:
    fail(f"instance '{pid}' has no read_write_dns yet — provisioning may still be finishing; re-run shortly")

# 2. mint a short-lived Postgres credential for the instance (same call the app uses)
tok = db.generate_database_credential(instance_names=[pid]).token
user = w.current_user.me().user_name

# 3. seed the starter prompts into databricks_postgres
conn = psycopg.connect(host=host, user=user, password=tok, dbname="databricks_postgres", sslmode="require")
with conn, conn.cursor() as cur:
    cur.execute(SEED_SQL)
    cur.execute("SELECT count(*) FROM seed_questions")
    n = cur.fetchone()[0]
if n != 4:
    fail(f"seed_questions has {n} rows, expected 4")
ok(f"seeded seed_questions ({n} rows)")
manifest_put("lakebase", {"applicable": True, "instance": pid, "host": host})
print(f"\nStage 05b: Lakebase ready — instance '{pid}' at {host}")
