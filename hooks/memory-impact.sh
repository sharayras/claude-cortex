#!/bin/bash
# PostToolUse Edit|Write — flag memories that reference the modified file
RUNNER="$CLAUDE_PROJECT_DIR/{{CORTEX_SCRIPTS_DIR}}/_hook_runner.py"
[ ! -f "$RUNNER" ] && exit 0
python "$RUNNER" memory-impact
