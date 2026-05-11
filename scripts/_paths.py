#!/usr/bin/env python3
"""_paths.py — Centralized path resolution for the cortex memory tooling.

Resolves PROJECT_ID, MEMORY_DIR, and INDEX_DIR from:
1. Explicit env vars (CORTEX_PROJECT_ID, CORTEX_MEMORY_DIR, CORTEX_INDEX_DIR)
2. Auto-detect from cwd (default — matches Claude Code's project ID convention)

The auto-detect normalizes the project path the same way Claude Code does:
    E:\\Games\\My Project  ->  E--Games-My-Project
    /home/user/proj         ->  -home-user-proj

This module is the **single point** where any path knowledge about the project
lives. All scripts in scripts/ import from here, never hardcode paths.
"""
import os
from pathlib import Path


def _normalize_path_to_project_id(path: Path) -> str:
    """Mirror Claude Code's project ID normalization (Windows + POSIX safe)."""
    s = str(path.resolve())
    # Drive separator E:\ -> E--
    s = s.replace(":\\", "--").replace(":/", "--")
    # Remaining path separators -> -
    s = s.replace("\\", "-").replace("/", "-")
    # Spaces -> -
    s = s.replace(" ", "-")
    return s


def get_project_id() -> str:
    """Return PROJECT_ID — explicit override or auto-detected from cwd."""
    explicit = os.environ.get("CORTEX_PROJECT_ID")
    if explicit:
        return explicit
    return _normalize_path_to_project_id(Path.cwd())


def get_memory_dir() -> Path:
    """Return the memory directory for the current project."""
    explicit = os.environ.get("CORTEX_MEMORY_DIR")
    if explicit:
        return Path(explicit)
    return Path.home() / ".claude" / "projects" / get_project_id() / "memory"


def get_index_dir() -> Path:
    """Return the vector index directory for the current project."""
    explicit = os.environ.get("CORTEX_INDEX_DIR")
    if explicit:
        return Path(explicit)
    return Path.home() / ".claude" / "projects" / get_project_id() / "_vector_index"


def get_project_root() -> Path:
    """Return the project root (cwd if contains .claude/, else parent of scripts/)."""
    cwd = Path.cwd().resolve()
    file_root = Path(__file__).resolve().parent.parent
    if (cwd / ".claude").exists():
        return cwd
    return file_root


def get_config_path() -> Path:
    """Return path to cortex_config.yaml — project-local override or repo default."""
    explicit = os.environ.get("CORTEX_CONFIG")
    if explicit:
        return Path(explicit)
    # Look for project-local config first
    local = get_project_root() / "cortex_config.yaml"
    if local.exists():
        return local
    # Fallback to memory dir default config
    return get_memory_dir() / "cortex_config.yaml"


# Resolved once at import for performance + consistency
PROJECT_ID = get_project_id()
MEMORY_DIR = get_memory_dir()
INDEX_DIR = get_index_dir()
PROJECT_ROOT = get_project_root()
CONFIG_PATH = get_config_path()


if __name__ == "__main__":
    # Diagnostic mode — `python scripts/_paths.py`
    print(f"PROJECT_ID   = {PROJECT_ID}")
    print(f"MEMORY_DIR   = {MEMORY_DIR}  (exists={MEMORY_DIR.exists()})")
    print(f"INDEX_DIR    = {INDEX_DIR}  (exists={INDEX_DIR.exists()})")
    print(f"PROJECT_ROOT = {PROJECT_ROOT}  (exists={PROJECT_ROOT.exists()})")
    print(f"CONFIG_PATH  = {CONFIG_PATH}  (exists={CONFIG_PATH.exists()})")
