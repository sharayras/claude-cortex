"""_safe_io.py — UTF-8 safe stdin/stdout for Claude Code hooks.

Forces UTF-8 and emits ASCII-safe JSON to avoid orphan surrogates that break
the Anthropic API.
"""
import json
import sys


def read_input_json() -> dict:
    """Read stdin and parse JSON. Returns {} if invalid JSON."""
    if hasattr(sys.stdin, "reconfigure"):
        try:
            sys.stdin.reconfigure(encoding="utf-8")
        except Exception:
            pass
    try:
        raw = sys.stdin.read()
    except Exception:
        return {}
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def dump_for_claude(obj: dict) -> str:
    """Serialize a dict to ASCII-safe JSON (no orphan surrogates)."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
