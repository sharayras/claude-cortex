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
    """Generate YAML frontmatter."""
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


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("text", nargs="+", help="Memory content (free-form text)")
    parser.add_argument("--type", choices=["feedback", "project", "reference", "user"], default="feedback",
                        help="Memory type (default: feedback)")
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

    # Frontmatter fields
    if args.name:
        name = args.name
    else:
        first_sentence = re.split(r"[.!?\n]", text)[0].strip()
        name = first_sentence[:80] if first_sentence else text[:80]

    description = args.description or (text[:150] + ("..." if len(text) > 150 else ""))

    # Slug
    slug = args.slug or slugify(name)
    filename = f"{args.type}_{slug}.md"

    target_path = MEMORY_DIR / filename
    if target_path.exists():
        print(f"⚠️ File already exists: {filename}")
        print("   Use --slug <other-slug> or edit the existing file.")
        sys.exit(1)

    # Triggers
    triggers = extract_triggers(text)
    if not triggers:
        triggers = ["note", args.type]

    # Anti-duplicate check
    if not args.force:
        is_dup, msg = anti_doublon_check(text)
        print(msg)
        if is_dup:
            sys.exit(2)

    # Compose
    fm = make_frontmatter(name, description, args.type, triggers)
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
    print(f"   Type    : {args.type}")
    print(f"   Triggers: {triggers}")
    print()
    print("⏭️ Suggested next steps:")
    print(f"   1. Edit the file to enrich (index_entry, related, assertions)")
    print(f"   2. Run `python scripts/rebuild_index.py --write` if index_entry added")
    print(f"   3. Run `python scripts/vector.py index` to reindex")
    print(f"   4. (Or just /sync-memory to orchestrate 2+3)")


if __name__ == "__main__":
    main()
