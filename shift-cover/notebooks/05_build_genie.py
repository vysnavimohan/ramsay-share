# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 05 — Recreate the Genie space (idempotent)
# MAGIC Rebuilds the "Ramsay Workforce — Nurse Replacement" Genie space from the **shipped**
# MAGIC definition (`artefacts/genie.json`): its `table_identifiers` + all 24 curated instructions
# MAGIC (glossary, hospital synonyms, replacement-eligibility rules, row-limit policy), remapped to
# MAGIC your target schema. **No source workspace is read.**
# MAGIC
# MAGIC **Idempotent:** deletes a previously-recorded space before recreating, so re-runs never
# MAGIC orphan duplicates.

# COMMAND ----------

# MAGIC %run ./_common

# COMMAND ----------

ARTEFACT = ARTEFACTS / "genie.json"
TITLE = "Ramsay Workforce — Nurse Replacement"

w = target_sql().w
if not ARTEFACT.exists():
    fail(f"shipped Genie definition missing: {ARTEFACT}")
g = json.loads(ARTEFACT.read_text())
tables = g.get("table_identifiers", [])
instructions = g.get("instructions", [])
tgt_tables = [remap(t) for t in tables]

# idempotent: remove a previously-recorded space
prev = manifest_get("genie", {}).get("GENIE_WORKFORCE", {}).get("space_id")
if prev:
    try:
        w.api_client.do("DELETE", f"/api/2.0/data-rooms/{prev}")
        ok(f"removed previous space {prev}")
    except Exception as e:
        print(f"  (warn) could not delete previous space {prev}: {e}")

space = w.api_client.do("POST", "/api/2.0/data-rooms", body={
    "display_name": f"{TITLE} [{CFG['TARGET_SCHEMA']}]",
    "description": g.get("description", ""),
    "warehouse_id": CFG["WAREHOUSE_ID"],
    "table_identifiers": tgt_tables,
})
if "space_id" not in space:
    fail(f"create space failed: {json.dumps(space)[:300]}")
sid = space["space_id"]
ok(f"created space {sid} with {len(tgt_tables)} tables")

applied = 0
for ins in instructions:
    body = {"title": ins.get("title"), "content": remap(ins.get("content")),
            "instruction_type": ins.get("instruction_type"), "status": "ACCEPTED"}
    r = w.api_client.do("POST", f"/api/2.0/data-rooms/{sid}/instructions", body=body)
    applied += 1 if ("instruction_id" in r or "id" in r) else 0
ok(f"re-applied {applied}/{len(instructions)} instructions")

host = w.config.host.rstrip("/")
manifest_put("genie", {"GENIE_WORKFORCE": {
    "space_id": sid, "title": TITLE, "source_id": g.get("source_id"),
    "instruction_count": applied, "url": f"{host}/genie/rooms/{sid}"}})
print(f"\nStage 05: Genie space -> {host}/genie/rooms/{sid}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify — smoke-test a live question against the target schema
# MAGIC Uses the Conversation API; allow ~1–2 min.

# COMMAND ----------

SMOKE_Q = "How many open shifts need cover in the next 7 days?"
entry = manifest_get("genie", {}).get("GENIE_WORKFORCE", {})
sid = entry.get("space_id")
ok(f"space recorded: {sid} ({entry.get('instruction_count')} instructions)")

msg = w.genie.start_conversation_and_wait(space_id=sid, content=SMOKE_Q)
attachments = getattr(msg, "attachments", []) or []
sqls = " ".join((getattr(getattr(a, "query", None), "query", "") or "") for a in attachments)
if CFG["TARGET_SCHEMA"] not in sqls:
    print(f"  (warn) smoke-test SQL did not clearly target {CFG['TARGET_SCHEMA']}; inspect manually: {sqls[:200]}")
else:
    ok(f"Genie answered against {CFG['TARGET_SCHEMA']}")
print("Stage 05 verify: done")
