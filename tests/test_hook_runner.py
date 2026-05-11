"""Tests for _hook_runner.py — JSON stdin parsing + memory hooks behavior."""
import importlib
import json


def test_safe_io_read_input_json_parses(monkeypatch):
    """_safe_io reads JSON from stdin and returns dict."""
    import _safe_io
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO('{"foo": "bar"}'))
    data = _safe_io.read_input_json()
    assert data == {"foo": "bar"}


def test_safe_io_read_input_json_empty(monkeypatch):
    """_safe_io returns {} on empty/invalid stdin."""
    import _safe_io
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    assert _safe_io.read_input_json() == {}
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    assert _safe_io.read_input_json() == {}


def test_safe_io_dump_for_claude_ascii_safe():
    """dump_for_claude produces parseable JSON with unicode preserved."""
    import _safe_io
    out = _safe_io.dump_for_claude({"key": "héllo 🎲"})
    parsed = json.loads(out)
    assert parsed["key"] == "héllo 🎲"


def test_frontmatter_validate_catches_missing_fields(isolated_cortex, make_memory):
    """memory-frontmatter-validate flags missing required fields."""
    import _hook_runner
    importlib.reload(_hook_runner)

    # Create a memory with missing 'type' field
    bad_path = isolated_cortex["memory_dir"] / "feedback_bad.md"
    bad_path.write_text("---\nname: Bad\ndescription: missing type\n---\n\nBody.\n", encoding="utf-8")

    errors = _hook_runner._validate_memory_frontmatter({"name": "Bad", "description": "no type"})
    assert any("type" in e and "missing" in e for e in errors)


def test_frontmatter_validate_catches_unquoted_date_trigger(isolated_cortex):
    """Unquoted date in triggers (datetime.date) is caught — would crash vector.py."""
    import _hook_runner
    importlib.reload(_hook_runner)

    import datetime
    fm = {
        "name": "X", "description": "y", "type": "project",
        "triggers": [datetime.date(2026, 5, 11), "valid-trigger"],
    }
    errors = _hook_runner._validate_memory_frontmatter(fm)
    assert any("datetime.date" in e for e in errors)


def test_frontmatter_validate_catches_invalid_type(isolated_cortex):
    """type outside the canonical set is flagged."""
    import _hook_runner
    importlib.reload(_hook_runner)

    fm = {"name": "X", "description": "y", "type": "garbage"}
    errors = _hook_runner._validate_memory_frontmatter(fm)
    assert any("type" in e and "invalid" in e for e in errors)


def test_frontmatter_validate_catches_invalid_priority(isolated_cortex):
    """priority outside the canonical set is flagged."""
    import _hook_runner
    importlib.reload(_hook_runner)

    fm = {"name": "X", "description": "y", "type": "project", "priority": "urgent"}
    errors = _hook_runner._validate_memory_frontmatter(fm)
    assert any("priority" in e and "invalid" in e for e in errors)


def test_frontmatter_validate_accepts_clean(isolated_cortex):
    """A well-formed frontmatter produces no errors."""
    import _hook_runner
    importlib.reload(_hook_runner)

    fm = {
        "name": "Good", "description": "valid", "type": "project",
        "last_verified": "2026-05-11",
        "triggers": ["one", "two"],
        "priority": "high",
    }
    errors = _hook_runner._validate_memory_frontmatter(fm)
    assert errors == []
