#!/usr/bin/env python3
"""verify.py — Test-driven memory: verify memory assertions against real code.

Each memory can declare in its YAML frontmatter:

    assertions:
      - source: src/path/file.py
        contains: 'EXPECTED_LITERAL = "value"'
      - source: design/gdd/foo.md
        regex: 'pa_pool\\s*=\\s*\\d+'
      - source: scripts/_paths.py
        grep: 'PROJECT_ID ='

The script reads all memories, executes assertions, reports:
- ✅ PASS: memory is up to date
- ❌ FAIL: memory diverges from code (fix needed)
- ⚠️ SKIP: source missing or assertion malformed

Paths resolved via `_paths.py` (PROJECT_ROOT auto-detected from cwd or parent).

Usage:
    python scripts/verify.py
    python scripts/verify.py --memory project_current_state.md
    python scripts/verify.py --fail-only
"""
import argparse
import re
import sys
from pathlib import Path

import yaml

from _paths import MEMORY_DIR, PROJECT_ROOT

# Force UTF-8 stdout on Windows (cp1252 default)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def parse_frontmatter(path: Path) -> dict | None:
    """Returns YAML frontmatter or None if absent."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    try:
        return yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError:
        return None


def _normalize_frontmatter(fm: dict) -> dict:
    """Promote fields from `metadata:` wrapping to top-level (Claude Code auto-memory compat).

    See rebuild_index.py for the full rationale. Without this, memories created via
    the Write tool (which auto-wraps fields under `metadata:`) would never have their
    assertions verified.
    """
    metadata = fm.get("metadata")
    if isinstance(metadata, dict):
        for key, value in metadata.items():
            fm.setdefault(key, value)
    return fm


def check_assertion(assertion: dict) -> tuple[str, str]:
    """Run one assertion, return (status, message).

    status: 'PASS' | 'FAIL' | 'SKIP'
    """
    source = assertion.get("source")
    if not source:
        return "SKIP", "assertion without 'source'"

    src_path = PROJECT_ROOT / source
    if not src_path.exists():
        return "SKIP", f"source missing: {source}"

    try:
        content = src_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return "SKIP", f"read failed: {e}"

    # 3 assertion types supported
    if "contains" in assertion:
        needle = assertion["contains"]
        if needle in content:
            return "PASS", f"'{needle[:50]}' found in {source}"
        return "FAIL", f"'{needle[:50]}' MISSING from {source}"

    if "regex" in assertion:
        pattern = assertion["regex"]
        try:
            if re.search(pattern, content):
                return "PASS", f"regex '{pattern[:50]}' matched in {source}"
            return "FAIL", f"regex '{pattern[:50]}' no match in {source}"
        except re.error as e:
            return "SKIP", f"invalid regex: {e}"

    if "grep" in assertion:
        line_needle = assertion["grep"]
        for line in content.splitlines():
            if line_needle in line:
                return "PASS", f"'{line_needle[:50]}' found (line grep) in {source}"
        return "FAIL", f"'{line_needle[:50]}' MISSING (line grep) from {source}"

    return "SKIP", "assertion without 'contains' / 'regex' / 'grep'"


def verify_memory(path: Path) -> list[tuple[str, str, str]]:
    """Returns list of (status, memory_name, message)."""
    fm = parse_frontmatter(path)
    if fm is None:
        return []
    fm = _normalize_frontmatter(fm)
    assertions = fm.get("assertions") or []
    if not assertions:
        return []
    results = []
    for a in assertions:
        status, msg = check_assertion(a)
        results.append((status, path.name, msg))
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--memory", help="Verify only this memory")
    parser.add_argument("--fail-only", action="store_true", help="Show FAIL only")
    args = parser.parse_args()

    if not MEMORY_DIR.exists():
        print(f"⚠️ MEMORY_DIR does not exist: {MEMORY_DIR}")
        sys.exit(1)

    if args.memory:
        paths = [MEMORY_DIR / args.memory]
    else:
        paths = sorted(MEMORY_DIR.glob("*.md"))

    total = 0
    failures = 0
    skips = 0
    all_results = []

    for path in paths:
        if path.name.startswith("_"):
            continue
        results = verify_memory(path)
        for status, name, msg in results:
            total += 1
            if status == "FAIL":
                failures += 1
            elif status == "SKIP":
                skips += 1
            all_results.append((status, name, msg))

    _ICONS = {"PASS": "✅", "FAIL": "❌", "SKIP": "⚠️"}

    for status, name, msg in all_results:
        if args.fail_only and status != "FAIL":
            continue
        icon = _ICONS.get(status, "?")
        print(f"{icon} [{name}] {msg}")

    print()
    print(f"── Assertions: {total}")
    print(f"   ✅ PASS: {total - failures - skips}")
    print(f"   ❌ FAIL: {failures}")
    print(f"   ⚠️ SKIP: {skips}")

    sys.exit(1 if failures > 0 else 0)


if __name__ == "__main__":
    main()
