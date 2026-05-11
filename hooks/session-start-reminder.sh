#!/bin/bash
# SessionStart hook — forces reading of project state + memory protocol at startup.
cat <<'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "[Session start — memory protocol]\n\nBefore answering the first user message, do in order:\n1. Read the project's session handoff file (e.g. SESSION_HANDOFF.md) if present\n2. Read MEMORY.md (auto-generated index, section-by-section view)\n3. Confirm to the user: 'I have read the handoff. Resuming on <X>.' + list 3 main points\n\nPermanent rules:\n- Memory search = python scripts/vector.py search \"<topic>\" --k 3 BEFORE blind grep\n- Quick memory creation = python scripts/note.py \"<fact>\" (auto-frontmatter + anti-duplicate)\n- Memory workflows = /sync-memory (after memory change) · /consolidate-memory (end of session) · /audit-memory (monthly) · /handoff (close session)\n- Doubt about info = python scripts/verify.py --fail-only\n- Continuous encoding = project fact changed → update memory IN THE SAME RESPONSE, never batch at end-of-session\n- Anti-duplicate MANDATORY = vector search before create memory\n\nDetailed protocol: ~/.claude/projects/<PROJECT_ID>/memory/MEMORY_PROTOCOL.md\n"
  }
}
EOF
