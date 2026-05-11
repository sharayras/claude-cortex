---
name: Memory protocol (canonical)
description: Rules on HOW to use cortex memory — tooling BGE-M3, skills, hooks, enriched frontmatter, session workflows. Re-read whenever memory feels out-of-sync with code.
type: feedback
last_verified: 2026-05-11
---
# Memory Protocol — claude-cortex

This memory system is a local-first cortex: markdown files in `~/.claude/projects/<PROJECT_ID>/memory/` + BGE-M3 vector search + CLI scripts + skills + hooks. This document is the **meta-memory** — how to use the memory itself.

Re-read this when you sense desynchronization with the actual code.

## The 3 long-term memory types

Inspired by cognitive science applied to AI agents (Mem0, Letta, 2026 state-of-the-art).

### Semantic — "what"
Stable project facts: versions, thresholds, canonical names, architectures, design decisions.
- Storage: `project_*.md`
- Expected freshness: long (months). Needs `last_verified` + ideally `assertions:` (verified by `verify.py`)

### Procedural — "how"
Behavior rules, workflows, repeated recipes.
- Storage: `feedback_*.md`
- Freshness: indefinite. Updated when user corrects or adds a rule.

### Episodic — "when"
Notable one-time events, incidents, time-contextual decisions.
- Storage: `project_session_*.md`
- Freshness: frozen (it's the past). Archive to `_archive/` after months if no longer relevant.

## CLI tooling (`scripts/`)

### `vector.py` — semantic search (reflex #1)

```bash
python scripts/vector.py search "<free topic>" --k 3
```

BGE-M3 local, ~30 ms. **Use BEFORE any grep** when the user mentions a topic. Confidence threshold: score > 0.4.

Reindex: `vector.py index` (automatic via `/sync-memory`, mtime-based).

First run: downloads BGE-M3 (~1 GB) from HuggingFace, ~5-10 min. Global sentence-transformers cache — if already downloaded for another project, instant.

### `note.py` — quick capture

```bash
python scripts/note.py "<your fact in free-form text>"
python scripts/note.py --type project "<stable project fact>"
```

Auto-generates frontmatter + extracts triggers + **enforced anti-duplicate** (vector search before write). Refuses creation if top-1 score > 0.6 (suggests extending the existing memory).

### `verify.py` — assertions vs code

Checks each `assertions:` field of frontmatters against real source.

```bash
python scripts/verify.py
python scripts/verify.py --fail-only  # CI-friendly filter
```

A FAIL = memory that drifted. Fix before any other action.

### `rebuild_index.py` — regenerate MEMORY.md

Rebuilds MEMORY.md from `index_entry:` fields of frontmatters. **MEMORY.md is auto-generated** — never edit by hand.

Workflow: modify a memory's `index_entry:` → run `rebuild_index.py --write` (or `/sync-memory`).

Dry-run first if unsure: `rebuild_index.py --diff`.

Layout (sections, prologue, epilogue, sub-files) is loaded from `cortex_config.yaml` if present in the project root.

## Skills

| Skill | What it does | When to invoke |
|---|---|---|
| `/sync-memory` | Orchestrates verify + rebuild_index + vector reindex | After creating/modifying a memory |
| `/audit-memory` | Freshness + duplicates + broken links + code inconsistencies | Monthly routine |
| `/consolidate-memory` | Sleep-phase: extracts conversational learnings into memories | End of session |
| `/handoff` | Generates SESSION_HANDOFF.md + SESSION_HANDOFF_DETAIL.md | Closing a session |

## Session workflows

### Startup (mandatory)

1. Read any project handoff file (e.g. `SESSION_HANDOFF.md`)
2. Read `MEMORY.md` — the auto-generated index (loaded auto if hook configured)
3. Confirm to user: *"I have read the handoff. Resuming on X."*

### Mid-session

- **Topic mentioned** → `vector.py search` before any grep
- **Project fact change** (design decision, knob value, doc authored) → create/update memory **in the same response**, not batched
- **Non-obvious finding / corrected rule** → create the memory immediately

### End of session

Recommended order (skills):
1. `/handoff` — generate handoff files
2. `/consolidate-memory` — extract conversational learnings
3. `/sync-memory` — reindex BGE-M3 + verify

## Enriched frontmatter format

### Minimum required

```yaml
---
name: <short descriptive title>
description: <one sentence for semantic search — be specific>
type: user | feedback | project | reference
---
```

### For type=project (add)

```yaml
last_verified: YYYY-MM-DD     # date of last check vs code/design
```

### Optional fields (but valuable)

```yaml
priority: critical | high | normal | low
triggers: [word1, word2, word3]    # boosts vector search
related: [other_memory.md, ...]    # link graph
supersedes: old_filename.md        # replaces an obsolete memory
assertions:                         # checkable by verify.py
  - source: src/path/file.py
    contains: 'EXPECTED_LITERAL = "value"'
  - source: design/spec.md
    regex: 'pa_pool\s*=\s*\d+'
index_entry:                        # for rebuild_index.py
  section: "🧠 Semantic — Design"
  order: 10
  label: "Combat DNA"
  hook: "Hero + 1 ally · PA unified · 4-dir facing"
originSessionId: <session uuid of creation>
```

### Body structure (feedback/project)

Lead with the rule/fact, then:
- **Why:** rationale (incident, constraint, preference)
- **How to apply:** when/where it kicks in

## Anti-duplicates (mandatory before creation)

**Search first**:

```bash
python scripts/vector.py search "<topic>" --k 3
```

- Top-1 score > 0.6 → **extend** existing memory, don't duplicate
- Top-1 score 0.4-0.6 → re-read before deciding
- Score < 0.4 → OK to create a new memory

The `memory-write-check` hook **blocks** Write on new memory at score ≥ 0.6.

## Archiving and supersession

### Supersession procedure (major rewrite)

**Rule: any major rewrite of a memory must archive the old one, not overwrite.**

1. Copy current memory to `memory/_archive/YYYY-MM-DD_<name>.md`
2. Remove `index_entry:` from the archived copy (so it leaves rebuild_index)
3. Write the new version at the original location
4. Add `supersedes: _archive/YYYY-MM-DD_<name>.md` to the new frontmatter
5. `rebuild_index.py --write` (or `/sync-memory`) to propagate

**Why:** direct write = history loss. Explicit supersession lets you trace decisions and detect loops.

### Pure archiving (obsolescence without replacement)

1. Move the file to `memory/_archive/`
2. Remove `index_entry:` if present
3. Run `rebuild_index.py --write` → the line disappears from MEMORY.md
4. `/sync-memory` to reindex BGE-M3

## Anti-patterns

- **Cite a memory as absolute truth** without `verify.py` or grep confirmation
- **Create a memory** without anti-duplicate via `vector.py search`
- **Edit MEMORY.md by hand** — auto-generated, modify `index_entry:` then `rebuild_index.py --write`
- **Mix episodic and semantic** in the same memory
- **Forget `last_verified`** on a project memory → silent drift
- **Batch-update at end of session** project facts modified during the work — rule: *continuous encoding MANDATORY*
- **Rewrite a memory without archiving the old version** — use the supersession procedure

---

*This protocol is itself a memory. If it becomes outdated or no longer reflects actual usage, update it — and run `/sync-memory` afterward.*
