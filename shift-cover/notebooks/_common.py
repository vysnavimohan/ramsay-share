# Databricks notebook source
# MAGIC %md
# MAGIC # _common — shared config + helpers (Shift-Cover handover)
# MAGIC
# MAGIC `%run` this from every stage notebook. It:
# MAGIC - reads deployment parameters from **notebook widgets** (no `config.env`, no profile),
# MAGIC - authenticates with the **notebook's own identity** (`WorkspaceClient()` — no source workspace),
# MAGIC - runs SQL through the configured **SQL warehouse** (same path the CLI package used, so
# MAGIC   `CREATE MATERIALIZED VIEW` / `... WITH METRICS` behave exactly as verified),
# MAGIC - resolves the package directory (this repo folder in the workspace) so stages can read
# MAGIC   `ddl/`, `artefacts/`, `MANIFEST.json`, and writes `deployment_manifest.json` back to it.
# MAGIC
# MAGIC This package reads **no source workspace** — every object ships as a captured artefact and is
# MAGIC remapped from its origin catalog/schema onto your target at build time.

# COMMAND ----------

import io
import json
import re
import time
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

# The shipped artefacts (DDL, dashboard.json, genie.json) are qualified with the ORIGIN
# catalog.schema they were captured from. Stages 2/4/5 remap this origin -> your target.
# This is a fixed property of the package, not recipient config.
ORIGIN_CATALOG = "ramsay_workforce"
ORIGIN_SCHEMA = "allocate"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Widgets — deployment parameters
# MAGIC Set these once (top of any stage notebook) and they persist across `%run`.

# COMMAND ----------

dbutils.widgets.text("target_catalog", "classic_stable_82ujqz", "Target catalog (must already exist)")
dbutils.widgets.text("target_schema", "ramsay_shiftcover", "Target schema (created if absent)")
dbutils.widgets.text("warehouse_id", "7464666eb7d50c27", "SQL warehouse id (runs all SQL)")
dbutils.widgets.text("staging_volume", "", "Staging Volume (blank => <catalog>.<schema>._staging)")
dbutils.widgets.text("app_name", "ramsay-shift-cover", "Databricks App name (<=30 chars)")
dbutils.widgets.text("fm_endpoint", "databricks-gpt-oss-120b", "Foundation-model endpoint for the app")
dbutils.widgets.text("data_volume_path", "", "Volume path holding uploaded parquet data/ (blank => staging volume)")
dbutils.widgets.text("app_source_path", "", "Workspace/Volume path to the uploaded, unzipped app source (Stage 6)")
dbutils.widgets.text("never_touch", "ramsay_health", "Comma-sep catalogs/ids teardown must never remove")


def _cfg():
    c = {
        "TARGET_CATALOG": dbutils.widgets.get("target_catalog").strip(),
        "TARGET_SCHEMA": dbutils.widgets.get("target_schema").strip(),
        "WAREHOUSE_ID": dbutils.widgets.get("warehouse_id").strip(),
        "APP_NAME": dbutils.widgets.get("app_name").strip(),
        "FM_ENDPOINTS_REQUIRED": dbutils.widgets.get("fm_endpoint").strip(),
        "APP_SOURCE_PATH": dbutils.widgets.get("app_source_path").strip(),
        "NEVER_TOUCH": dbutils.widgets.get("never_touch").strip(),
    }
    sv = dbutils.widgets.get("staging_volume").strip()
    c["STAGING_VOLUME"] = sv or f'{c["TARGET_CATALOG"]}.{c["TARGET_SCHEMA"]}._staging'
    dv = dbutils.widgets.get("data_volume_path").strip()
    if dv:
        c["DATA_VOLUME_PATH"] = dv.rstrip("/")
    else:
        v = c["STAGING_VOLUME"].split(".")
        c["DATA_VOLUME_PATH"] = f"/Volumes/{v[0]}/{v[1]}/{v[2]}"
    return c


CFG = _cfg()
print("Target :", CFG["TARGET_CATALOG"] + "." + CFG["TARGET_SCHEMA"])
print("Warehouse:", CFG["WAREHOUSE_ID"])


def never_touch(cfg=CFG):
    return [x.strip() for x in cfg.get("NEVER_TOUCH", "").split(",") if x.strip()]

# COMMAND ----------

# MAGIC %md
# MAGIC ## Package directory — resolve sibling `ddl/`, `artefacts/`, `MANIFEST.json`
# MAGIC When this repo is added as a **Git folder** (or the folder is imported), the notebooks live
# MAGIC at `<pkg>/notebooks/`. We resolve `<pkg>` from the running notebook's own path so file reads
# MAGIC work without any absolute path baked in.

# COMMAND ----------

def _pkg_dir():
    ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
    nb_path = ctx.notebookPath().get()          # e.g. /Repos/me/ramsay-share/shift-cover/notebooks/_common
    pkg_ws = nb_path.rsplit("/", 2)[0]           # -> /Repos/me/ramsay-share/shift-cover
    p = Path("/Workspace" + pkg_ws)
    if p.exists():
        return p
    # Fallback: notebook imported outside a repo — allow an override widget.
    raise RuntimeError(
        f"package dir not found at {p}. Add this repo as a Git folder, or import the whole "
        f"'shift-cover' folder so ddl/ artefacts/ MANIFEST.json sit next to notebooks/.")


PKG = _pkg_dir()
DDL_DIR = PKG / "ddl"
DATA_DIR = PKG / "data"
ARTEFACTS = PKG / "artefacts"
MANIFEST = PKG / "MANIFEST.json"
DEPLOY_MANIFEST = PKG / "deployment_manifest.json"
print("Package dir:", PKG)

# COMMAND ----------

# MAGIC %md
# MAGIC ## SQL executor (warehouse) + manifest helpers + remap

# COMMAND ----------

class SQL:
    """SQL executor bound to the notebook identity + the configured warehouse."""

    def __init__(self, warehouse_id, catalog=None, schema=None):
        self.w = WorkspaceClient()
        self.warehouse_id = warehouse_id
        self.catalog = catalog
        self.schema = schema

    def run(self, sql, catalog=None, schema=None):
        r = self.w.statement_execution.execute_statement(
            statement=sql, warehouse_id=self.warehouse_id, wait_timeout="50s",
            catalog=catalog if catalog is not None else self.catalog,
            schema=schema if schema is not None else self.schema)
        while r.status.state in (StatementState.PENDING, StatementState.RUNNING):
            time.sleep(2)
            r = self.w.statement_execution.get_statement(r.statement_id)
        if r.status.state != StatementState.SUCCEEDED:
            msg = r.status.error.message if r.status.error else r.status.state
            raise RuntimeError(f"SQL FAILED: {msg}\n--- statement ---\n{sql[:500]}")
        cols = [c.name for c in r.manifest.schema.columns] if r.manifest.schema.columns else []
        rows = r.result.data_array if (r.result and r.result.data_array) else []
        return cols, rows

    def scalar(self, sql, **kw):
        _, rows = self.run(sql, **kw)
        return rows[0][0] if rows and rows[0] else None


def target_sql(cfg=CFG):
    return SQL(cfg["WAREHOUSE_ID"], cfg["TARGET_CATALOG"], cfg["TARGET_SCHEMA"])


def _load_deploy():
    if DEPLOY_MANIFEST.exists():
        try:
            return json.loads(DEPLOY_MANIFEST.read_text())
        except Exception:
            return {}
    return {}


def manifest_get(key, default=None):
    return _load_deploy().get(key, default)


def manifest_put(key, value):
    d = _load_deploy()
    d[key] = value
    DEPLOY_MANIFEST.write_text(json.dumps(d, indent=2))
    return d


def remap(text, cfg=CFG):
    """Rewrite ORIGIN_CATALOG.ORIGIN_SCHEMA -> target, in every form the artefacts use."""
    tcat, tsch = cfg["TARGET_CATALOG"], cfg["TARGET_SCHEMA"]
    tgt = f"{tcat}.{tsch}"
    text = (text or "").replace(f"`{ORIGIN_CATALOG}`.`{ORIGIN_SCHEMA}`.", f"`{tcat}`.`{tsch}`.")
    text = text.replace(f"{ORIGIN_CATALOG}.{ORIGIN_SCHEMA}.", f"{tgt}.")
    text = re.sub(rf"\b{re.escape(ORIGIN_SCHEMA)}\.", f"{tgt}.", text)
    return text


def backtick_col_list(text):
    """Backtick bare multi-word columns in a metric-view CREATE header so it re-parses."""
    m = re.search(r"^(CREATE VIEW [^\(]+\()([^\)]*)(\))", text, re.S)
    if not m:
        return text
    head, cols, tail = m.groups()
    fixed = []
    for c in cols.split(","):
        name = c.strip()
        if name and not name.startswith("`") and " " in name:
            name = f"`{name}`"
        fixed.append("\n  " + name)
    return text[:m.start()] + head + ",".join(fixed) + tail + text[m.end():]


def force_replace(stmt):
    """CREATE -> CREATE OR REPLACE for idempotent re-runs (skips MATERIALIZED VIEW: handled by DROP)."""
    s = stmt.lstrip()
    up = s.upper()
    if up.startswith("CREATE OR REPLACE") or up.startswith("CREATE MATERIALIZED VIEW"):
        return stmt
    if up.startswith("CREATE "):
        return "CREATE OR REPLACE " + s[len("CREATE "):]
    return stmt


def ok(msg):
    print(f"  ✓ {msg}")


def fail(msg):
    raise RuntimeError(f"✗ {msg}")


print("_common loaded: CFG, target_sql(), remap(), force_replace(), manifest_*(), ok/fail")
