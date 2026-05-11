"""Tests for _paths.py — env var resolution and project ID normalization."""
import importlib
import os
import sys
from pathlib import Path


def test_env_var_overrides(monkeypatch, tmp_path):
    """CORTEX_PROJECT_ID + CORTEX_MEMORY_DIR + CORTEX_INDEX_DIR override defaults."""
    monkeypatch.setenv("CORTEX_PROJECT_ID", "test-id")
    monkeypatch.setenv("CORTEX_MEMORY_DIR", str(tmp_path / "mem"))
    monkeypatch.setenv("CORTEX_INDEX_DIR", str(tmp_path / "idx"))

    import _paths
    importlib.reload(_paths)

    assert _paths.PROJECT_ID == "test-id"
    assert _paths.MEMORY_DIR == tmp_path / "mem"
    assert _paths.INDEX_DIR == tmp_path / "idx"


def test_normalize_strips_forbidden_chars(tmp_path):
    """Normalized project IDs contain no path separators, colons, or spaces."""
    import _paths
    weird = tmp_path / "Some Folder" / "with spaces"
    weird.mkdir(parents=True)
    pid = _paths._normalize_path_to_project_id(weird)
    assert ":" not in pid
    assert "\\" not in pid
    assert "/" not in pid
    assert " " not in pid
    assert pid  # non-empty


def test_normalize_is_deterministic():
    """Same input → same output."""
    import _paths
    a = _paths._normalize_path_to_project_id(Path("/some/path/x"))
    b = _paths._normalize_path_to_project_id(Path("/some/path/x"))
    assert a == b


def test_project_id_autodetect_from_cwd(monkeypatch, tmp_path):
    """Without env override, PROJECT_ID derives from cwd."""
    monkeypatch.delenv("CORTEX_PROJECT_ID", raising=False)
    monkeypatch.delenv("CORTEX_MEMORY_DIR", raising=False)
    monkeypatch.delenv("CORTEX_INDEX_DIR", raising=False)
    monkeypatch.chdir(tmp_path)

    import _paths
    importlib.reload(_paths)

    # PROJECT_ID should contain a normalized form of tmp_path
    assert _paths.PROJECT_ID  # non-empty
    # MEMORY_DIR should be under ~/.claude/projects/<id>/memory
    assert ".claude" in str(_paths.MEMORY_DIR)
    assert "memory" in str(_paths.MEMORY_DIR)
