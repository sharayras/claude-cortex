---
name: handoff
description: Generates or updates SESSION_HANDOFF.md to pass the baton to the next session. Invoke at end of session, when user says "close out", "handoff", "that's it for today", "wrap up the session".
---

# Skill: handoff

## Purpose

Produce a `SESSION_HANDOFF.md` that lets the next session **resume work without re-discovering context**. The file should be read automatically at startup (configure the session-start-reminder hook to mention it).

## Canonical structure — 2 files

Default is **2 separate files** for any normal-sized session. See "When to skip the split" at bottom if the session is short.

### File 1: `SESSION_HANDOFF.md` (short, ≤ 150 lines)

Operational sections only — what the next session must read first.

```markdown
# SESSION_HANDOFF.md

> **First file to read at the start of the next session.**
> Describes the exact project state and the next work to attack.
>
> **⚠️ If you're reading this (Claude, next session):**
> 1. Confirm to user: *"I have read the handoff. Resuming on [X]."*
> 2. List 3 main points to prove you read it.
> 3. If something discussed is not here, **say so** rather than improvise.

Last update: YYYY-MM-DD (morning/afternoon/evening/night), session **{short theme}**.

---

## Quick summary

{3-5 bullets on what was done this session.}

**{N} commits pushed on `origin/main`** this session. All pushed / Not pushed / Working tree dirty.

---

## Project state

### Phase
- **Phase**: {pre-prod / prod / polish / release}
- **Active sprint**: {name + N° + status}

### Code (if applicable)
- **Branch**: {main / feature-x}
- **Tests**: {N pass, X fails}
- **Build status**: {OK / broken / not tested}

---

## Remaining work

### High priority
- {clear items, with estimate if relevant}

### Medium priority
- {short-term backlog}

---

## Next session startup

### Verification check
1. `git status --short` → {expected state}
2. `git log --oneline -5` → {expected latest commits}
3. Confirm to user: *"I have read the handoff. Resuming on [X]."*

⚠️ **NEVER include `pytest tests/` (or test runner) in the startup checklist of a handoff.** Previous session already tested. If working tree is clean, running tests at startup = token + time waste. Tests are only useful when about to modify code.

### Quick-start

```
1. Read SESSION_HANDOFF.md (this file)
2. Read MEMORY.md (auto-generated index, section-by-section view)
3. Vector search if specific topic mentioned: python scripts/vector.py search "<topic>" --k 3
4. Confirm to user
5. Propose: {concrete options}
```

---

> Full session story → `SESSION_HANDOFF_DETAIL.md`
```

### File 2: `SESSION_HANDOFF_DETAIL.md` (free-form, no line limit)

Source of truth — contains EVERYTHING that happened.

```markdown
# SESSION_HANDOFF_DETAIL.md — {short theme} — YYYY-MM-DD

## What was done

### 1. {Theme of commit / chantier / doc}
{Detail, approximate diff, commit links, paths.}

### 2. ...

---

## Commits pushed this session

```
<hash> <subject>
...
```

---

## Notable design decisions

{Decisions made, alternatives rejected, reasoning.}

---

## Incidents / learnings

{What almost went wrong, what was learned. Captures to turn into durable memories via /consolidate-memory.}

---

## Memories created / modified this session

{List by name: new + enriched. Lets the next session know where to look for new content.}
```

## 2-step generation

### Step A — Generate DETAIL first (source of truth)

`SESSION_HANDOFF_DETAIL.md` is written first because it contains EVERYTHING: commits, decisions, incidents, learnings, full context. No filter at this stage.

### Step B — Extract the short version from DETAIL

`SESSION_HANDOFF.md` is **extracted** from DETAIL, not rewritten from memory. Copy only operational sections (quick summary, project state, remaining work, quick-start). Condense long bullets. Target: ≤ 150 lines.

**Anti-divergence**: NEVER edit `SESSION_HANDOFF.md` directly after the fact. If a correction is needed, do it in DETAIL and re-extract the short version. The 2 files must stay consistent.

### Edge case: DETAIL > 500 lines

If DETAIL exceeds 500 lines (marathon session), propose interactively:

> *"DETAIL is {N} lines — split by theme into `SESSION_HANDOFF_DETAIL_<theme>.md` sub-files (targeted search + readability) or keep as one file (simplicity)?"*

The split is a **manual choice**, not an auto rule.

## When to skip the split

Short session (≤ 100 lines of handoff expected, e.g. quick hotfix, no-commit review session) → **1 file suffices**. Keep the name `SESSION_HANDOFF.md`. No DETAIL.

Signal for 1 file: < 3 commits, < 2 distinct chantiers, duration < 1h.

## Before generating

1. **Get git state**:
```bash
git status --short
git log --oneline -10
```

2. **Identify session commits** (vs those before) — ask user when the session started if unsure.

3. **List uncommitted working-tree items** — very important to document for the next session.

## Writing rules

- **Concrete and factual**: no "we worked a lot" — commits, files, decisions made
- **High priority**: what's blocking the next session from starting
- **No omissions**: if a refactor is in uncommitted working tree, say so
- **Mention new skills/memories** created during the session
- **Date in format** `YYYY-MM-DD (time-of-day)` — e.g. `2026-05-11 (night)`
- **NEVER write "Run the tests"** in startup instructions if no code change

## After writing — mandatory chain

The handoff is INCOMPLETE without these final steps:

### 1. Learnings consolidation

Invoke `/consolidate-memory` immediately after writing the handoff. Extracts patterns/corrections/notable incidents from the session into durable memories (feedback_*, project_session_*, etc.).

### 2. Memory index sync

Invoke `/sync-memory` after consolidation. Re-indexes the BGE-M3 vector store, rebuilds MEMORY.md auto, verifies assertions vs code/design.

### 3. Commit + push

If your project has a "no auto-commit" rule (see CLAUDE.md), don't auto-commit. Propose to user:

> *"Handoff written + memories consolidated + sync OK. Want me to commit + push? Proposed message: 'handoff: close session {short theme}'"*

If user OK → targeted `git add` (never `git add -A` without confirmation), commit with message, push if requested.

### Why this chain is mandatory

Without `/consolidate-memory` + `/sync-memory`, the handoff has a hole: SESSION_HANDOFF.md captures state but learnings aren't extracted as durable memories, and the vector index stays stale. The next session won't be able to find patterns via vector search.

**Complete handoff = SESSION_HANDOFF.md + durable memories + index sync (+ commit/push if user OK).**
