"""Tests for note.py — slugify, trigger extraction, dry-run output."""
import importlib


def test_slugify_basic():
    import note
    s = note.slugify("This is a test memory about combat AP")
    # Stop-words removed? Not in slugify — it just takes first 8 words.
    # First 8 words: "this is a test memory about combat ap" → kebab
    assert s == "this-is-a-test-memory-about-combat-ap"


def test_slugify_ascii_safe():
    import note
    s = note.slugify("Tactical combat — Hoppe & friends")
    # Dash variants get cleaned; non-ASCII gets stripped
    assert "—" not in s
    assert "&" not in s
    assert s.replace("-", "").isalnum() or s.startswith("tactical")


def test_slugify_empty_fallback():
    import note
    assert note.slugify("") == "note"
    assert note.slugify("@@@@") == "note"


def test_slugify_caps_length():
    import note
    long_text = "word " * 50
    s = note.slugify(long_text)
    assert len(s) <= 50


def test_extract_triggers_filters_stopwords():
    import note
    triggers = note.extract_triggers("The combat system is the heart of the game design")
    assert "the" not in triggers
    assert "combat" in triggers or "system" in triggers or "design" in triggers


def test_extract_triggers_top_n():
    import note
    triggers = note.extract_triggers("combat combat combat strategy strategy unique", max_triggers=2)
    assert len(triggers) <= 2
    # 'combat' appears most → must be in top-N
    assert "combat" in triggers


def test_make_frontmatter_includes_required_fields():
    import note
    fm = note.make_frontmatter(
        name="X", description="Y", mem_type="feedback", triggers=["a", "b"]
    )
    assert "name: X" in fm
    assert "description: Y" in fm
    assert "type: feedback" in fm
    assert "triggers: [a, b]" in fm
    assert "last_verified:" in fm
