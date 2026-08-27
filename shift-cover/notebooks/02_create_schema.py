# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 02 — Create target schema + objects (idempotent)
# MAGIC Creates the target **schema** inside the existing target catalog, then replays the shipped
# MAGIC DDL — remapped from the origin catalog/schema to your target — in dependency order.
# MAGIC
# MAGIC **Idempotent:** tables/views/metric-views/functions use `CREATE OR REPLACE`; the
# MAGIC materialized view is `DROP … IF EXISTS` then `CREATE` (Spark rejects `OR REPLACE MATERIALIZED
# MAGIC VIEW`, and DROP also releases any pipeline ownership from a prior run). Tables are created
# MAGIC empty here — data lands in Stage 03.

# COMMAND ----------

# MAGIC %run ./_common

# COMMAND ----------

m = json.loads(MANIFEST.read_text())
sql = target_sql()
cat, sch = CFG["TARGET_CATALOG"], CFG["TARGET_SCHEMA"]

# never create a catalog — it must already exist (Stage 00 checked this)
_, cats = sql.run(f"SHOW CATALOGS LIKE '{cat}'", catalog=None, schema=None)
if not any(r[0] == cat for r in cats):
    fail(f"catalog '{cat}' must already exist — set target_catalog to an existing catalog")
sql.run(f"CREATE SCHEMA IF NOT EXISTS {cat}.{sch}", catalog=None, schema=None)
ok(f"schema ready in existing catalog: {cat}.{sch}")

for name in m["order"]:
    ddl_file = next(DDL_DIR.glob(f"*_{name}.sql"))
    stmt = ddl_file.read_text().rstrip().rstrip(";")
    stmt = backtick_col_list(remap(stmt))
    typ = m["carry_set"][name]["type"]
    # fully reclaim any pre-existing object of the same name (idempotent re-run)
    for drop in (f"DROP MATERIALIZED VIEW IF EXISTS {cat}.{sch}.{name}",
                 f"DROP VIEW IF EXISTS {cat}.{sch}.{name}",
                 f"DROP TABLE IF EXISTS {cat}.{sch}.{name}"):
        try:
            sql.run(drop, catalog=None, schema=None)
        except Exception:
            pass
    try:
        sql.run(force_replace(stmt), catalog=None, schema=None)
        ok(f"{typ:<18} {name}")
    except Exception as e:
        fail(f"{name}: {e}")

print(f"\nStage 02: created {len(m['order'])} objects in {cat}.{sch}")

# COMMAND ----------

# MAGIC %md ## Verify — all carry-set objects present

# COMMAND ----------

_, trows = sql.run(
    f"SELECT table_name FROM {cat}.information_schema.tables WHERE table_schema='{sch}'",
    catalog=None, schema=None)
_, frows = sql.run(
    f"SELECT routine_name FROM {cat}.information_schema.routines WHERE routine_schema='{sch}'",
    catalog=None, schema=None)
present = {r[0] for r in trows} | {r[0] for r in frows}
missing = set(m["order"]) - present
if missing:
    fail(f"missing in target: {sorted(missing)}")
ok(f"all {len(m['order'])} carry-set objects present in {cat}.{sch}")
print("Stage 02 verify: PASS")
