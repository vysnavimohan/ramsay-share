# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 05 — Recreate the 4 Genie agents (idempotent)
# MAGIC Rebuilds the supervisor's four Genie spaces from the **shipped** definitions
# MAGIC (`artefacts/genie.json`) — each agent's `table_identifiers` + curated instructions (glossary,
# MAGIC metric-view MEASURE() rules, certified example SQL), remapped to your target schema.
# MAGIC **No source workspace is read.**
# MAGIC
# MAGIC | env var | agent |
# MAGIC |---|---|
# MAGIC | `GENIE_CAPACITY` | Ramsay Capacity |
# MAGIC | `GENIE_PATIENT_FINANCE` | Ramsay Patient Activity & Finance |
# MAGIC | `GENIE_THROUGHPUT_FLOW` | Ramsay Throughput & Flow |
# MAGIC | `GENIE_WORKFORCE` | Ramsay Workforce |
# MAGIC
# MAGIC **Idempotent:** deletes previously-recorded spaces before recreating.
# MAGIC
# MAGIC > **Genie One note:** the supervisor app's *live* Q&A ("Genie One" conversational experience)
# MAGIC > needs a Claude model that is **not available in every region** (e.g. fevm-azure). The spaces
# MAGIC > still build and are usable directly; if the conversational smoke test can't complete in your
# MAGIC > region it is reported as a WARN, not a failure.

# COMMAND ----------

# MAGIC %run ./_common

# COMMAND ----------

ARTEFACT = ARTEFACTS / "genie.json"
if not ARTEFACT.exists():
    fail(f"shipped Genie definitions missing: {ARTEFACT}")
agents = json.loads(ARTEFACT.read_text())   # { GENIE_CAPACITY: {display_name, table_identifiers, instructions[], ...}, ... }

w = target_sql().w
host = w.config.host.rstrip("/")

# idempotent: delete previously-recorded spaces
prev = manifest_get("genie", {})
for env, entry in (prev.items() if isinstance(prev, dict) else []):
    sid = entry.get("space_id") if isinstance(entry, dict) else None
    if sid:
        try:
            w.api_client.do("DELETE", f"/api/2.0/data-rooms/{sid}")
            ok(f"removed previous space {env} {sid}")
        except Exception as e:
            print(f"  (warn) could not delete previous {env} {sid}: {e}")

created = {}
for env, a in agents.items():
    title = a.get("display_name", env)
    tgt_tables = [remap(t) for t in a.get("table_identifiers", [])]
    space = w.api_client.do("POST", "/api/2.0/data-rooms", body={
        "display_name": f"{title} [{CFG['TARGET_SCHEMA']}]",
        "description": a.get("description", ""),
        "warehouse_id": CFG["WAREHOUSE_ID"],
        "table_identifiers": tgt_tables,
    })
    if "space_id" not in space:
        fail(f"create space {env} failed: {json.dumps(space)[:300]}")
    sid = space["space_id"]
    applied = 0
    for ins in a.get("instructions", []):
        body = {"title": ins.get("title"), "content": remap(ins.get("content")),
                "instruction_type": ins.get("instruction_type", "TEXT_INSTRUCTION"), "status": "ACCEPTED"}
        r = w.api_client.do("POST", f"/api/2.0/data-rooms/{sid}/instructions", body=body)
        applied += 1 if ("instruction_id" in r or "id" in r) else 0
    ok(f"{env}: space {sid} ({len(tgt_tables)} tables, {applied} instructions)")
    created[env] = {"space_id": sid, "title": title, "instruction_count": applied,
                    "url": f"{host}/genie/rooms/{sid}"}

manifest_put("genie", created)
print(f"\nStage 05: created {len(created)} Genie spaces")

# COMMAND ----------

# MAGIC %md ## Verify — smoke-test the Capacity agent (WARN, not fail, if Genie One unavailable)

# COMMAND ----------

SMOKE_Q = "What is the average theatre utilisation by site?"
cap = manifest_get("genie", {}).get("GENIE_CAPACITY", {})
sid = cap.get("space_id")
if not sid:
    fail("no GENIE_CAPACITY space recorded — run the build cell first")
ok(f"Capacity space: {cap['url']} ({cap.get('instruction_count')} instructions)")
try:
    msg = w.genie.start_conversation_and_wait(space_id=sid, content=SMOKE_Q)
    attachments = getattr(msg, "attachments", []) or []
    sqls = " ".join((getattr(getattr(a, "query", None), "query", "") or "") for a in attachments)
    if CFG["TARGET_SCHEMA"] in sqls:
        ok(f"Capacity agent answered against {CFG['TARGET_SCHEMA']}")
    else:
        print(f"  (warn) smoke-test SQL did not clearly target {CFG['TARGET_SCHEMA']}: {sqls[:200]}")
except Exception as e:
    print(f"  WARN Genie conversational smoke test could not complete (Genie One / Claude model "
          f"may be unavailable in this region): {e}")
    print("       The 4 spaces are built and usable directly; this is not a build failure.")
print("Stage 05 verify: done")
