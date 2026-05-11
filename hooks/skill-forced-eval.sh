#!/bin/bash
# UserPromptSubmit hook — adaptive evaluation of memory skills
# Injects the skill grid ONLY if the prompt contains skill keywords
# Saves tokens when the question is off-skill

input=$(cat)
prompt=$(echo "$input" | python -c "import json,sys; print(json.load(sys.stdin).get('prompt',''))" 2>/dev/null)
prompt_lower=$(echo "$prompt" | tr '[:upper:]' '[:lower:]')

# Trigger keywords (skill potentially relevant)
if echo "$prompt_lower" | grep -qE 'handoff|close session|end of session|consolidate|consolidat|audit|sync.?memory|sync.?memoire|sync.?mémoire|check.*memor|rebuild.*memor|reindex'; then
    cat <<'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "[SKILL CHECK] Relevant memory skills: /handoff (close session) · /consolidate-memory (extract learnings) · /sync-memory (reindex BGE-M3 + rebuild MEMORY.md) · /audit-memory (monthly). Canonical end-of-session workflow: /handoff → /consolidate-memory → /sync-memory. Invoke via Skill() — no improvisation."
  }
}
EOF
else
    # No skill keyword → no context injected (token saving)
    echo '{}'
fi
