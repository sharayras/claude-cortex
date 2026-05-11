---
name: Example feedback memory — concise output preference
description: How feedback memories capture user preferences and corrections that should apply to future sessions
type: feedback
last_verified: 2026-01-01
priority: normal
triggers: [example, feedback, template, preferences, communication]
related: [user_profile.md]
index_entry:
  section: "⚙️ Procedural — Meta"
  order: 1
  label: "Example: concise output"
  hook: "Skip trailing summaries — user reads the diff"
---

# Concise output, no trailing summaries

User wants terse responses with no trailing "I have done X" summary blocks.

**Why:** the user reviews the diff directly; a written summary at the end is redundant
and consumes context.

**How to apply:** end of every response — stop after the final tool call or the
last informational sentence. If a status is necessary, one sentence max.

---

This is an example template memory. Remove or replace it with real procedural
feedback you've captured. The frontmatter structure is the canonical pattern:

- `type: feedback` — procedural / behavior rules
- `last_verified` — date the rule was confirmed
- `priority` — `critical | high | normal | low` for vector ranking
- `triggers` — keywords that boost vector search
- `index_entry` — placement in auto-generated MEMORY.md
