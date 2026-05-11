"""Tests for verify.py — assertion checks against real source files."""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VERIFY_PY = REPO_ROOT / "scripts" / "verify.py"


def _run_verify(cwd, env, *args):
    """Helper to invoke verify.py as subprocess."""
    cmd = [sys.executable, str(VERIFY_PY), *args]
    return subprocess.run(cmd, cwd=cwd, env={**env}, capture_output=True, text=True, encoding="utf-8")


def test_verify_pass(isolated_cortex, make_memory):
    """An assertion that matches the source file should PASS."""
    # Create a source file
    src = isolated_cortex["project_root"] / "config.py"
    src.write_text("PA_POOL = 6\n", encoding="utf-8")

    # Create a memory with a matching assertion
    make_memory("project_pa.md", {
        "name": "PA pool", "description": "PA at 6", "type": "project",
        "assertions": [{"source": "config.py", "contains": "PA_POOL = 6"}],
    })

    env = {
        **dict(__import__("os").environ),
        "CORTEX_PROJECT_ID": "test-project",
        "CORTEX_MEMORY_DIR": str(isolated_cortex["memory_dir"]),
        "CORTEX_INDEX_DIR": str(isolated_cortex["index_dir"]),
    }
    result = _run_verify(isolated_cortex["project_root"], env)
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    assert "PASS" in result.stdout
    assert "FAIL: 0" in result.stdout.replace(" ", " ")


def test_verify_fail_drift_detection(isolated_cortex, make_memory):
    """A memory asserting a value that diverges from source returns FAIL + exit 1."""
    src = isolated_cortex["project_root"] / "config.py"
    src.write_text("PA_POOL = 8\n", encoding="utf-8")  # value diverged

    make_memory("project_pa.md", {
        "name": "PA pool", "description": "PA at 6", "type": "project",
        "assertions": [{"source": "config.py", "contains": "PA_POOL = 6"}],
    })

    env = {
        **dict(__import__("os").environ),
        "CORTEX_PROJECT_ID": "test-project",
        "CORTEX_MEMORY_DIR": str(isolated_cortex["memory_dir"]),
        "CORTEX_INDEX_DIR": str(isolated_cortex["index_dir"]),
    }
    result = _run_verify(isolated_cortex["project_root"], env)
    assert result.returncode == 1
    # The FAIL count line should mention at least one failure
    assert "FAIL" in result.stdout


def test_verify_skip_missing_source(isolated_cortex, make_memory):
    """An assertion pointing to a missing source returns SKIP, not FAIL."""
    make_memory("project_pa.md", {
        "name": "PA pool", "description": "PA at 6", "type": "project",
        "assertions": [{"source": "nonexistent.py", "contains": "anything"}],
    })

    env = {
        **dict(__import__("os").environ),
        "CORTEX_PROJECT_ID": "test-project",
        "CORTEX_MEMORY_DIR": str(isolated_cortex["memory_dir"]),
        "CORTEX_INDEX_DIR": str(isolated_cortex["index_dir"]),
    }
    result = _run_verify(isolated_cortex["project_root"], env)
    # SKIP doesn't fail the run — exit 0
    assert result.returncode == 0
    assert "SKIP" in result.stdout


def test_verify_regex_assertion(isolated_cortex, make_memory):
    """Regex assertions support pattern matching."""
    src = isolated_cortex["project_root"] / "balance.md"
    src.write_text("# Balance\nThe pa_pool = 6 for all units.\n", encoding="utf-8")

    make_memory("project_pa.md", {
        "name": "PA regex", "description": "...", "type": "project",
        "assertions": [{"source": "balance.md", "regex": r"pa_pool\s*=\s*\d+"}],
    })

    env = {
        **dict(__import__("os").environ),
        "CORTEX_PROJECT_ID": "test-project",
        "CORTEX_MEMORY_DIR": str(isolated_cortex["memory_dir"]),
        "CORTEX_INDEX_DIR": str(isolated_cortex["index_dir"]),
    }
    result = _run_verify(isolated_cortex["project_root"], env)
    assert result.returncode == 0
    assert "PASS" in result.stdout
