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

# Deployment parameters are set ONCE in 00_preflight (widgets render there) and saved to
# deploy_config.json in the package folder; every later notebook reads that file via %run ./_common.
# (Widgets defined inside a %run helper don't render in the parent's UI, so they live in preflight.)
# Fixed for these demos (not widgets):
#  - FM_ENDPOINT: the app's LLM endpoint (always this value).
#  - NEVER_TOUCH: 99_teardown refuses to drop anything whose catalog/id is listed here (guards the
#    OTHER Ramsay demo's catalog).
FM_ENDPOINT = "databricks-gpt-oss-120b"
NEVER_TOUCH = "ramsay_workforce"

# The ONLY parameters preflight asks for (its widgets) and saves to deploy_config.json.
PARAM_DEFAULTS = {
    "target_catalog": "classic_stable_82ujqz",
    "target_schema": "ramsay_ai_supervisor",
    "warehouse_id": "7464666eb7d50c27",
    "staging_volume": "",
    "app_name": "ramsay-ai-supervisor",
}


def _derive(raw):
    """Turn the saved {key: value} dict into the CFG the stages use.
    data_volume_path is derived from the staging Volume; app_source_path (Stage 06) and
    lakebase_instance (Stage 05b) are their own notebooks' widgets, read from raw if present;
    never_touch/fm are fixed constants."""
    g = lambda k: (raw.get(k) or PARAM_DEFAULTS.get(k, "")).strip()
    c = {
        "TARGET_CATALOG": g("target_catalog"),
        "TARGET_SCHEMA": g("target_schema"),
        "WAREHOUSE_ID": g("warehouse_id"),
        "APP_NAME": g("app_name"),
        "FM_ENDPOINTS_REQUIRED": FM_ENDPOINT,
        "APP_SOURCE_PATH": (raw.get("app_source_path") or "").strip(),
        "LAKEBASE_INSTANCE": (raw.get("lakebase_instance") or "").strip(),
        "NEVER_TOUCH": NEVER_TOUCH,
    }
    sv = g("staging_volume")
    c["STAGING_VOLUME"] = sv or f'{c["TARGET_CATALOG"]}.{c["TARGET_SCHEMA"]}._staging'
    v = c["STAGING_VOLUME"].split(".")
    c["DATA_VOLUME_PATH"] = f"/Volumes/{v[0]}/{v[1]}/{v[2]}"
    return c

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
DEPLOY_CONFIG = PKG / "deploy_config.json"   # written by 00_preflight, read by every other stage
print("Package dir:", PKG)

# COMMAND ----------

def save_config(raw):
    """00_preflight calls this to persist the chosen parameters for all later notebooks."""
    DEPLOY_CONFIG.write_text(json.dumps(raw, indent=2))


def _load_saved():
    if DEPLOY_CONFIG.exists():
        try:
            return json.loads(DEPLOY_CONFIG.read_text())
        except Exception:
            return {}
    return {}


CFG = _derive(_load_saved())
if not DEPLOY_CONFIG.exists():
    print("⚠️  deploy_config.json not found — using DEFAULTS. Run 00_preflight first to set + save "
          "your catalog/schema/warehouse.")
print("Target :", CFG["TARGET_CATALOG"] + "." + CFG["TARGET_SCHEMA"])
print("Warehouse:", CFG["WAREHOUSE_ID"])


def never_touch(cfg=CFG):
    return [x.strip() for x in cfg.get("NEVER_TOUCH", "").split(",") if x.strip()]

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
