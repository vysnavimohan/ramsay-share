# Databricks notebook source
# MAGIC %md
# MAGIC # _common — shared config + helpers (AI-Supervisor handover)
# MAGIC
# MAGIC `%run` this from every stage notebook. It reads deployment parameters from **notebook
# MAGIC widgets** (no `config.env`, no profile), authenticates with the **notebook's own identity**
# MAGIC (`WorkspaceClient()` — no source workspace), runs SQL through the configured **SQL warehouse**,
# MAGIC and resolves the package directory so stages can read `ddl/`, `artefacts/`, `MANIFEST.json`.
# MAGIC
# MAGIC This package reads **no source workspace** — every object ships as a captured artefact and is
# MAGIC remapped from its origin catalog/schema (`ramsay_health.ops`) onto your target at build time.

# COMMAND ----------

import io
import json
import re
import time
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

ORIGIN_CATALOG = "ramsay_health"
ORIGIN_SCHEMA = "ops"

# COMMAND ----------

dbutils.widgets.text("target_catalog", "classic_stable_82ujqz", "Target catalog (must already exist)")
dbutils.widgets.text("target_schema", "ramsay_ai_supervisor", "Target schema (created if absent)")
dbutils.widgets.text("warehouse_id", "7464666eb7d50c27", "SQL warehouse id (runs all SQL)")
dbutils.widgets.text("staging_volume", "", "Staging Volume (blank => <catalog>.<schema>._staging)")
dbutils.widgets.text("data_volume_path", "", "Volume path holding uploaded parquet data/ (blank => staging volume)")
dbutils.widgets.text("app_name", "ramsay-ai-supervisor", "Databricks App name (<=30 chars)")
dbutils.widgets.text("app_source_path", "", "Workspace path to the uploaded, unzipped app source (Stage 06)")
dbutils.widgets.text("fm_endpoint", "databricks-gpt-oss-120b", "Foundation-model endpoint for the app")
dbutils.widgets.text("lakebase_instance", "", "Lakebase instance name (blank => skip Lakebase, Stage 05b no-op)")
dbutils.widgets.text("never_touch", "ramsay_workforce", "Comma-sep catalogs/ids teardown must never remove")


def _cfg():
    c = {
        "TARGET_CATALOG": dbutils.widgets.get("target_catalog").strip(),
        "TARGET_SCHEMA": dbutils.widgets.get("target_schema").strip(),
        "WAREHOUSE_ID": dbutils.widgets.get("warehouse_id").strip(),
        "APP_NAME": dbutils.widgets.get("app_name").strip(),
        "FM_ENDPOINTS_REQUIRED": dbutils.widgets.get("fm_endpoint").strip(),
        "APP_SOURCE_PATH": dbutils.widgets.get("app_source_path").strip(),
        "LAKEBASE_INSTANCE": dbutils.widgets.get("lakebase_instance").strip(),
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

def _pkg_dir():
    ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
    nb_path = ctx.notebookPath().get()          # /.../ramsay-share/ai-supervisor/notebooks/_common
    pkg_ws = nb_path.rsplit("/", 2)[0]           # -> /.../ramsay-share/ai-supervisor
    p = Path("/Workspace" + pkg_ws)
    if p.exists():
        return p
    raise RuntimeError(
        f"package dir not found at {p}. Add this repo as a Git folder, or import the whole "
        f"'ai-supervisor' folder so ddl/ artefacts/ MANIFEST.json sit next to notebooks/.")


PKG = _pkg_dir()
DDL_DIR = PKG / "ddl"
DATA_DIR = PKG / "data"
ARTEFACTS = PKG / "artefacts"
MANIFEST = PKG / "MANIFEST.json"
DEPLOY_MANIFEST = PKG / "deployment_manifest.json"
print("Package dir:", PKG)

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
    tcat, tsch = cfg["TARGET_CATALOG"], cfg["TARGET_SCHEMA"]
    tgt = f"{tcat}.{tsch}"
    text = (text or "").replace(f"`{ORIGIN_CATALOG}`.`{ORIGIN_SCHEMA}`.", f"`{tcat}`.`{tsch}`.")
    text = text.replace(f"{ORIGIN_CATALOG}.{ORIGIN_SCHEMA}.", f"{tgt}.")
    text = re.sub(rf"\b{re.escape(ORIGIN_SCHEMA)}\.", f"{tgt}.", text)
    return text


def backtick_col_list(text):
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
