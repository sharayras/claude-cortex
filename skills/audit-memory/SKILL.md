---
name: audit-memory
description: Audits the memory system — detects stale memories, duplicates, broken links, inconsistencies vs code/design. Invoke when user says "audit memory", "check memory", "verify my memories", or periodically (monthly) for hygiene.
---

# Skill: audit-memory

## Purpose

Ensure the memory system stays synchronized with the actual project state. Detect:

- **Stale** memories (last_verified > 30 days for type=project)
- **Broken links** in MEMORY.md (referenced files missing)
- **Duplicates** (memories overlapping >50%)
- **Inconsistencies** vs current code/design — covered by `verify.py`
- **Overly long memories** (> 200 lines — split candidate)
- **MEMORY.md too long** (> 200 lines — auto-generated, watch with shorter index_entry hooks)

## Execution protocol

### 1. Inventory

```bash
python {{CORTEX_SCRIPTS_DIR}}/_paths.py
# Then list .md files in the printed MEMORY_DIR
```

Compare with MEMORY.md — any file absent from the index (no `index_entry:`) should be listed.

### 2. MEMORY.md link check

Parse MEMORY.md and any sub-index files, verify each `[label](file.md)` points to an existing file. Report broken links.

### 3. Freshness check

List `type=project` memories without `last_verified` — to enrich.

For those with `last_verified`, compute age:
- > 30 days: flag "to re-verify"
- > 90 days: flag "probably stale, re-verify or archive"

### 4. Consistency vs code/design check (verify.py)

```bash
python {{CORTEX_SCRIPTS_DIR}}/verify.py --fail-only
```

Assertions declared in frontmatters → compared to real code/design. Any FAIL = drifting memory → fix as priority.

### 5. Duplicate check (semantic, not grep)

Use vector search to detect overlaps. For each memory, query its description against the rest of the index; if another result has score > 0.6 to a different file, investigate manually.

The `memory-write-check` hook blocks **creation** of a duplicate at Write time. The audit covers duplicates that existed before the hook or were created via incremental Edit.

### 6. Length check

List memories sorted by line count. Flag:
- Memory > 150 lines: split candidate
- MEMORY.md > 200 lines: urgent compaction (condense `hook:` in frontmatters rather than trimming the index)

## Report to produce

Structured format:

```
## Memory audit — YYYY-MM-DD

### 🔴 Critical
- [broken links in MEMORY.md]
- [verify.py FAIL (memory diverges from code/design)]
- [memories without index_entry that should have one]

### 🟡 To re-verify
- [type=project memories > 30 days without last_verified bump]
- [potential duplicates (vector score > 0.6 between 2 memories)]
- [memories > 150 lines — split candidates]

### 🟢 Clean
- N memories, MEMORY.md at X lines
- verify.py: X PASS / Y FAIL
- last audit: YYYY-MM-DD

### Archive candidates
- [partial list of memories without recent usage]

### Proposed actions
- [corrections to apply, by priority]
```

## After the audit

After the report, **ask user** before fixing. Don't overwrite a memory without OK, except for:
- Updating `last_verified` (mechanical, OK silent)
- Fixing a dead link mechanically (idem)

For supersessions / archivals / content fixes → user OK mandatory.

## Recommended frequency

- **Monthly** as routine
- **After a marathon session** (>20 code/design changes) since memories likely drifted
- **Before a milestone gate** (consolidate memory state before locking a baseline)

## When to invoke

- User says "audit memory" / "check memory" / "verify my memories"
- Monthly routine
- Sudden doubt about the freshness of a remembered fact

## References

- Memory dir: see `python {{CORTEX_SCRIPTS_DIR}}/_paths.py` output
- `MEMORY_PROTOCOL.md` in the memory dir — memory management rules
- `/sync-memory` skill — sync after corrections
- `/consolidate-memory` skill — extract learnings to turn an audit into memories
