---
name: Example project memory — locked design decision
description: How project memories capture stable, code-verifiable facts about the project
type: project
last_verified: 2026-01-01
priority: high
triggers: [example, project, template, stable, decision]
assertions:
  - source: README.md
    contains: "claude-cortex"
index_entry:
  section: "🧠 Semantic — Design"
  order: 1
  label: "Example: locked decision"
  hook: "PA pool unified at 6, no separate move/attack pools"
---

# PA pool unified at 6

Both player and enemy units share a single 6-AP pool per turn. Costs:

- Move 1 tile: 1 AP
- Standard attack: 3 AP
- Face change: 1 AP
- Pass: 0 AP

**Why:** playtest feedback (week 12) — separating Move-AP from Attack-AP made every
turn feel like an inventory problem, not a tactical one. The unified 6 restored
fluid decision-making while keeping the "3 actions per turn" rhythm.

**How to apply:** any combat formula referencing AP must use this pool, not separate
move/attack pools. Refactor needed if you encounter `attack_pool` or `move_pool` in
source.

---

This is an example template memory. The `assertions:` block lets `verify.py` detect
drift — replace with assertions pointing at your real source files.

The `triggers: [...]` field boosts vector search relevance for these keywords.
