#!/usr/bin/env python3
"""note.py — Quick-add memory command. Fast capture without frontmatter ceremony.

Usage:
    python scripts/note.py "The memory-impact hook flags memories affected by each edit"
    python scripts/note.py --type project "Tactical Combat = Hero + 1 ally vs N enemies"
    python scripts/note.py --section "⚙️ Procedural — Meta" --label "Hook flag rule" "..."

Behavior:
- Auto-generates slug from first 8 words
- Creates `feedback_<slug>.md` (default) or `<type>_<slug>.md` if --type X
- Auto-extracts triggers from text keywords (top tokens > 3 chars)
- Minimal frontmatter (name, description, type, last_verified, triggers)
- Body = provided text
- **Anti-duplicate mandatory**: vector search top-3 before create. Score > 0.6 → refuse +
  suggests extending existing memory.

The created file is editable afterward to enrich (index_entry, related, assertions, etc.).
"""
import argparse
import datetime
import os
import re
import sys
from pathlib import Path

from _paths import MEMORY_DIR

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# Minimal multilingual stop-words (FR + EN, just the most frequent)
STOPWORDS = {
    # FR
    "le", "la", "les", "un", "une", "des", "du", "de", "et", "ou", "que", "qui", "dans",
    "pour", "par", "avec", "sur", "sous", "en", "au", "aux", "se", "ce", "cette", "ces",
    "son", "sa", "ses", "il", "elle", "ils", "elles", "on", "nous", "vous", "est", "sont",
    "été", "être", "avoir", "fait", "faire", "tout", "tous", "toute", "toutes",
    "plus", "moins", "très", "bien", "mais", "donc", "aussi", "déjà", "encore",
    # EN
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "at", "for", "with", "by",
    "from", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "should", "can", "could", "may", "might",
    "this", "that", "these", "those", "it", "its", "their",
}


def slugify(text: str, max_words: int = 8, max_chars: int = 50) -> str:
    """Generate kebab-case slug from first words."""
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    words = cleaned.split()[:max_words]
    slug = "-".join(words)
    # ASCII-safe (filenames + Git portability)
    slug = "".join(c for c in slug if c.isascii())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:max_chars] or "note"


def extract_triggers(text: str, max_triggers: int = 5) -> list[str]:
    """Extract salient keywords (top tokens excluding stop-words, > 3 chars)."""
    tokens = re.findall(r"[a-zA-Zà-ÿ_-]{4,}", text.lower())
    freq: dict[str, int] = {}
    for t in tokens:
        if t in STOPWORDS:
            continue
        freq[t] = freq.get(t, 0) + 1
    sorted_tokens = sorted(freq.items(), key=lambda x: -x[1])
    return [t for t, _ in sorted_tokens[:max_triggers]]


def anti_doublon_check(text: str, threshold: float = 0.6) -> tuple[bool, str]:
    """Vector search top-3 for anti-duplicate. Returns (is_duplicate, message)."""
    try:
        # Lazy import to avoid BGE-M3 cost if check skipped
        from vector import rank  # type: ignore
    except ImportError:
        return False, "(vector.py not importable — skip anti-duplicate check)"

    try:
        results = rank(text, k=3)
    except Exception as e:
        return False, f"(vector.rank failed: {e} — skip anti-duplicate check)"

    if not results:
        return False, "(empty index or no results — OK to create)"

    top = results[0]
    if top["final"] > threshold:
        msg = (
            f"⚠️ Potential duplicate detected ({top['file']}, score={top['final']:.2f} > {threshold})\n"
            f"   First line: {top['first_line']}\n"
            f"   → Consider EXTENDING this memory rather than creating a duplicate.\n"
            f"   → If you insist on creating, add --force."
        )
        return True, msg

    return False, f"OK — top result {top['file']} score={top['final']:.2f} (< {threshold})"


def make_frontmatter(name: str, description: str, mem_type: str, triggers: list[str]) -> str:
    """Generate YAML frontmatter (minimal default — for quick capture)."""
    today = datetime.date.today().isoformat()
    origin = os.environ.get("CLAUDE_SESSION_ID", "")

    lines = [
        "---",
        f"name: {name}",
        f"description: {description}",
        f"type: {mem_type}",
        f"last_verified: {today}",
        f"triggers: [{', '.join(triggers)}]",
    ]
    if origin:
        lines.append(f"originSessionId: {origin}")
    lines.append("---")
    return "\n".join(lines)


def make_template_frontmatter(name: str, description: str, mem_type: str, triggers: list[str]) -> str:
    """Generate enriched YAML frontmatter (skeleton with placeholders for power users).

    Pre-fills priority, related, index_entry, and assertions stubs per memory type so
    the user only has to fill in the specifics rather than recall the schema. Targets
    the same flat top-level layout that rebuild_index/verify/vector consume directly
    (no `metadata:` wrapping like Claude Code's auto-memory write would create).

    Per type:
    - feedback : priority + triggers + related + index_entry stub
    - project  : everything in feedback + last_verified (today) + 1 assertion stub
    - reference: priority + triggers + related + index_entry stub (no assertions)

    Implementation note : we still emit raw text (not yaml.safe_dump) because the
    existing parser tolerates exact line shapes and the templates need readable
    placeholders (PLACEHOLDER_*) that yaml.safe_dump would quote awkwardly.
    """
    today = datetime.date.today().isoformat()
    origin = os.environ.get("CLAUDE_SESSION_ID", "")

    triggers_str = ", ".join(triggers) if triggers else "PLACEHOLDER_TRIGGER"

    lines = [
        "---",
        f"name: {name}",
        f"description: {description}",
        f"type: {mem_type}",
    ]
    if mem_type == "project":
        lines.append(f"last_verified: {today}")
    lines.extend([
        "priority: normal",
        f"triggers: [{triggers_str}]",
        "related: []",
        "index_entry:",
        "  section: \"PLACEHOLDER_SECTION — fill in (must match a section in cortex_config.yaml)\"",
        "  order: 100",
        f"  label: \"{name}\"",
        f"  hook: \"{description[:100]}\"",
    ])
    if mem_type == "project":
        lines.extend([
            "assertions:",
            "  - source: PLACEHOLDER_PATH/file.md",
            "    contains: \"PLACEHOLDER_NEEDLE\"",
        ])
    if origin:
        lines.append(f"originSessionId: {origin}")
    lines.append("---")
    return "\n".join(lines)


def make_template_body(name: str, text: str, mem_type: str) -> str:
    """Generate a structured body stub per memory type (feedback/project: Why+How; reference: Source+When)."""
    if mem_type == "reference":
        return (
            f"# {name}\n\n"
            f"{text}\n\n"
            "## Source\n\n"
            "_TODO: URL, path, or citation for the external resource._\n\n"
            "## When relevant\n\n"
            "_TODO: what queries / situations should surface this reference?_\n"
        )
    # feedback + project share the Why/How structure (per MEMORY_PROTOCOL.md §Structure du corps)
    return (
        f"# {name}\n\n"
        f"{text}\n\n"
        "## Why\n\n"
        "_TODO: the incident, constraint, or preference behind this rule/fact._\n\n"
        "## How to apply\n\n"
        "_TODO: when this kicks in (concrete triggers, scope, anti-patterns)._\n"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("text", nargs="+", help="Memory content (free-form text)")
    parser.add_argument("--type", choices=["feedback", "project", "reference", "user"], default="feedback",
                        help="Memory type (default: feedback)")
    parser.add_argument("--from-template", choices=["feedback", "project", "reference"], default=None,
                        dest="from_template",
                        help="Generate enriched skeleton with priority + index_entry + related + assertions stubs "
                             "+ structured body (Why/How for feedback/project, Source/When for reference). "
                             "Implies --type if not set explicitly.")
    parser.add_argument("--name", default=None, help="Explicit name (default: first sentence)")
    parser.add_argument("--description", default=None, help="Explicit description (default: truncated text)")
    parser.add_argument("--slug", default=None, help="Explicit slug for filename")
    parser.add_argument("--force", action="store_true", help="Skip anti-duplicate check")
    parser.add_argument("--dry-run", action="store_true", help="Show content without writing")
    args = parser.parse_args()

    text = " ".join(args.text).strip()
    if not text:
        print("ERROR: empty text", file=sys.stderr)
        sys.exit(1)

    # --from-template implies --type if not explicitly set
    if args.from_template:
        # If user passed --type explicitly AND --from-template with different value, prefer --from-template
        # (the template choice carries more intent than the default --type)
        mem_type = args.from_template
    else:
        mem_type = args.type

    # Frontmatter fields
    if args.name:
        name = args.name
    else:
        first_sentence = re.split(r"[.!?\n]", text)[0].strip()
        name = first_sentence[:80] if first_sentence else text[:80]

    description = args.description or (text[:150] + ("..." if len(text) > 150 else ""))

    # Slug
    slug = args.slug or slugify(name)
    filename = f"{mem_type}_{slug}.md"

    target_path = MEMORY_DIR / filename
    if target_path.exists():
        print(f"⚠️ File already exists: {filename}")
        print("   Use --slug <other-slug> or edit the existing file.")
        sys.exit(1)

    # Triggers
    triggers = extract_triggers(text)
    if not triggers:
        triggers = ["note", mem_type]

    # Anti-duplicate check
    if not args.force:
        is_dup, msg = anti_doublon_check(text)
        print(msg)
        if is_dup:
            sys.exit(2)

    # Compose
    if args.from_template:
        fm = make_template_frontmatter(name, description, mem_type, triggers)
        body = make_template_body(name, text, mem_type)
        content = f"{fm}\n\n{body}"
    else:
        fm = make_frontmatter(name, description, mem_type, triggers)
        content = f"{fm}\n\n{text}\n"

    if args.dry_run:
        print()
        print(f"=== Dry-run: {filename} ===")
        print(content)
        return

    # Write
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(content, encoding="utf-8")
    print(f"✅ Memory created: {target_path}")
    print(f"   Type    : {mem_type}")
    print(f"   Triggers: {triggers}")
    if args.from_template:
        print(f"   Template: enriched skeleton ({mem_type})")
    print()
    print("⏭️ Suggested next steps:")
    if args.from_template:
        print(f"   1. Edit the file: replace PLACEHOLDER_* values, fill Why/How sections")
        print(f"   2. Run `python scripts/rebuild_index.py --write` (index_entry already present)")
    else:
        print(f"   1. Edit the file to enrich (index_entry, related, assertions)")
        print(f"   2. Run `python scripts/rebuild_index.py --write` if index_entry added")
    print(f"   3. Run `python scripts/vector.py index` to reindex")
    print(f"   4. (Or just /sync-memory to orchestrate 2+3)")


if __name__ == "__main__":
    main()
