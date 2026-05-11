#!/bin/bash
# PostToolUse Edit|Write on memory/*.md — validate frontmatter against schema
RUNNER="$CLAUDE_PROJECT_DIR/{{CORTEX_SCRIPTS_DIR}}/_hook_runner.py"
[ ! -f "$RUNNER" ] && exit 0
python "$RUNNER" memory-frontmatter-validate
