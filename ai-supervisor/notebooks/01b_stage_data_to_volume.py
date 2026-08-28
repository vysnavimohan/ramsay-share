# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 01b — Stage the shipped data into a UC Volume (no laptop needed)
# MAGIC The parquet payload ships **inside this Git folder** at `../data/`. Databricks checks it out
# MAGIC when you add the repo as a Git folder, so the files are already in the workspace — this stage
# MAGIC just copies them into a **UC Volume** (where `COPY INTO` in Stage 03 can read them).
# MAGIC
# MAGIC It (idempotently):
# MAGIC 1. creates the target **schema** (inside the existing catalog) and the **staging Volume**,
# MAGIC 2. copies every `data/<table>/*.parquet` from the Git folder into
# MAGIC    `<data_volume_path>/<table>/`.
# MAGIC
# MAGIC No manual upload, no laptop. (If you prefer to upload by hand via Catalog → Volume → Upload,
# MAGIC you can skip this stage — just make sure the Volume ends up with `<table>/*.parquet`.)
# MAGIC
# MAGIC > **Large-file note (AI-Supervisor only):** this package's data is ~41 MB and includes a
# MAGIC > ~26 MB `tbwlmds` parquet. Databricks Git folders enforce a per-file size limit, so a table
# MAGIC > may not check out. If this stage reports a missing/empty table, upload that table's parquet
# MAGIC > to the Volume via **Catalog → Volume → Upload** (or `databricks fs cp`) and re-run — the
# MAGIC > verify only requires the parquet to be present on the Volume, however it got there.

# COMMAND ----------

# MAGIC %run ./_common

# COMMAND ----------

m = json.loads(MANIFEST.read_text())
sql = target_sql()
cat, sch = CFG["TARGET_CATALOG"], CFG["TARGET_SCHEMA"]
tables = m["data_tables"]

# 1. schema + staging Volume (idempotent; catalog must already exist)
_, cats = sql.run(f"SHOW CATALOGS LIKE '{cat}'", catalog=None, schema=None)
if not any(r[0] == cat for r in cats):
    fail(f"catalog '{cat}' must already exist — set target_catalog to an existing catalog")
sql.run(f"CREATE SCHEMA IF NOT EXISTS {cat}.{sch}", catalog=None, schema=None)
sv = CFG["STAGING_VOLUME"].split(".")
sql.run(f"CREATE VOLUME IF NOT EXISTS {CFG['STAGING_VOLUME']}", catalog=None, schema=None)
ok(f"schema + volume ready: {cat}.{sch} / {CFG['STAGING_VOLUME']}")

# 2. copy data/<table>/*.parquet from the Git folder -> the Volume
#    DATA_DIR is a /Workspace path; dbutils.fs needs the file: scheme for workspace-local files.
base = CFG["DATA_VOLUME_PATH"]
copied = 0
for t in tables:
    srcdir = DATA_DIR / t
    files = sorted(srcdir.glob("*.parquet")) if srcdir.exists() else []
    if not files:
        fail(f"no parquet in the Git folder for {t} at {srcdir} — is the repo checked out with data/?")
    dst = f"{base}/{t}"
    try:
        dbutils.fs.mkdirs(dst)
    except Exception:
        pass
    for f in files:
        dbutils.fs.cp(f"file:{f.as_posix()}", f"{dst}/{f.name}")
        copied += 1
    ok(f"staged {t} ({len(files)} file(s)) -> {dst}")

print(f"\nStage 01b: staged {copied} parquet file(s) for {len(tables)} tables into {base}")

# COMMAND ----------

# MAGIC %md ## Verify — every table folder has parquet on the Volume

# COMMAND ----------

missing = []
for t in tables:
    try:
        n = len([x for x in dbutils.fs.ls(f"{base}/{t}") if x.name.endswith(".parquet")])
    except Exception:
        n = 0
    if n < 1:
        missing.append(t)
    else:
        ok(f"{t}: {n} parquet file(s) on volume")
if missing:
    fail(f"no parquet staged for: {missing}")
print("Stage 01b verify: PASS — data staged on the Volume, ready for Stage 03")
