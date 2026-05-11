#!/bin/bash
# PreToolUse Write on memory/*.md — anti-duplicate + supersession enforcement
RUNNER="$CLAUDE_PROJECT_DIR/{{CORTEX_SCRIPTS_DIR}}/_hook_runner.py"
[ ! -f "$RUNNER" ] && exit 0
python "$RUNNER" memory-write-check
