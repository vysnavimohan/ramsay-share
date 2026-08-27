# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 01 — Validate the shipped carry set
# MAGIC This package ships everything the demo needs, captured once from the original build:
# MAGIC - `MANIFEST.json` — the 13-object carry set + types + dependency edges
# MAGIC - `ddl/NN_<obj>.sql` — ordered CREATE statements (origin-qualified; Stage 02 remaps)
# MAGIC - `data/<table>/*.parquet` — a data snapshot for every data-bearing base table
# MAGIC
# MAGIC There is **no source workspace to introspect**. This stage only confirms the shipped
# MAGIC artefacts are present and internally consistent so later stages have something to build from.

# COMMAND ----------

# MAGIC %run ./_common

# COMMAND ----------

if not MANIFEST.exists():
    fail(f"MANIFEST.json missing at {MANIFEST} — the package is incomplete")
m = json.loads(MANIFEST.read_text())

order = m.get("order", [])
if not order:
    fail("MANIFEST.json has an empty carry set — the package is incomplete")

# every object has a non-empty DDL file
for n in order:
    matches = list(DDL_DIR.glob(f"*_{n}.sql"))
    if not matches or matches[0].stat().st_size < 10:
        fail(f"DDL missing/empty for {n} (expected ddl/*_{n}.sql)")

# dependency-closed
names = set(m["carry_set"])
for n, meta in m["carry_set"].items():
    for r in meta["refs"]:
        if r not in names:
            fail(f"dangling ref {n} -> {r} not in carry set")

# every data table ships a parquet payload
for n in m["data_tables"]:
    files = list((DATA_DIR / n).glob("*.parquet")) if (DATA_DIR / n).exists() else []
    if not files:
        fail(f"no parquet payload shipped for {n} (expected data/{n}/*.parquet)")

by_type = m.get("by_type", {})
print("Carry set (shipped):", len(order), "objects —",
      ", ".join(f"{len(v)} {k}" for k, v in sorted(by_type.items())))
for n in m["data_tables"]:
    ok(f"payload present: {n} ({m['row_counts'].get(n, '?')} rows)")
ok(f"{len(order)} DDL files present and non-empty")
ok("carry set is dependency-closed")
ok(f"parquet payload present for {len(m['data_tables'])} data tables")
print("\nStage 01: shipped carry set validated (no source workspace read)")
