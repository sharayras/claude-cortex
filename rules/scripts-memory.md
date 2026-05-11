# Scripts Memory Rules

Path-scoped rule that Claude Code reads when working in the project. Loaded
automatically when files under `scripts/cortex/` (or whatever path you chose)
are involved.

## Process standards

- **At session start (MANDATORY)**: read any `SESSION_HANDOFF.md` + `MEMORY.md` (the auto-generated index) + the project's primary state file. Confirm to user: *"I have read the state, resuming on X."* Memory is the only continuity vector between sessions.
- **Repetitive workflows = skills, not improvisation**: `/sync-memory` after creating/modifying a memory · `/audit-memory` (monthly) · `/consolidate-memory` (end of session) · `/handoff` (close session).
- Memory scripts live in `scripts/cortex/` (or your configured path) and operate on the cortex memory dir at `~/.claude/projects/<PROJECT_ID>/memory/` + `_vector_index/` (Chroma BGE-M3).
- **Vector search before grep**: on any topical question, run `python scripts/cortex/vector.py search "<topic>" --k 3` before a blind grep. Latency < 100 ms, returns top-3 relevant memories with scores.
- `scripts/cortex/verify.py --fail-only`: drift detection. Compares memory assertions to current code/design state. Run on doubt or in routine `/audit-memory`.
- `scripts/cortex/rebuild_index.py --write`: regenerates MEMORY.md from frontmatter `index_entry:` fields. Without rebuild, a new memory doesn't appear in the index.
- The `/sync-memory` skill orchestrates verify + rebuild_index + vector reindex — prefer the skill over running scripts manually.
- **Continuous encoding mandatory**: modification of a project fact (design decision, knob value, formula) → update the corresponding memory IMMEDIATELY in the same response. Never batch at end of session.
- **Anti-duplicate mandatory** before creating a memory: `vector.py search "<topic>" --k 3` to check existence. If duplicate, extend rather than create.
- `MEMORY_PROTOCOL.md` (in the memory dir) = source of truth for types (`user`, `feedback`, `project`, `reference`) + enriched frontmatter + anti-duplicate rules.

## Anti-patterns

- ❌ Blind grep on `MEMORY.md` instead of `vector.py search` — waste of time, less relevant results.
- ❌ Create a memory without `rebuild_index` — the new memory exists on disk but isn't in the index, invisible in MEMORY.md.
- ❌ Memory tooling depending on project code (importing from the application) — memory scripts must be standalone to run even if the project is broken. Memory is a **cross-cutting** cortex.
- ❌ Modify a memory script without testing on a backup — cortex operations are semi-irreversible (deletes, replaces). Always back up the memory dir before structural changes.
- ❌ Hardcoded paths in the cortex code — use `_paths.py` which derives them automatically from cwd or env var.

## Cross-cuts

- `vector.py` is consumed by `MEMORY_PROTOCOL.md` — every session starts by reading the state + vector search.
- `rebuild_index.py` is called by skill `/sync-memory`.
- `verify.py` is called by skill `/sync-memory` (and `/audit-memory`).
- Hook `memory-impact` (PostToolUse Edit|Write) flags impacted memories after each tool call.
- Hook `memory-write-check` (PreToolUse Write) blocks duplicate memory creation at vector score ≥ 0.6.

## See also

- `MEMORY_PROTOCOL.md` (in the memory dir) — full memory system protocol
- `.claude/skills/sync-memory/SKILL.md` — sync workflow
- `.claude/skills/audit-memory/SKILL.md` — monthly audit
- `.claude/skills/consolidate-memory/SKILL.md` — end-of-session learning extraction
- `.claude/skills/handoff/SKILL.md` — session handoff
