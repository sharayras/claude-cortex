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


def test_template_feedback_has_index_entry_and_priority():
    """--from-template feedback emits index_entry, priority, related stubs (no last_verified, no assertions)."""
    import note
    fm = note.make_template_frontmatter(
        name="My rule", description="Always do X", mem_type="feedback", triggers=["x", "rule"]
    )
    assert "name: My rule" in fm
    assert "type: feedback" in fm
    assert "priority: normal" in fm
    assert "triggers: [x, rule]" in fm
    assert "related: []" in fm
    assert "index_entry:" in fm
    assert "PLACEHOLDER_SECTION" in fm
    assert "label: \"My rule\"" in fm
    # feedback has no last_verified
    assert "last_verified:" not in fm
    # feedback has no assertions
    assert "assertions:" not in fm


def test_template_project_adds_last_verified_and_assertion_stub():
    """--from-template project includes last_verified (today) + 1 assertion stub."""
    import datetime
    import note
    fm = note.make_template_frontmatter(
        name="A fact", description="...", mem_type="project", triggers=["fact"]
    )
    assert "type: project" in fm
    assert f"last_verified: {datetime.date.today().isoformat()}" in fm
    assert "assertions:" in fm
    assert "PLACEHOLDER_PATH" in fm
    assert "PLACEHOLDER_NEEDLE" in fm


def test_template_reference_no_last_verified_no_assertions():
    """--from-template reference has index_entry but no last_verified + no assertions."""
    import note
    fm = note.make_template_frontmatter(
        name="Ext doc", description="...", mem_type="reference", triggers=["ext"]
    )
    assert "type: reference" in fm
    assert "priority: normal" in fm
    assert "index_entry:" in fm
    # reference is not type=project, no last_verified
    assert "last_verified:" not in fm
    # reference has no assertions stub
    assert "assertions:" not in fm


def test_template_body_feedback_has_why_and_how_sections():
    """feedback/project body templates include Why + How to apply stubs."""
    import note
    body = note.make_template_body(name="My rule", text="Some content here", mem_type="feedback")
    assert "# My rule" in body
    assert "Some content here" in body
    assert "## Why" in body
    assert "## How to apply" in body


def test_template_body_reference_has_source_and_when_relevant():
    """reference body template uses Source + When relevant (not Why/How)."""
    import note
    body = note.make_template_body(name="Ext doc", text="See URL", mem_type="reference")
    assert "# Ext doc" in body
    assert "See URL" in body
    assert "## Source" in body
    assert "## When relevant" in body
    # reference does NOT use Why/How structure
    assert "## Why" not in body
    assert "## How to apply" not in body


def test_template_frontmatter_is_top_level_no_metadata_wrapping():
    """--from-template emits flat top-level YAML (no `metadata:` wrapping like Claude Code auto-memory).

    This is the whole point of the template flag: bypass the auto-memory transform that
    would otherwise wrap fields under `metadata:` (silently breaking rebuild_index until
    pass 7 fix). With templates, downstream consumers see the canonical schema directly.
    """
    import note
    fm = note.make_template_frontmatter(
        name="X", description="Y", mem_type="feedback", triggers=["a"]
    )
    # Critical: NO `metadata:` wrapping
    assert "\nmetadata:" not in fm
    assert "metadata: " not in fm
    # All key fields appear as top-level lines
    for needle in ("name:", "description:", "type:", "priority:", "triggers:", "index_entry:"):
        # Each must appear at start of a line (top-level), not indented
        assert any(line.startswith(needle) for line in fm.splitlines()), f"{needle!r} not at top level"
