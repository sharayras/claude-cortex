# Demo recording script

The exact command sequence to run during recording. Total runtime ~45s. Designed for an existing claude-cortex install with at least 10-20 memories indexed (use the maintainer's dogfooding cortex or seed a temp one).

## Setup before recording

```bash
# Ensure a populated cortex exists (use your real project or seed a demo one)
cd ~/your/claude-code/project

# Verify state
ls ~/.claude/projects/$(python -c "from scripts._paths import PROJECT_ID; print(PROJECT_ID)")/memory/ | wc -l
# Should show 20+ files for a meaningful demo

# Pre-warm BGE-M3 (avoids first-call ~3s model load showing in the recording)
python ~/tools/claude-cortex/scripts/vector.py search "warmup" --k 1 > /dev/null

# Set a clean prompt for recording
export PS1="$ "
clear
```

## Recording sequence (~45s)

### Beat 1 — the problem (5s)

```bash
# Pretend to look up something via grep — show the noise
grep -ri "facing" ~/.claude/projects/*/memory/ | wc -l
# Output: 47 (or whatever) — too many irrelevant matches
```

Beat → audience feels the pain.

### Beat 2 — vector.py to the rescue (10s)

```bash
python ~/tools/claude-cortex/scripts/vector.py search "tactical combat facing rules" --k 3
```

Output (formatted, top 3 with scores) appears in <100ms after BGE-M3 load. Show that the top result is the canonical memory, not a false positive.

Beat → audience sees the relevance jump.

### Beat 3 — verify.py drift detection (15s)

```bash
python ~/tools/claude-cortex/scripts/verify.py
```

Output : `✅ 18/19 PASS · ❌ 0 FAIL · ⚠️ 1 SKIP`. Each line shows a memory's assertion checked against a real source file (`'MULT_REAR' found in design/gdd/...`).

Beat → audience understands "this is not just another markdown index".

### Beat 4 — note.py anti-duplicate (10s)

```bash
python ~/tools/claude-cortex/scripts/note.py "Tactical combat uses 4-direction facing with 1.0/1.15/1.30 damage multipliers" --dry-run
```

Output : the anti-duplicate check fires — `⚠️ Potential duplicate detected (project_tactical_combat_dna.md, score=0.78 > 0.6)` — and prompts the user to extend rather than create.

Beat → audience sees enforcement, not just advisory.

### Beat 5 — wrap (3-5s)

Show one final line :

```bash
echo "claude-cortex : memories that don't rot."
```

Or just rest on the previous output.

## Timing notes

- Type each command at a calm pace (~6-8 chars/sec). Don't rush.
- After pressing Enter, wait for output to fully render before starting the next command (1-2s pause).
- Total budget : Beat 1 (5s) + Beat 2 (10s) + Beat 3 (15s) + Beat 4 (10s) + Beat 5 (3-5s) = ~43-45s.

## Variations

- Skip Beat 1 if you want to save 5s (jump straight to vector.py).
- Replace Beat 4 with `note.py --from-template feedback "..."` to showcase the new template flag (issue #1).
- Add a Beat 0 (5s) showing `cat ~/.claude/projects/.../memory/MEMORY.md | head -20` to illustrate the auto-generated index, if you want to highlight `rebuild_index.py` too.
