# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 03 — Load data from the uploaded parquet payload (idempotent)
# MAGIC Loads the shipped parquet snapshot into the target base tables with `COPY INTO`.
# MAGIC
# MAGIC ### Manual step (once, before this stage)
# MAGIC Upload the package's `data/` folder to the target **UC Volume** given by the `data_volume_path`
# MAGIC widget (defaults to the staging Volume `<catalog>.<schema>._staging`). The layout on the
# MAGIC Volume must be `<data_volume_path>/<table>/*.parquet` — i.e. copy `data/` as-is. See
# MAGIC `00_START_HERE.md`. If the Volume doesn't exist yet, this stage creates the staging Volume
# MAGIC for you; upload into it, then re-run.
# MAGIC
# MAGIC **Idempotent:** each table is `TRUNCATE`d then `COPY INTO … force=true`, so re-runs reload
# MAGIC exactly the current payload without double-counting.

# COMMAND ----------

# MAGIC %run ./_common

# COMMAND ----------

m = json.loads(MANIFEST.read_text())
sql = target_sql()
cat, sch = CFG["TARGET_CATALOG"], CFG["TARGET_SCHEMA"]
tables = m["data_tables"]
base = CFG["DATA_VOLUME_PATH"]

# ensure the staging Volume exists (harmless if the user uploaded to a different existing Volume)
sv = CFG["STAGING_VOLUME"].split(".")
try:
    sql.run(f"CREATE SCHEMA IF NOT EXISTS {sv[0]}.{sv[1]}", catalog=None, schema=None)
    sql.run(f"CREATE VOLUME IF NOT EXISTS {CFG['STAGING_VOLUME']}", catalog=None, schema=None)
    ok(f"staging volume ready: {CFG['STAGING_VOLUME']}")
except Exception as e:
    print(f"  (warn) could not ensure staging volume: {e}")

print(f"Loading {len(tables)} tables from {base}")
for t in tables:
    src = f"{base}/{t}"
    try:
        dbutils.fs.ls(src)
    except Exception:
        fail(f"no uploaded parquet at {src} — upload the package's data/ folder to the Volume "
             f"(see 00_START_HERE.md), then re-run this stage.")
    sql.run(f"TRUNCATE TABLE {cat}.{sch}.{t}", catalog=None, schema=None)
    sql.run(f"COPY INTO {cat}.{sch}.{t} FROM '{src}' "
            f"FILEFORMAT = PARQUET COPY_OPTIONS ('mergeSchema'='true', 'force'='true')",
            catalog=None, schema=None)
    ok(f"loaded {t}")

# warm the materialized-view cache for the demo
for n in m["by_type"].get("MATERIALIZED_VIEW", []):
    try:
        sql.run(f"REFRESH MATERIALIZED VIEW {cat}.{sch}.{n}", catalog=None, schema=None)
        ok(f"refreshed {n}")
    except Exception as e:
        print(f"    (warn) refresh {n} skipped: {e}")

print(f"\nStage 03: loaded {len(tables)} tables")

# COMMAND ----------

# MAGIC %md ## Verify — row counts match the shipped manifest + MEASURE spot check

# COMMAND ----------

expected = m.get("row_counts", {})
for t in tables:
    d = int(sql.scalar(f"SELECT count(*) FROM {cat}.{sch}.{t}"))
    exp = int(expected.get(t, -1))
    if exp >= 0 and d != exp:
        fail(f"row-count mismatch {t}: target {d} vs shipped manifest {exp}")
ok(f"row counts match shipped manifest for {len(tables)} tables")

dv = sql.scalar(f"SELECT MEASURE(total_shifts) FROM {cat}.{sch}.mv_shift_fulfilment")
if dv is None:
    fail("MEASURE(total_shifts) returned nothing on target mv_shift_fulfilment")
ok(f"metric-view MEASURE OK (mv_shift_fulfilment total_shifts = {dv})")
print("Stage 03 verify: PASS")
