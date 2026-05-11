---
name: sync-memory
description: Orchestrates all memory maintenance scripts — verify (assertions vs code/design), rebuild_index (auto-gen MEMORY.md), vector index (BGE-M3 re-embedding). Invoke after creating/modifying a memory, or when user says "sync memory" / "rebuild memory" / "update the cortex".
---

# Skill: sync-memory

## Purpose

Sync the entire memory system in one call. Runs the 3 scripts in optimal order:

1. **verify** — check memory assertions against real code/design
2. **rebuild_index** — regenerate `MEMORY.md` from frontmatter `index_entry:` fields
3. **vector index** — re-embed modified memories (BGE-M3)

## Execution protocol

### Step 1: verify (5s)

```bash
python {{CORTEX_SCRIPTS_DIR}}/verify.py
```

If FAIL detected → **stop and report**. Memories diverge from code/design: fix before continuing.

### Step 2: rebuild_index (dry-run diff then write)

```bash
python {{CORTEX_SCRIPTS_DIR}}/rebuild_index.py --diff
```

If diff non-empty → present to user, ask confirmation before write.

```bash
python {{CORTEX_SCRIPTS_DIR}}/rebuild_index.py --write
```

### Step 3: vector reindex

```bash
python {{CORTEX_SCRIPTS_DIR}}/vector.py index
```

Reindexes only modified memories (mtime-based). Usual time: a few seconds after the first build.

First run: BGE-M3 downloads from HuggingFace (~1 GB, 5-10 min). Sentence-transformers cache — if already cached for another project, instant.

## Final report

```
## Memory sync — YYYY-MM-DD HH:MM

### Verify
- N assertions: X PASS / Y FAIL / Z SKIP

### MEMORY.md index
- Rebuilt: N lines, M entries
- (or "already up to date")

### Vector index
- Re-indexed: N / Total
- Vector store: X documents
- Collection: cortex_<PROJECT_ID>
```

## When to invoke

- **After creating or modifying a memory** — to reindex and verify
- **Start of session** if user complains I cite stale things
- **End of session** to propagate learnings (with `/consolidate-memory`)
- **Monthly** as preventive routine (combined with `/audit-memory`)

## Anti-patterns

- **Don't run** the skill if nothing has changed in memory (useless)
- **Don't overwrite MEMORY.md** (step 2 write) without showing the diff first
- **Don't ignore** a verify FAIL — that's the signal a memory diverges from code/design

## Dependencies

- `{{CORTEX_SCRIPTS_DIR}}/_paths.py` — centralized paths
- `{{CORTEX_SCRIPTS_DIR}}/verify.py` · `rebuild_index.py` · `vector.py`
- Python venv with `chromadb`, `sentence-transformers`, `pyyaml` (cf. `{{CORTEX_SCRIPTS_DIR}}/requirements.txt`)
