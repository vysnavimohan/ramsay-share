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
# MAGIC ## Deployment parameters — set ONCE in `00_preflight`, saved, reused everywhere
# MAGIC You choose catalog/schema/warehouse/etc. **only in `00_preflight`** (widgets render there).
# MAGIC Preflight saves them to `deploy_config.json` in the package folder; every later notebook
# MAGIC reads that file via `%run ./_common` — no widgets to set again. (Widgets defined inside a
# MAGIC `%run` helper don't render in the parent's UI, which is why they live in preflight only.)

# COMMAND ----------

# Fixed for these demos — the app's LLM endpoint. Not a widget (always this value).
FM_ENDPOINT = "databricks-gpt-oss-120b"

# Canonical parameter keys + their defaults (used to pre-fill the preflight widgets and as the
# fallback if nothing has been saved yet). fm_endpoint is intentionally NOT here (hardcoded above).
PARAM_DEFAULTS = {
    "target_catalog": "classic_stable_82ujqz",
    "target_schema": "ramsay_shiftcover",
    "warehouse_id": "7464666eb7d50c27",
    "staging_volume": "",
    "data_volume_path": "",
    "app_name": "ramsay-shift-cover",
    "app_source_path": "",
    # Safety guard for 99_teardown — refuses to drop anything whose catalog/id is listed here.
    # Defaults to the OTHER Ramsay demo's catalog so a mis-set teardown can't nuke it. Set-and-forget.
    "never_touch": "ramsay_health",
}


def _derive(raw):
    """Turn a raw {key: value} dict into the CFG the stages use (fills volume defaults)."""
    g = lambda k: (raw.get(k) or PARAM_DEFAULTS.get(k, "")).strip()
    c = {
        "TARGET_CATALOG": g("target_catalog"),
        "TARGET_SCHEMA": g("target_schema"),
        "WAREHOUSE_ID": g("warehouse_id"),
        "APP_NAME": g("app_name"),
        "FM_ENDPOINTS_REQUIRED": FM_ENDPOINT,
        "APP_SOURCE_PATH": g("app_source_path"),
        "NEVER_TOUCH": g("never_touch"),
    }
    sv = g("staging_volume")
    c["STAGING_VOLUME"] = sv or f'{c["TARGET_CATALOG"]}.{c["TARGET_SCHEMA"]}._staging'
    dv = g("data_volume_path")
    if dv:
        c["DATA_VOLUME_PATH"] = dv.rstrip("/")
    else:
        v = c["STAGING_VOLUME"].split(".")
        c["DATA_VOLUME_PATH"] = f"/Volumes/{v[0]}/{v[1]}/{v[2]}"
    return c

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
DEPLOY_CONFIG = PKG / "deploy_config.json"   # written by 00_preflight, read by every other stage
print("Package dir:", PKG)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load the saved deployment parameters (written by `00_preflight`)

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


# CFG is derived from the saved config (preflight) — or defaults if preflight hasn't run yet.
CFG = _derive(_load_saved())
if not DEPLOY_CONFIG.exists():
    print("⚠️  deploy_config.json not found — using DEFAULTS. Run 00_preflight first to set + save "
          "your catalog/schema/warehouse.")
print("Target :", CFG["TARGET_CATALOG"] + "." + CFG["TARGET_SCHEMA"])
print("Warehouse:", CFG["WAREHOUSE_ID"])


def never_touch(cfg=CFG):
    return [x.strip() for x in cfg.get("NEVER_TOUCH", "").split(",") if x.strip()]

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
