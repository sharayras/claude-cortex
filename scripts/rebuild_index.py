#!/usr/bin/env python3
"""rebuild_index.py — Regenerate MEMORY.md from memory frontmatters.

Each memory declares its index placement via:

    index_entry:
      section: "🧠 Semantic — Design"
      order: 10                      # order within section (optional)
      label: "Combat DNA"            # displayed label (default: name)
      hook: "Hero + 1 ally · PA unified · 4-dir facing"

Memories without `index_entry` are NOT in the index (useful for archives).

Layout (sections, prologue, epilogue, sub-files) is loaded from
`cortex_config.yaml` — search order:
  1. $CORTEX_CONFIG (explicit env var)
  2. <project_root>/cortex_config.yaml
  3. <memory_dir>/cortex_config.yaml
  4. Built-in default (this file)

Paths resolved via `_paths.py` — project-agnostic.

Usage:
    python scripts/rebuild_index.py               # dry-run (stdout)
    python scripts/rebuild_index.py --write       # overwrite MEMORY.md
    python scripts/rebuild_index.py --diff        # diff vs current
"""
import argparse
import difflib
import sys
from pathlib import Path

import yaml

from _paths import MEMORY_DIR, CONFIG_PATH

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


INDEX_PATH = MEMORY_DIR / "MEMORY.md"


# ─── Built-in default config (used if cortex_config.yaml is missing) ────────
DEFAULT_CONFIG = {
    "sections": [
        "🧠 Semantic — Project state",
        "🧠 Semantic — Design",
        "🧠 Semantic — Architecture",
        "⚙️ Procedural — Workflows",
        "⚙️ Procedural — Meta",
        "⚙️ Procedural — Code quality",
        "📅 Episodic — Sessions",
        "🎯 Validated designs",
        "🚧 Future work",
        "📂 Stable project context",
        "🔗 External references",
    ],
    "subfiles": {
        "MEMORY_BACKLOG.md": {
            "title": "Backlog & stable context",
            "description": "validated designs not yet implemented, future work, stable project context",
            "sections": [
                "🎯 Validated designs",
                "🚧 Future work",
                "📂 Stable project context",
            ],
        },
        "MEMORY_REFERENCES.md": {
            "title": "External references",
            "description": "systems/resources outside the project (frameworks, vendor APIs, etc.)",
            "sections": ["🔗 External references"],
        },
    },
    "category_suffix": {
        "🧠 Semantic": "stable project facts",
        "⚙️ Procedural": "workflows and rules",
        "📅 Episodic": "incidents and notable sessions",
        "🎯 Validated designs": "not yet implemented (high priority)",
        "🚧 Future work": "backlog ideation",
        "📂 Stable project context": None,
        "🔗 External references": "systems outside the project",
    },
    "prologue": (
        "## 🚨 SESSION START — read in order\n\n"
        "1. **<your project state file>** — current session state\n"
        "2. **<entry-point design docs>** — vision + roadmap\n"
        "3. **<canonical fact registry>** — cross-system facts\n"
        "4. **[User profile](user_profile.md)** + project overviews\n\n"
        "Out-of-sync code ↔ memory → **[MEMORY_PROTOCOL.md](MEMORY_PROTOCOL.md)**.\n\n"
        "## 🔍 FINDING A MEMORY (BGE-M3, ~30ms)\n\n"
        "```bash\n"
        "python scripts/vector.py search \"<topic>\" --k 3\n"
        "```\n\n"
        "Score < 0.4 → fall back to grep.\n\n"
        "## 🛠️ MEMORY SKILLS (`/name`)\n\n"
        "- `/sync-memory` reindexes BGE-M3 + rebuild MEMORY.md + verify\n"
        "- `/audit-memory` monthly freshness audit\n"
        "- `/consolidate-memory` end-of-session learnings extraction\n"
        "- `/handoff` close session with summary file\n\n"
        "## ⚙️ REFLEXES\n\n"
        "- Topic mentioned → `vector.py` BEFORE grep\n"
        "- Memory change or project fact → `/sync-memory` right away\n"
        "- Doubt about info → `verify.py --fail-only`\n"
        "- Anti-duplicate MANDATORY before creating memory: `vector.py search \"<topic>\"`\n\n"
    ),
    "epilogue": (
        "\n---\n\n"
        "## 🗑️ ARCHIVE (`memory/_archive/`, out of index)\n\n"
        "Obsolete memories are moved to `_archive/` with date prefix `YYYY-MM-DD_`. "
        "See [MEMORY_PROTOCOL.md](MEMORY_PROTOCOL.md) §Archiving for the procedure.\n"
    ),
}


def load_config() -> dict:
    """Load cortex_config.yaml or fall back to DEFAULT_CONFIG."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            print(f"WARN: {CONFIG_PATH} — YAML error: {e}", file=sys.stderr)
            return DEFAULT_CONFIG
        # Merge with defaults so missing keys fall through
        merged = dict(DEFAULT_CONFIG)
        for k, v in loaded.items():
            merged[k] = v
        return merged
    return DEFAULT_CONFIG


def section_to_subfile_map(config: dict) -> dict[str, str]:
    """Reverse-map: section name → subfile filename."""
    out = {}
    for subfile_name, subfile_def in config.get("subfiles", {}).items():
        for section in subfile_def.get("sections", []):
            out[section] = subfile_name
    return out


def parse_frontmatter(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    try:
        return yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError as e:
        print(f"WARN: {path.name} — YAML error: {e}", file=sys.stderr)
        return None


def _normalize_frontmatter(fm: dict) -> dict:
    """Promote fields from `metadata:` wrapping to top-level (Claude Code auto-memory compat).

    Claude Code's built-in auto-memory feature transforms memory frontmatters created
    via the Write tool, wrapping all fields except `name`/`description` under
    `metadata:` (and auto-injecting `node_type`, `originSessionId`). Most readers
    expect top-level fields. This helper merges `metadata.*` fields into the
    top-level dict (top-level wins on collision, preserving user intent if both exist).

    Without this normalization, memories created via Write would silently fail to
    appear in the rebuilt index — a class of bug that's hard to debug because the
    YAML parses correctly but downstream consumers look at the wrong path.
    """
    metadata = fm.get("metadata")
    if isinstance(metadata, dict):
        for key, value in metadata.items():
            fm.setdefault(key, value)
    return fm


def collect_entries() -> dict[str, list[dict]]:
    """Group memories by index section."""
    by_section: dict[str, list[dict]] = {}
    for path in sorted(MEMORY_DIR.glob("*.md")):
        if path.name in ("MEMORY.md", "MEMORY_PROTOCOL.md"):
            continue
        fm = parse_frontmatter(path)
        if fm is None:
            continue
        fm = _normalize_frontmatter(fm)
        entry = fm.get("index_entry") or {}
        section = entry.get("section")
        if not section:
            continue  # memory without index_entry = out of index (archive/internal)
        by_section.setdefault(section, []).append({
            "file": path.name,
            "label": entry.get("label") or fm.get("name") or path.stem,
            "hook": entry.get("hook") or fm.get("description") or "",
            "order": entry.get("order", 100),
        })
    for sect in by_section.values():
        sect.sort(key=lambda e: (e["order"], e["label"]))
    return by_section


def _render_section_block(
    out: list[str],
    section: str,
    entries: list[dict],
    last_category: str | None,
    category_suffix: dict[str, str | None],
    *,
    first_overall: bool = False,
) -> str | None:
    """Append category header + sub-section + entries to `out`."""
    category = section.split(" — ")[0] if " — " in section else section

    if category != last_category:
        suffix = category_suffix.get(category)
        if first_overall and last_category is None:
            out.append("---\n\n")
        else:
            out.append("\n---\n\n")
        if suffix:
            out.append(f"## {category} — {suffix}\n")
        else:
            out.append(f"## {category}\n")
        last_category = category

    subsection_label = section.split(" — ", 1)[1] if " — " in section else None
    if subsection_label:
        out.append(f"\n### {subsection_label}\n")

    for entry in entries:
        line = f"- [{entry['label']}]({entry['file']})"
        if entry["hook"]:
            line += f" — {entry['hook']}"
        out.append(line + "\n")

    return last_category


def render_main(by_section: dict[str, list[dict]], config: dict) -> str:
    """Generate MEMORY.md content."""
    out = [config.get("prologue", "")]
    category_suffix = config.get("category_suffix", {})
    section_order = config.get("sections", [])
    section_to_subfile = section_to_subfile_map(config)

    last_category: str | None = None
    first_section = True
    for section in section_order:
        if section not in by_section:
            continue
        if section in section_to_subfile:
            continue  # delocate to sub-file

        last_category = _render_section_block(
            out,
            section,
            by_section[section],
            last_category,
            category_suffix,
            first_overall=first_section,
        )
        first_section = False

    # Sub-index block
    referenced_subfiles: list[str] = []
    seen: set[str] = set()
    for section in section_order:
        subfile = section_to_subfile.get(section)
        if subfile and subfile not in seen and section in by_section:
            referenced_subfiles.append(subfile)
            seen.add(subfile)

    if referenced_subfiles:
        out.append("\n---\n\n## 📚 Sub-index\n")
        for subfile in referenced_subfiles:
            subfile_def = config.get("subfiles", {}).get(subfile, {})
            title = subfile_def.get("title", subfile)
            desc = subfile_def.get("description", "")
            line = f"- [{title}]({subfile})"
            if desc:
                line += f" — {desc}"
            out.append(line + "\n")

    out.append(config.get("epilogue", ""))
    return "".join(out)


def render_subfile(subfile_name: str, by_section: dict[str, list[dict]], config: dict) -> str:
    """Generate a sub-file's content."""
    subfile_def = config.get("subfiles", {}).get(subfile_name, {})
    title = subfile_def.get("title", subfile_name)
    out = [f"# {title}\n\n"]
    category_suffix = config.get("category_suffix", {})
    section_order = config.get("sections", [])
    section_to_subfile = section_to_subfile_map(config)

    last_category: str | None = None
    first_section = True
    for section in section_order:
        if section_to_subfile.get(section) != subfile_name:
            continue
        if section not in by_section:
            continue

        last_category = _render_section_block(
            out,
            section,
            by_section[section],
            last_category,
            category_suffix,
            first_overall=first_section,
        )
        first_section = False

    return "".join(out)


def render(by_section: dict[str, list[dict]], config: dict) -> str:
    """Alias for render_main() (compat with --diff)."""
    return render_main(by_section, config)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Write MEMORY.md (default: dry-run)")
    parser.add_argument("--diff", action="store_true", help="Show diff with current file")
    args = parser.parse_args()

    config = load_config()
    entries = collect_entries()
    content = render(entries, config)

    if args.diff:
        if not INDEX_PATH.exists():
            print("INDEX_PATH does not exist — no diff possible. Run --write first.")
            return
        current = INDEX_PATH.read_text(encoding="utf-8")
        diff = difflib.unified_diff(
            current.splitlines(keepends=True),
            content.splitlines(keepends=True),
            fromfile="current/MEMORY.md",
            tofile="rebuilt/MEMORY.md",
        )
        diff_text = "".join(diff)
        if diff_text:
            print(diff_text)
        else:
            print("No diff.")
        return

    if args.write:
        INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        INDEX_PATH.write_text(content, encoding="utf-8")
        print(f"✅ MEMORY.md rewritten ({len(content.splitlines())} lines)")
        total_entries = sum(len(v) for v in entries.values())
        print(f"   {total_entries} entries across {len(entries)} sections")

        # Write sub-files
        section_to_subfile = section_to_subfile_map(config)
        written_subfiles: set[str] = set()
        for section in config.get("sections", []):
            subfile_name = section_to_subfile.get(section)
            if subfile_name and subfile_name not in written_subfiles and section in entries:
                written_subfiles.add(subfile_name)
                subfile_path = MEMORY_DIR / subfile_name
                subfile_content = render_subfile(subfile_name, entries, config)
                subfile_path.write_text(subfile_content, encoding="utf-8")
                print(f"✅ {subfile_name} rewritten ({len(subfile_content.splitlines())} lines)")
    else:
        print(content)


if __name__ == "__main__":
    main()
