# claude-cortex

> **Local-first, drift-resistant memory system for Claude Code.** Markdown + BGE-M3 vector search + assertion verification. No vendor lock-in, no cloud round-trips, no schema drift.

<!-- Demo asset placeholder — render docs/demo/demo.cast to docs/demo/demo.svg
     via svg-term-cli (recommended) or the bundled docs/demo/cast_to_svg.py
     (stdlib-only fallback). See docs/demo/README.md for the recording workflow.
     Once rendered, replace this comment block with:
       ![claude-cortex demo](docs/demo/demo.svg)
-->


```
~/.claude/projects/<PROJECT_ID>/memory/
├── MEMORY.md              ← auto-generated index (rebuild_index.py)
├── MEMORY_PROTOCOL.md     ← usage rules
├── feedback_*.md          ← procedural memories (rules, conventions)
├── project_*.md           ← semantic memories (stable facts, decisions)
├── project_session_*.md   ← episodic memories (notable sessions)
├── reference_*.md         ← external references
└── _vector_index/         ← Chroma local store (BGE-M3 embeddings)
```

## Why not the official Cortex MCP plugin?

The official plugin works for many use cases — but in production sessions we've hit hard limits:

| Issue | Plugin | claude-cortex |
|---|---|---|
| **Output size** | Can dump 100k+ chars in a single tool result, eating the context window | Vector search returns top-N memories with scores, ~500 chars |
| **Schema stability** | Internal schema can change between versions | Plain markdown + YAML frontmatter, your files, you own them |
| **Multilingual quality** | English-biased | BGE-M3 native FR/ES/DE/100+ languages, ranked equally |
| **Anti-duplicates** | Implicit / advisory | **Enforced via hook** — Write blocked at vector score ≥ 0.6 |
| **Drift detection** | None | `verify.py` checks assertions against real source files |
| **Cost** | Tokens consumed per recall | Local, ~30 ms latency, zero token cost |
| **Auto-memory compat** | N/A | Transparently handles Claude Code's `metadata:` frontmatter wrapping (memories created via the Write tool work without extra steps — see [CHANGELOG](CHANGELOG.md)) |

This isn't a replacement for the MCP plugin in every case. It's the path you take when you've outgrown what plugin sessions can return inside a context window.

## Quick start (5 minutes)

```bash
# 1. Clone
git clone https://github.com/sharayras/claude-cortex.git ~/tools/claude-cortex

# 2. Bootstrap into your project
cd ~/your/claude-code/project
python ~/tools/claude-cortex/init.py

#    → Copies scripts/ → <project>/scripts/cortex/
#    → Copies hooks/ → <project>/.claude/hooks/
#    → Copies skills/ → <project>/.claude/skills/
#    → Creates ~/.claude/projects/<PROJECT_ID>/memory/
#    → Optional: pip install, hook registration, first index build

# 3. Test it
python scripts/cortex/note.py "We use Python 3.12 with type hints"
python scripts/cortex/vector.py search "python version" --k 3

# 4. In a Claude Code session
/sync-memory         # reindex + rebuild MEMORY.md + verify
/audit-memory        # monthly freshness check
/consolidate-memory  # end-of-session learnings extraction
/handoff             # close session with summary file
```

## Architecture

### Memory layer (markdown + YAML)

Each memory is a markdown file with a YAML frontmatter:

```markdown
---
name: PA pool is unified at 6
description: Player and enemy share a single 6-AP pool, no separate move/attack pools
type: project
last_verified: 2026-05-11
priority: high
triggers: [combat, action-points, pa, pool]
assertions:
  - source: design/registry/entities.yaml
    regex: 'pa_pool_default_player.*value:\s*6'
index_entry:
  section: "🧠 Semantic — Design"
  order: 10
  label: "PA pool unified"
  hook: "6 AP shared player+enemy, no separate pools"
---

The decision came from playtest feedback in week 12: separating Move-AP from
Attack-AP made every turn feel like an inventory problem, not a tactical one.
Unifying into a single 6-AP pool restored fluid decision-making.
```

Frontmatter types: `user`, `feedback`, `project`, `reference` (cognitive science: semantic / procedural / episodic).

### Vector search (BGE-M3 + Chroma)

BAAI/bge-m3 is a SOTA 2024 multilingual embedder (100+ languages). Ranks memories by **multiplicative scoring**:

```
final_score = bge_similarity × decay_factor × priority_multiplier

decay_factor    = 1 − 0.5 × min(days_since_verified / 180, 1)
priority_mult   = {critical: ×1.10, high: ×1.05, normal: ×1.00, low: ×0.95}
```

Multiplicative > additive: a low-quality match cannot be boosted past a high-quality one. ~30 ms local latency.

### Drift detection (verify.py)

Memories can declare verifiable assertions:

```yaml
assertions:
  - source: src/combat/calc.py
    contains: 'PA_POOL = 6'
  - source: design/balance.md
    regex: 'pa_pool\s*=\s*\d+'
```

`python scripts/verify.py --fail-only` reports any memory that no longer matches the source. Plug this into CI to catch drift before it lies to future sessions.

### Hooks (enforcement, not advisory)

Six hooks register in `.claude/settings.local.json` to enforce the protocol:

| Hook | Event | Effect |
|---|---|---|
| `session-start-reminder` | SessionStart | Injects protocol reminder + reading list |
| `session-start-verify` | SessionStart | Runs `verify.py --fail-only`, surfaces drift |
| `memory-protocol-reminder` | UserPromptSubmit | Reminds: vector search before grep, anti-duplicate before create |
| `skill-forced-eval` | UserPromptSubmit | Surfaces relevant memory skills based on prompt keywords |
| `memory-write-check` | PreToolUse Write | **BLOCKS** new memory if top-1 vector score ≥ 0.6 (suggests extending) |
| `memory-impact` | PostToolUse Edit\|Write | Flags memories that reference the modified file (continuous encoding) |
| `memory-frontmatter-validate` | PostToolUse Edit\|Write | Validates frontmatter schema (types, dates, triggers) |

### Auto-generated index (rebuild_index.py)

MEMORY.md is **never edited by hand**. It's regenerated from each memory's `index_entry:` field:

```yaml
index_entry:
  section: "🧠 Semantic — Design"
  order: 10                          # within-section ordering
  label: "PA pool unified"
  hook: "6 AP shared player+enemy"   # one-line summary
```

Layout (sections, prologue, epilogue, sub-files for backlog/references) is configured in `cortex_config.yaml` at the project root.

## Skills (Claude Code slash commands)

| Skill | Purpose |
|---|---|
| `/sync-memory` | Orchestrates verify + rebuild_index + vector reindex |
| `/audit-memory` | Monthly hygiene: freshness, duplicates, broken links, drift |
| `/consolidate-memory` | End-of-session sleep-phase: extracts learnings to durable memories |
| `/handoff` | Generates SESSION_HANDOFF.md + DETAIL for the next session |

All skills are markdown files installed to `.claude/skills/<name>/SKILL.md`.

## Configuration

`cortex_config.yaml` at the project root customizes MEMORY.md layout:

```yaml
sections:
  - "🧠 Semantic — Design"
  - "⚙️ Procedural — Workflows"
  - "📅 Episodic — Sessions"

subfiles:
  MEMORY_BACKLOG.md:
    title: "Backlog & stable context"
    sections: ["🎯 Validated designs", "🚧 Future work"]

prologue: |
  ## SESSION START — read in order
  1. ...

epilogue: |
  ## Archive procedure → see MEMORY_PROTOCOL.md
```

If absent, built-in defaults are used. Copy `cortex_config.yaml.example` to start.

## Environment overrides

| Var | Effect |
|---|---|
| `CORTEX_PROJECT_ID` | Override project ID (default: derived from cwd) |
| `CORTEX_MEMORY_DIR` | Override memory dir location |
| `CORTEX_INDEX_DIR` | Override vector index location |
| `CORTEX_CONFIG` | Override cortex_config.yaml path |

By default, the project ID is derived from the current working directory using the same normalization Claude Code uses (`/home/user/proj` → `-home-user-proj`).

## Benchmarks

Baseline on a 120-memory production codebase (2026-04-22, BGE-M3 + multiplicative scoring):

| Metric | Score |
|---|---|
| Top-1 recall | 86.7% |
| Top-3 recall | 93.3% |
| MRR | 0.900 |
| Median latency | ~30 ms (warm) |
| First-load latency | ~2 s (cold model) |
| Index size | ~80 MB per 100 memories |

## Requirements

- Python 3.10+
- ~1 GB disk for BGE-M3 model (one-time download on first vector index build)
- Claude Code 2.0+ (for skill/hook compatibility)

Tested on Windows 11 (PowerShell + Bash via Git for Windows). Linux/macOS should work; please file an issue if you hit platform-specific problems.

## Comparison to other memory systems

- **claude-mem** — SQLite-backed, simpler scope; no vector search, no drift detection
- **mem0** — commercial / hosted; great UX but vendor lock-in
- **Letta / MemGPT** — heavier framework; aimed at agents, not Claude Code workflow
- **Official Cortex MCP** — works well until you hit the context-window output limits

claude-cortex sits at the intersection: pure files (no DB), local-first, BGE-M3 quality, hook-enforced protocol, fits the Claude Code skill model.

## Project status

Validated on two independent production codebases (Discord bot + game studio workflow). 0.x version — API may shift before 1.0 based on early adopter feedback.

Bug reports and PRs welcome at https://github.com/sharayras/claude-cortex/issues.

## Contributing

PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for dev setup (5 min), coding conventions, testing patterns, and the PR process. Good first issues are tagged [`good first issue`](https://github.com/sharayras/claude-cortex/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).

For security vulnerabilities, please use GitHub's private security advisory feature (Security tab → Report a vulnerability) instead of opening a public issue.

## License

MIT — see `LICENSE`.
