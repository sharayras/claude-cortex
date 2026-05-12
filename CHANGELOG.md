# Changelog

All notable changes to claude-cortex are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **Frontmatter parsers now transparently handle Claude Code's auto-memory `metadata:` wrapping.**
  When a memory file is created via Claude Code's `Write` tool, the built-in auto-memory
  feature wraps all fields except `name`/`description` under a `metadata:` key (and
  auto-injects `node_type` + `originSessionId`). Previously, `rebuild_index.py`,
  `verify.py`, and `vector.py` read fields from the top level only and silently failed
  on wrapped memories — they parsed the YAML correctly but downstream consumers found
  empty fields:
  - `rebuild_index.py` → memory absent from `MEMORY.md` (no `index_entry` at top)
  - `verify.py` → assertions skipped silently
  - `vector.py` → indexed with empty `triggers`/`type`/`priority`, ranked poorly
  All three parsers now apply a `_normalize_frontmatter()` helper that promotes
  `metadata.*` fields to the top level (top-level wins on collision, preserving user
  intent if both schemas coexist). Two new tests in `test_rebuild_index.py` cover the
  wrapped-memory path and the top-level-wins-collision case.
  Discovered while consolidating Project Hope memories (2026-05-12) — 2 memories
  created via `Write` were silently absent from the rebuilt index.

## [0.1.0] — 2026-05-11

### Added
- Initial public release of claude-cortex extracted from the Aeldoria bot project.
- Core scripts: `vector.py` (BGE-M3 + Chroma local search, ~30 ms), `verify.py`
  (assertion drift detection vs source files), `rebuild_index.py` (auto-generated
  `MEMORY.md` index from frontmatter `index_entry:` declarations), `note.py` (rapid
  memory creation with anti-duplicate enforcement via vector search).
- Path resolution via `_paths.py` — env-driven (`CORTEX_PROJECT_ID`,
  `CORTEX_MEMORY_DIR`, `CORTEX_INDEX_DIR`) with auto-detection fallback matching
  Claude Code's project ID convention.
- Hooks: `memory-write-check.sh` (pre-Write anti-duplicate enforcement), Claude
  Code skill `/sync-memory` (orchestrates verify + rebuild_index + vector reindex).
- `init.py` setup script for new projects: creates memory dir, installs Python deps,
  generates skeleton `MEMORY_PROTOCOL.md`, runs first vector index build.
- Configuration: `cortex_config.yaml` for `rebuild_index.py` section layout (vs
  hardcoded), placeholder `{{CORTEX_SCRIPTS_DIR}}` substitution in hooks/skills via
  `init.py`.
- Documentation: comprehensive `README.md` (architecture + quick-start + comparison
  vs Cortex MCP plugin) and `MEMORY_PROTOCOL.md` (memory types, frontmatter schema,
  anti-pattern guide).
- Tests: 27 pytest tests in `tests/` (vector search, verify, rebuild_index, note,
  hook_runner, paths) — runs in 0.36 s without BGE-M3 model load for fast CI.
- CI: GitHub Actions matrix Ubuntu / Windows / macOS × Python 3.10 / 3.11 / 3.12
  (9 jobs).
- License: MIT.

[Unreleased]: https://github.com/sharayras/claude-cortex/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/sharayras/claude-cortex/releases/tag/v0.1.0
