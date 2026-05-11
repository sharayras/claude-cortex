---
name: consolidate-memory
description: "Sleep-phase" consolidation — extracts learnings from the current session (conversation + git log + files authored) and creates/updates the appropriate memories. Invoke at the end of a session (typically after /handoff) or after a marathon session that produced many decisions.
---

# Skill: consolidate-memory

## Purpose

Transform the experience of a session into memory usable by future sessions. Inspired by human sleep, which consolidates daily experiences into long-term memory.

## Input

- Current session conversation (implicit in context)
- `git log` since the session started
- Files created/modified on disk (docs, configs, code)
- Observed incidents and corrections

## Output

1. **New memories** if novel patterns emerged
2. **Updated memories** if existing rules were refined (bump `last_verified`)
3. **`project_session_YYYYMMDD.md`** capturing notable session events
4. Update of impacted memories

## Protocol

### Step 1: capture git state

```bash
git log --oneline --since="1 day ago"
git diff --stat HEAD@{1.day.ago}..HEAD | head -10
```

Identify commits from the session. If no commits (e.g. design-only session), rely on the conversation + files written.

### Step 2: detect correction patterns

In the session conversation, look for:

- **User corrections** like "no, rather X", "watch out for Y", "you didn't Z"
- If the same correction appears **2+ times** in the session → that's a rule to capture
- If user explicitly says "remember this", "note it" → memory to create immediately
- **Explicit design decisions** (constants, knobs, formulas) → `project_*` memory

### Step 3: pick the learning type

For each identified learning:

| Signal | Memory type | Example |
|---|---|---|
| Behavior rule | `feedback_*.md` | "Default to concise output, no trailing summaries" |
| Stable project fact | `project_*.md` | "Combat DNA — 4 foundational decisions" |
| Notable one-time incident | `project_session_YYYYMMDD.md` | "2026-05-11: ported memory system from project A to B" |
| Discovered external resource | `reference_*.md` | "BGE-M3 multilingual, ~30ms local latency" |

### Step 4: anti-duplicate before creation

**Mandatory** before creating a new memory:

```bash
python {{CORTEX_SCRIPTS_DIR}}/vector.py search "<keywords of the learning>" --k 3
```

- Top-1 score > 0.6 → memory already exists, **extend** rather than create
- Top-1 score 0.4-0.6 → re-read before deciding
- Score < 0.4 → new topic, create

### Step 5: create or update

For a new memory: follow `MEMORY_PROTOCOL.md` format. **Mandatory**: `name`, `description`, `type`, `last_verified` (if type=project). **Recommended**: `triggers`, `related`, `index_entry`, `assertions` if applicable.

For an update: modify content + bump `last_verified` to today.

**Anti-pattern**: rewriting a memory without archiving the previous version. Supersession procedure in `MEMORY_PROTOCOL.md` §Archiving.

### Step 6: session file

Create `project_session_YYYYMMDD.md` if the session produced significant content:

```markdown
---
name: Session YYYY-MM-DD — {short theme}
description: Factual session summary — commits, docs authored, key decisions, extracted learnings.
type: project
last_verified: YYYY-MM-DD
triggers: [session, YYYY-MM-DD, {main themes}]
index_entry:
  section: "📅 Episodic — Sessions"
  order: {auto-increment, or YYYYMMDD for chronological order}
  label: "Session YYYY-MM-DD — {theme}"
  hook: "{1-line hook}"
---

# Session YYYY-MM-DD — {theme}

## Commits / files authored
{list of commits with hash + subject; OR list of design docs/configs created without commit}

## Design decisions
{Gameplay/architecture choices made, with rationale.}

## Notable incidents
{What broke and how it recovered.}

## Learnings (captured as memories)
- [Link to feedback_X.md] — 1-line summary
- ...
```

### Step 7: final sync

Run `/sync-memory` to propagate changes through the vector index and MEMORY.md.

## Final report

```
## Consolidation — YYYY-MM-DD HH:MM

### New memories (N)
- feedback_xyz.md — 1-line description
- project_abc.md — ...

### Updated memories (M)
- project_def.md (last_verified bumped) — what changed
- ...

### Session file
- project_session_YYYYMMDD.md created / extended

### Sync
- Vector index: +N documents
- MEMORY.md: rebuilt (or up to date)
```

## Rules

- **No memory for one-shot info** — if it only serves this session, don't create
- **No duplicate** — vector search mandatory before creation
- **Always present to user** before overwriting existing content
- **last_verified** updated for anything touched
- **Index entry mandatory** for memories that should appear in MEMORY.md (otherwise out-of-index, OK for archives/internal)

## When to invoke

- **End of a notable session** — this skill turns session into durable memory
- **User says "remember this"** → create the memory immediately, don't wait
- **After an audit** (via `/audit-memory` that revealed drifts) — consolidate the corrections
- **After `/handoff`** — canonical chain: `/handoff` → `/consolidate-memory` → `/sync-memory`
