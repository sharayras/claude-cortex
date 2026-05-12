# Contributing to claude-cortex

Thanks for considering a contribution. This document covers the dev setup, conventions, and PR process. The goal is for a first-time contributor to ship a small fix in under 30 minutes.

## Dev setup (5 min)

```bash
# 1. Fork on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/claude-cortex.git
cd claude-cortex

# 2. Install dev dependencies (no BGE-M3 model — tests run without it)
pip install -r requirements.txt
pip install pytest

# 3. Run the test suite (~0.5s)
python -m pytest tests/

# 4. Verify your install works on a real cortex
python scripts/_paths.py     # prints resolved paths
```

Optional, only for end-to-end vector search testing :

```bash
pip install sentence-transformers chromadb     # ~1 GB model download on first run
python scripts/vector.py search "test query"
```

## Coding conventions

- **Python 3.10+** — match types use `|`, dict literal types use lowercase
- **Type hints on public functions** — `def foo(x: str) -> int:` not bare `def foo(x):`
- **Docstrings on public functions** — one-line minimum, longer if behavior is non-obvious
- **No project-specific paths** — always use `_paths.py` (`MEMORY_DIR`, `INDEX_DIR`, `PROJECT_ROOT`); never hardcode `~/.claude/...` or `E:/...`
- **`_normalize_*` helper pattern** — when a parser needs to handle multiple input shapes (like the `metadata:` wrapping fix in [#fix](https://github.com/sharayras/claude-cortex/commit/4d0ff9b)), add a private `_normalize_*` function rather than scattering shape checks
- **No silent failure** — if a parse / verify / index step encounters a malformed input, log a structured `WARN: <file> — <reason>` to stderr, never `pass` silently
- **UTF-8 everywhere** — `read_text(encoding="utf-8")`, `write_text(..., encoding="utf-8")`, `sys.stdout.reconfigure(encoding="utf-8")` at script start (Windows-default cp1252 breaks accented characters)

## Testing

All tests live in `tests/` and use shared fixtures from `conftest.py`:

- `isolated_cortex` — provides a temp `MEMORY_DIR` + `INDEX_DIR` + `PROJECT_ROOT`, env-vars set, modules reloaded
- `make_memory(name, frontmatter, body)` — factory for writing a memory file with given YAML frontmatter

Example test :

```python
def test_my_feature(isolated_cortex, make_memory):
    make_memory("project_a.md", {
        "name": "A", "description": "...", "type": "project",
        "index_entry": {"section": "🧠 Semantic — Design", "order": 10, "label": "A", "hook": "h"},
    })

    import rebuild_index
    importlib.reload(rebuild_index)

    entries = rebuild_index.collect_entries()
    assert "A" in str(entries)
```

**Test rules** :
- Each test must pass in isolation (no test ordering dependency)
- No network access in tests (use mocks if testing HTTP-touching code)
- BGE-M3 model load is slow (~3s) — skip it via importlib reload + the `isolated_cortex` fixture's env vars unless the test specifically targets vector behavior
- New features need at least one test covering the happy path + one edge case

CI runs the same `python -m pytest tests/` on Ubuntu / Windows / macOS × Python 3.10 / 3.11 / 3.12 (9 jobs). If your tests pass locally on one platform but you're unsure about the others, push to your fork and watch the matrix.

## PR process

1. **Branch off `main`** — `git checkout -b feat/my-thing` or `fix/my-thing`
2. **Run tests locally** — `python -m pytest tests/` should be green before pushing
3. **Add a CHANGELOG entry** under `## [Unreleased]` in `CHANGELOG.md`
   - Use sections : `### Added`, `### Changed`, `### Fixed`, `### Deprecated`, `### Removed`, `### Security`
   - Reference your PR number once it exists
4. **Update docs if user-facing** — README, MEMORY_PROTOCOL.md, or both
5. **Open the PR** — link the issue with `Closes #N` in the description
6. **Wait for CI green** + maintainer review

Small PRs are easier to review and ship. If you're tackling a large feature (one of the multi-hour issues), feel free to open a draft PR early and ask for direction.

## Commit message style

The project uses conventional-commit-ish prefixes :

- `feat(scope): ...` — new user-facing capability
- `fix(scope): ...` — bug fix
- `docs: ...` — documentation only
- `test: ...` — test changes only
- `refactor(scope): ...` — internal change without behavior shift
- `chore: ...` — tooling / CI / dependencies

Body is free-form. For non-trivial commits, explain *why* the change exists (the *what* is in the diff). Reference the issue/PR.

## Security issues

Please **don't** open public issues for security vulnerabilities. Use GitHub's private security advisory feature (Security tab → Report a vulnerability) or email the maintainer.

## Release process (maintainer-only)

1. Update `CHANGELOG.md` — move `[Unreleased]` items into a new `[X.Y.Z]` section with today's date
2. Tag : `git tag -a vX.Y.Z -m "Release X.Y.Z"` then `git push origin vX.Y.Z`
3. Create a GitHub release from the tag, paste the CHANGELOG section into the release notes

That's it. Welcome aboard 👋
