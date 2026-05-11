#!/bin/bash
# UserPromptSubmit hook — injects a memory protocol reminder at each turn
cat <<'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "[Memory protocol reminder]\n- Topic mentioned (any domain concept) -> `python scripts/vector.py search \"<topic>\" --k 3` BEFORE blind Read/Grep on memory/. MEMORY.md is an index, not the source of truth.\n- Known workflow -> invoke the skill: /sync-memory (after memory change), /consolidate-memory (end of session), /audit-memory (monthly), /handoff (close session).\n- Anti-duplicate before create memory: `vector.py search` or `note.py` (which forces it auto)."
  }
}
EOF
