# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 05b — Provision Lakebase + seed questions (required)
# MAGIC The supervisor app renders its sidebar history + starter prompts from Lakebase (Postgres)
# MAGIC `conversations`/`messages`/`traces` tables, so Lakebase is a **required** part of this demo.
# MAGIC The instance name comes from `00_preflight` (`lakebase_instance`, saved to `deploy_config.json`).
# MAGIC
# MAGIC This stage **creates the Lakebase Database Instance** (autoscaling) if it doesn't exist,
# MAGIC connects to its `databricks_postgres` database, runs `seed_lakebase.sql` (an exact mirror of
# MAGIC UK-South's chat history — 8 conversations, 22 messages, 11 traces), and records the instance
# MAGIC name + host in the deployment manifest so Stage 06 can wire `PGHOST` / `LAKEBASE_INSTANCE`.
# MAGIC It **fails** if `lakebase_instance` was not set in preflight.

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
SEED_SQL = (PKG / "seed_lakebase.sql").read_text()

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

# 2. mint a short-lived Postgres credential for the instance (same call the app uses).
#    request_id is required by the API — generate a fresh one per call.
import uuid
tok = db.generate_database_credential(instance_names=[pid], request_id=str(uuid.uuid4())).token
user = w.current_user.me().user_name

# 3. seed the chat history (conversations/messages/traces) — exact mirror of UK-South.
#    The app (server/db.py) reads these tables to render the sidebar + starter prompts.
conn = psycopg.connect(host=host, user=user, password=tok, dbname="databricks_postgres", sslmode="require")
with conn, conn.cursor() as cur:
    cur.execute(SEED_SQL)
    counts = {}
    for t in ("conversations", "messages", "traces"):
        cur.execute(f"SELECT count(*) FROM {t}")
        counts[t] = cur.fetchone()[0]
if counts.get("conversations", 0) < 1:
    fail(f"seed loaded no conversations — got {counts}")
ok(f"seeded chat history: {counts['conversations']} conversations, "
   f"{counts['messages']} messages, {counts['traces']} traces")
manifest_put("lakebase", {"applicable": True, "instance": pid, "host": host})
print(f"\nStage 05b: Lakebase ready — instance '{pid}' at {host}")
