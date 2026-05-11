"""_hook_runner.py — Central hook orchestrator for claude-cortex.

Each hook = function that reads JSON stdin and returns an exit code:
  0 = OK (advisory or no-op)
  1 = Warning (non-blocking)
  2 = Blocking (Claude Code refuses the tool use)

The shell wrappers in `hooks/*.sh` call `python _hook_runner.py <hook-name>`.
Pooled boilerplate (stdin parsing, _paths import, error handling) lives here.
"""
import json
import os
import sys
from pathlib import Path

# Add own dir to sys.path so we can import siblings (_safe_io, _paths, vector)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _safe_io import read_input_json, dump_for_claude  # noqa: E402


def _safe_paths():
    """Lazy import of _paths for fail-soft if cortex not set up."""
    try:
        from _paths import MEMORY_DIR, PROJECT_ROOT  # type: ignore
        return MEMORY_DIR, PROJECT_ROOT
    except ImportError:
        return None, None


# ─── memory-impact ─────────────────────────────────────────────────────────
def memory_impact(data: dict) -> int:
    """PostToolUse Edit|Write — lists memories that reference the modified file.

    Continuous encoding: rather than batch at end-of-session, flag impacted
    memories to update in the same response.
    """
    tool = data.get("toolName", "")
    if tool not in ("Edit", "Write"):
        return 0

    file_path = data.get("tool_input", {}).get("file_path", "")
    if not file_path:
        return 0

    MEMORY_DIR, PROJECT_ROOT = _safe_paths()
    if not MEMORY_DIR or not PROJECT_ROOT:
        return 0

    # Filter: don't flag modifs inside memory dir itself (recursive loop)
    abs_modified = Path(file_path).resolve()
    try:
        if MEMORY_DIR in abs_modified.parents or abs_modified == MEMORY_DIR:
            return 0
    except Exception:
        pass

    # Filter: skip .claude/hooks and scripts/ (infrastructure)
    norm = abs_modified.as_posix()
    if "/.claude/hooks/" in norm:
        return 0
    # Skip scripts dir (likely contains the cortex tooling itself)
    try:
        # Skip if it's inside the scripts/ subdir of project root
        rel_to_root = abs_modified.relative_to(PROJECT_ROOT).as_posix()
        if rel_to_root.startswith("scripts/cortex/") or rel_to_root.startswith("scripts/memory/"):
            return 0
    except ValueError:
        pass

    # Path relative to project for matching
    try:
        rel_path = abs_modified.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return 0

    # Variants to match: full path + basename
    needles = [rel_path]
    if "/" in rel_path:
        needles.append(Path(rel_path).name)

    matches = []
    for mem_path in sorted(MEMORY_DIR.glob("*.md")):
        if mem_path.name in ("MEMORY.md", "MEMORY_BACKLOG.md", "MEMORY_REFERENCES.md"):
            continue
        if mem_path.name.startswith("_"):
            continue
        try:
            content = mem_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for needle in needles:
            if needle in content:
                # Line context
                for line_no, line in enumerate(content.splitlines(), 1):
                    if needle in line:
                        snippet = line.strip()[:120]
                        matches.append((mem_path.name, f"L{line_no}: {snippet}"))
                        break
                break

    if not matches:
        return 0

    lines = [f"[memory-impact] File modified: {rel_path}", ""]
    lines.append(f"⚠️ {len(matches)} memory(ies) reference this file:")
    for memname, ctx in matches[:10]:
        lines.append(f"  • {memname} — {ctx}")
    if len(matches) > 10:
        lines.append(f"  • ... +{len(matches) - 10} more")
    lines.append("")
    lines.append("→ Continuous encoding mandatory: update these memories IN THE SAME RESPONSE.")
    lines.append("→ If the change makes an assertion obsolete, bump `last_verified` after fix.")

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": "\n".join(lines),
        }
    }
    print(dump_for_claude(output))
    return 0


# ─── memory-write-check ────────────────────────────────────────────────────
DOUBLON_THRESHOLD = 0.6


def _parse_memory_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter of a memory from raw content."""
    if not content.startswith("---"):
        return {}
    end = content.find("\n---\n", 4)
    if end == -1:
        return {}
    try:
        import yaml  # type: ignore
        return yaml.safe_load(content[4:end]) or {}
    except Exception:
        return {}


def memory_write_check(data: dict) -> int:
    """PreToolUse Write on memory/*.md: anti-duplicate (vector search) + supersession enforcement.

    Rules:
    - New memory + top-1 vector score ≥ 0.6 → BLOCK (suggests extending existing)
    - Existing memory + no `supersedes:` → WARNING (exit 1) — use Edit or add supersedes
    - Exception: if `supersedes:` present, skip anti-duplicate (intentional overwrite)
    """
    tool = data.get("toolName", "")
    if tool != "Write":
        return 0

    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    content = tool_input.get("content", "")
    if not file_path or not content:
        return 0

    MEMORY_DIR, _ = _safe_paths()
    if not MEMORY_DIR:
        return 0

    abs_path = Path(file_path).resolve()
    try:
        rel = abs_path.relative_to(MEMORY_DIR)
    except ValueError:
        return 0  # Not in memory dir

    if abs_path.suffix != ".md":
        return 0

    if rel.name in ("MEMORY.md", "MEMORY_BACKLOG.md", "MEMORY_REFERENCES.md"):
        return 0

    fm = _parse_memory_frontmatter(content)
    has_supersedes = bool(fm.get("supersedes"))
    file_exists = abs_path.exists()

    # Case 1: Write on existing memory without supersedes → warning
    if file_exists and not has_supersedes:
        print(f"[memory-write-check] ⚠️ Write overwriting existing memory without 'supersedes:': {rel.name}", file=sys.stderr)
        print(f"[memory-write-check] If this is a complete rewrite, add 'supersedes: <previous version>' to frontmatter.", file=sys.stderr)
        print(f"[memory-write-check] Otherwise use Edit for a targeted change. See MEMORY_PROTOCOL.md §Archiving.", file=sys.stderr)
        return 1

    # Case 2: new memory → check vector duplicate
    if not file_exists and not has_supersedes:
        # Build query from description + name + triggers
        nm = fm.get("name", "")
        desc = fm.get("description", "")
        triggers = fm.get("triggers") or []
        parts = []
        if nm:
            parts.append(nm)
        if desc:
            parts.append(desc[:200])
        if triggers and isinstance(triggers, list):
            parts.append(", ".join(str(t) for t in triggers[:5]))
        query = " ".join(parts).strip()
        if not query:
            return 0  # not enough info

        try:
            from vector import rank  # type: ignore
        except ImportError:
            return 0
        try:
            results = rank(query, k=3)
        except Exception:
            return 0

        if not results:
            return 0

        top = results[0]
        if top["final"] < DOUBLON_THRESHOLD:
            return 0

        # BLOCK
        msg_lines = [
            f"[memory-write-check] 🚫 BLOCK: new memory '{rel.name}' too similar to existing.",
            f"[memory-write-check]   → {top['file']} (score={top['final']:.2f} ≥ {DOUBLON_THRESHOLD})",
            f"[memory-write-check]   First line: {top['first_line']}",
            "",
            "[memory-write-check] Possible actions:",
            "[memory-write-check]   1) Edit on the existing memory (enrichment rather than duplicate)",
            f"[memory-write-check]   2) Add 'supersedes: {top['file']}' to frontmatter if this is an intentional rewrite",
            "[memory-write-check]   3) Adjust the description: so it differs semantically",
            "",
            "See MEMORY_PROTOCOL.md §Anti-duplicates.",
        ]
        for line in msg_lines:
            print(line, file=sys.stderr)
        return 2

    return 0


# ─── memory-frontmatter-validate ───────────────────────────────────────────
def _validate_memory_frontmatter(fm: dict) -> list[str]:
    """Validate memory frontmatter against recurring errors.

    Detected errors:
      1. Missing required fields (name, description, type)
      2. type outside {user, feedback, project, reference}
      3. triggers contains a datetime.date (unquoted YAML date → crashes vector.py)
      4. last_verified is datetime.date instead of string
      5. priority outside valid values
    """
    import datetime as _dt
    errors = []

    if not isinstance(fm, dict) or not fm:
        errors.append("frontmatter empty or non-dict")
        return errors

    # Required fields
    for k in ("name", "description", "type"):
        if not fm.get(k):
            errors.append(f"{k}: missing or empty")

    # Valid type
    valid_types = ("user", "feedback", "project", "reference")
    if fm.get("type") and fm["type"] not in valid_types:
        errors.append(f"type = {fm['type']!r} invalid. Allowed: {' | '.join(valid_types)}")

    # triggers — all strings (no datetime.date)
    triggers = fm.get("triggers")
    if triggers is not None:
        if not isinstance(triggers, list):
            errors.append(f"triggers: must be a list, not {type(triggers).__name__}")
        else:
            for i, t in enumerate(triggers):
                if isinstance(t, _dt.date):
                    errors.append(
                        f'triggers[{i}] = {t} parsed as datetime.date — quote it as "{t}" '
                        f'(otherwise TypeError in vector.py index)'
                    )
                elif not isinstance(t, str):
                    errors.append(f"triggers[{i}]: must be string, not {type(t).__name__}")

    # last_verified string
    lv = fm.get("last_verified")
    if lv is not None and not isinstance(lv, str):
        if isinstance(lv, _dt.date):
            errors.append(f'last_verified = {lv} parsed as datetime.date — quote it as "{lv}"')
        else:
            errors.append(f"last_verified: must be string, not {type(lv).__name__}")

    # Valid priority
    pr = fm.get("priority")
    if pr is not None:
        if not isinstance(pr, str) or pr not in ("low", "normal", "high", "critical"):
            errors.append(f"priority = {pr!r} invalid. Allowed: low | normal | high | critical")

    return errors


def memory_frontmatter_validate(data: dict) -> int:
    """PostToolUse Edit|Write on memory/*.md: validate frontmatter on disk.

    Covers the Edit case (which doesn't give full tool_input.content).
    Blocks via decision:block on error. Safety net after the write.
    """
    tool = data.get("toolName", "")
    if tool not in ("Edit", "Write"):
        return 0

    file_path = data.get("tool_input", {}).get("file_path", "")
    if not file_path:
        return 0

    MEMORY_DIR, _ = _safe_paths()
    if not MEMORY_DIR:
        return 0

    abs_path = Path(file_path).resolve()
    try:
        rel = abs_path.relative_to(MEMORY_DIR)
    except ValueError:
        return 0

    if abs_path.suffix != ".md":
        return 0
    if rel.name in ("MEMORY.md", "MEMORY_BACKLOG.md", "MEMORY_REFERENCES.md", "MEMORY_PROTOCOL.md"):
        return 0
    if rel.name.startswith("_"):
        return 0

    if not abs_path.exists():
        return 0

    try:
        content = abs_path.read_text(encoding="utf-8")
    except Exception:
        return 0

    fm = _parse_memory_frontmatter(content)
    if not fm:
        msg_lines = [
            "",
            f"⚠️ **Invalid memory frontmatter**: `{rel.name}`",
            "",
            "The YAML frontmatter is missing or unparseable. Likely causes:",
            "  - missing `---` delimiters at start/end",
            "  - broken indentation",
            "  - unescaped special character",
        ]
        output = {"decision": "block", "reason": "\n".join(msg_lines)}
        print(dump_for_claude(output))
        return 0

    errors = _validate_memory_frontmatter(fm)
    if not errors:
        return 0

    msg_lines = [
        "",
        f"⚠️ **Invalid frontmatter**: `{rel.name}`",
        "",
        "Detected errors:",
        "",
    ]
    for e in errors:
        msg_lines.append(f"  - {e}")
    msg_lines += [
        "",
        "**Consequences if uncorrected**:",
        "  - unquoted dates → `python scripts/vector.py index` crashes",
        "  - invalid `priority` → ignored in decay × priority ranking",
        "  - missing required fields → memory loses search properties",
        "",
        f"Fix the file `{file_path}` NOW before the next action.",
    ]
    output = {"decision": "block", "reason": "\n".join(msg_lines)}
    print(dump_for_claude(output))
    return 0


# ─── Dispatch ──────────────────────────────────────────────────────────────
HOOKS = {
    "memory-impact": memory_impact,
    "memory-write-check": memory_write_check,
    "memory-frontmatter-validate": memory_frontmatter_validate,
}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: _hook_runner.py <hook-name>", file=sys.stderr)
        print(f"Available hooks: {', '.join(HOOKS)}", file=sys.stderr)
        sys.exit(1)

    hook_name = sys.argv[1]
    if hook_name not in HOOKS:
        print(f"Unknown hook: {hook_name}", file=sys.stderr)
        print(f"Available hooks: {', '.join(HOOKS)}", file=sys.stderr)
        sys.exit(1)

    data = read_input_json()
    try:
        exit_code = HOOKS[hook_name](data)
    except Exception as e:
        # Hook silent on errors — never block tool execution
        print(f"[_hook_runner] {hook_name} exception: {e}", file=sys.stderr)
        sys.exit(0)
    sys.exit(exit_code)
