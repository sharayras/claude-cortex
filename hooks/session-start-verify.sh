#!/bin/bash
# SessionStart hook — runs verify.py --fail-only and injects detected drifts
# into the start-of-session context. Silent if 0 FAIL.

export PYTHONIOENCODING=utf-8

SCRIPTS_DIR="$CLAUDE_PROJECT_DIR/{{CORTEX_SCRIPTS_DIR}}"
[ ! -f "$SCRIPTS_DIR/_safe_io.py" ] && exit 0
[ ! -f "$SCRIPTS_DIR/verify.py" ] && exit 0

OUT=$(cd "$CLAUDE_PROJECT_DIR" 2>/dev/null && python -X utf8 "$SCRIPTS_DIR/verify.py" --fail-only 2>&1)
EC=$?

# If verify.py returns 0 (no FAIL) → inject nothing
if [ "$EC" -eq 0 ]; then
  exit 0
fi

# Build JSON via _safe_io (guarantees ASCII + zero surrogate)
printf '%s' "$OUT" | python -X utf8 -c "
import sys, os
sys.path.insert(0, os.environ.get('CORTEX_SCRIPTS_ABS', ''))
from _safe_io import dump_for_claude

raw = sys.stdin.read()
msg = ('[verify.py — memory drifts detected at startup]\n\n'
       'Code/design has diverged from what some memories claim. Fix BEFORE any other action:\n\n'
       + raw)
print(dump_for_claude({
    'hookSpecificOutput': {
        'hookEventName': 'SessionStart',
        'additionalContext': msg,
    }
}))
" CORTEX_SCRIPTS_ABS="$SCRIPTS_DIR"
