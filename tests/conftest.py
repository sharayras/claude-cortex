"""Shared pytest fixtures for claude-cortex tests.

Strategy:
- Each test runs with an isolated MEMORY_DIR + INDEX_DIR via env vars
- Cortex scripts are imported by adding `scripts/` to sys.path
- Modules that cache CORTEX_* env vars at import time are reloaded per-test
"""
import importlib
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"

# Ensure scripts/ is importable for all tests
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def isolated_cortex(tmp_path, monkeypatch):
    """Provide an isolated cortex environment: memory dir + index dir + project root.

    Returns a dict with paths. After the test, env vars are reset and modules
    that resolve paths at import time are reloaded.
    """
    project_root = tmp_path / "project"
    memory_dir = tmp_path / "memory"
    index_dir = tmp_path / "_vector_index"
    project_root.mkdir()
    # _paths.get_project_root() looks for .claude/ to pick cwd as PROJECT_ROOT
    (project_root / ".claude").mkdir()
    memory_dir.mkdir()

    monkeypatch.setenv("CORTEX_PROJECT_ID", "test-project")
    monkeypatch.setenv("CORTEX_MEMORY_DIR", str(memory_dir))
    monkeypatch.setenv("CORTEX_INDEX_DIR", str(index_dir))
    monkeypatch.chdir(project_root)

    # Reload _paths and any module that imports it, so the new env vars take effect
    for mod_name in ("_paths", "verify", "rebuild_index", "note", "_hook_runner"):
        if mod_name in sys.modules:
            importlib.reload(sys.modules[mod_name])

    yield {
        "project_root": project_root,
        "memory_dir": memory_dir,
        "index_dir": index_dir,
        "tmp_path": tmp_path,
    }


def write_memory(memory_dir: Path, name: str, frontmatter: dict, body: str = "Body.") -> Path:
    """Helper: write a memory file with given frontmatter dict + body."""
    import yaml
    fm_yaml = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False).strip()
    content = f"---\n{fm_yaml}\n---\n\n{body}\n"
    path = memory_dir / name
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def make_memory(isolated_cortex):
    """Factory fixture for writing memory files."""
    def _factory(name: str, frontmatter: dict, body: str = "Body.") -> Path:
        return write_memory(isolated_cortex["memory_dir"], name, frontmatter, body)
    return _factory
