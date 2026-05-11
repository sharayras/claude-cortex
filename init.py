#!/usr/bin/env python3
"""init.py — Bootstrap claude-cortex into an existing project.

Usage:
    cd /path/to/your/project
    python /path/to/claude-cortex/init.py

    # Or with explicit project dir:
    python /path/to/claude-cortex/init.py --project-dir /path/to/your/project

    # Custom scripts install dir (default: scripts/cortex/):
    python /path/to/claude-cortex/init.py --scripts-dir scripts/memory

Steps:
    1. Validate target project directory has .claude/ (or offer to create it)
    2. Copy scripts → <project>/<scripts-dir>/
    3. Copy hooks → <project>/.claude/hooks/ (substituting placeholder)
    4. Copy skills → <project>/.claude/skills/
    5. Copy cortex_config.yaml.example → <project>/cortex_config.yaml (if absent)
    6. Create memory dir (~/.claude/projects/<PROJECT_ID>/memory/)
    7. Copy template memories (MEMORY_PROTOCOL.md + examples)
    8. Optionally pip install requirements.txt
    9. Optionally register hooks in .claude/settings.local.json
   10. Optionally run first vector index build

Each step prompts for confirmation. Use --yes to accept all defaults non-interactively.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
PLACEHOLDER = "{{CORTEX_SCRIPTS_DIR}}"


def normalize_project_id(path: Path) -> str:
    """Mirror Claude Code's project ID normalization."""
    s = str(path.resolve())
    s = s.replace(":\\", "--").replace(":/", "--")
    s = s.replace("\\", "-").replace("/", "-")
    s = s.replace(" ", "-")
    return s


def ask(prompt: str, default: str = "y", non_interactive: bool = False) -> bool:
    """Yes/no prompt. Returns True if user accepts."""
    if non_interactive:
        return default.lower().startswith("y")
    answer = input(f"{prompt} [{default}]: ").strip().lower()
    if not answer:
        answer = default.lower()
    return answer.startswith("y")


def ask_text(prompt: str, default: str, non_interactive: bool = False) -> str:
    """Text prompt with a default."""
    if non_interactive:
        return default
    answer = input(f"{prompt} [{default}]: ").strip()
    return answer or default


def copy_with_substitution(src: Path, dest: Path, scripts_dir: str):
    """Copy a text file substituting {{CORTEX_SCRIPTS_DIR}} placeholder."""
    content = src.read_text(encoding="utf-8")
    content = content.replace(PLACEHOLDER, scripts_dir)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")


def copy_scripts(project_dir: Path, scripts_subdir: str, non_interactive: bool):
    """Copy scripts/*.py and requirements.txt to <project>/<scripts_subdir>/."""
    src_dir = REPO_ROOT / "scripts"
    dest_dir = project_dir / scripts_subdir
    print(f"\n→ Copying scripts: {src_dir} → {dest_dir}")
    if dest_dir.exists() and any(dest_dir.iterdir()):
        if not ask(f"  {dest_dir} exists and is non-empty. Overwrite?", "n", non_interactive):
            print("  Skipped scripts copy.")
            return False
    dest_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for src in src_dir.glob("*"):
        if src.is_file():
            shutil.copy2(src, dest_dir / src.name)
            count += 1
    print(f"  ✅ {count} files copied to {dest_dir}")
    return True


def copy_hooks(project_dir: Path, scripts_subdir: str, non_interactive: bool):
    """Copy hooks/*.sh to <project>/.claude/hooks/ with placeholder substitution."""
    src_dir = REPO_ROOT / "hooks"
    dest_dir = project_dir / ".claude" / "hooks"
    print(f"\n→ Copying hooks: {src_dir} → {dest_dir}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    skipped = 0
    for src in src_dir.glob("*.sh"):
        dest = dest_dir / src.name
        if dest.exists():
            if not ask(f"  {dest.name} exists. Overwrite?", "n", non_interactive):
                skipped += 1
                continue
        copy_with_substitution(src, dest, scripts_subdir)
        # On POSIX, make executable
        if os.name != "nt":
            os.chmod(dest, 0o755)
        count += 1
    print(f"  ✅ {count} hooks copied to {dest_dir} (skipped: {skipped})")


def copy_skills(project_dir: Path, scripts_subdir: str, non_interactive: bool):
    """Copy skills/*/SKILL.md to <project>/.claude/skills/ with substitution."""
    src_dir = REPO_ROOT / "skills"
    dest_root = project_dir / ".claude" / "skills"
    print(f"\n→ Copying skills: {src_dir} → {dest_root}")
    dest_root.mkdir(parents=True, exist_ok=True)
    count = 0
    skipped = 0
    for skill_dir in src_dir.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_dest = dest_root / skill_dir.name
        skill_dest.mkdir(parents=True, exist_ok=True)
        for src_file in skill_dir.glob("*"):
            if not src_file.is_file():
                continue
            dest_file = skill_dest / src_file.name
            if dest_file.exists():
                if not ask(f"  skills/{skill_dir.name}/{src_file.name} exists. Overwrite?", "n", non_interactive):
                    skipped += 1
                    continue
            copy_with_substitution(src_file, dest_file, scripts_subdir)
            count += 1
    print(f"  ✅ {count} skill files copied to {dest_root} (skipped: {skipped})")


def copy_rules(project_dir: Path, scripts_subdir: str, non_interactive: bool):
    """Copy rules/*.md to <project>/.claude/rules/ with substitution."""
    src_dir = REPO_ROOT / "rules"
    if not src_dir.exists() or not any(src_dir.iterdir()):
        return
    dest_dir = project_dir / ".claude" / "rules"
    print(f"\n→ Copying rules: {src_dir} → {dest_dir}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    skipped = 0
    for src in src_dir.glob("*.md"):
        dest = dest_dir / src.name
        if dest.exists():
            if not ask(f"  rules/{src.name} exists. Overwrite?", "n", non_interactive):
                skipped += 1
                continue
        copy_with_substitution(src, dest, scripts_subdir)
        count += 1
    print(f"  ✅ {count} rule files copied to {dest_dir} (skipped: {skipped})")


def setup_config(project_dir: Path, non_interactive: bool):
    """Copy cortex_config.yaml.example to <project>/cortex_config.yaml if absent."""
    src = REPO_ROOT / "cortex_config.yaml.example"
    dest = project_dir / "cortex_config.yaml"
    print(f"\n→ Cortex config: {dest}")
    if dest.exists():
        print(f"  cortex_config.yaml already exists — leaving as-is.")
        return
    if ask("  Create cortex_config.yaml from example template?", "y", non_interactive):
        shutil.copy2(src, dest)
        print(f"  ✅ {dest} created (edit to customize MEMORY.md layout)")


def setup_memory_dir(project_dir: Path, non_interactive: bool) -> Path:
    """Create memory dir and copy MEMORY_PROTOCOL.md + example memories."""
    project_id = normalize_project_id(project_dir)
    memory_dir = Path.home() / ".claude" / "projects" / project_id / "memory"
    print(f"\n→ Memory directory: {memory_dir}")
    memory_dir.mkdir(parents=True, exist_ok=True)
    print(f"  ✅ Memory dir ready (project_id: {project_id})")

    # Copy MEMORY_PROTOCOL.md if it doesn't exist
    protocol_src = REPO_ROOT / "MEMORY_PROTOCOL.md"
    protocol_dest = memory_dir / "MEMORY_PROTOCOL.md"
    if protocol_src.exists() and not protocol_dest.exists():
        if ask(f"  Copy MEMORY_PROTOCOL.md to memory dir?", "y", non_interactive):
            shutil.copy2(protocol_src, protocol_dest)
            print(f"  ✅ MEMORY_PROTOCOL.md copied")

    # Copy example memories if memory dir is empty (no .md files except possibly MEMORY_PROTOCOL)
    examples_dir = REPO_ROOT / "examples"
    if not examples_dir.exists():
        return memory_dir
    existing_memories = [
        p for p in memory_dir.glob("*.md")
        if p.name not in ("MEMORY.md", "MEMORY_BACKLOG.md", "MEMORY_REFERENCES.md", "MEMORY_PROTOCOL.md")
    ]
    if existing_memories:
        return memory_dir
    if ask(f"  Memory dir is empty. Seed with example template memories?", "y", non_interactive):
        count = 0
        for src in examples_dir.glob("*.md"):
            shutil.copy2(src, memory_dir / src.name)
            count += 1
        print(f"  ✅ {count} example memories copied")
    return memory_dir


def install_dependencies(scripts_dir: Path, non_interactive: bool):
    """pip install -r requirements.txt."""
    reqs = scripts_dir / "requirements.txt"
    if not reqs.exists():
        return
    print(f"\n→ Python dependencies: {reqs}")
    if not ask("  Run `pip install -r requirements.txt` now? (BGE-M3 ~1 GB on first vector index)", "y", non_interactive):
        print(f"  Skipped. Run manually: pip install -r {reqs}")
        return
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(reqs)],
        capture_output=False,
    )
    if result.returncode != 0:
        print(f"  ⚠️ pip install failed (exit {result.returncode}). Install manually.")
    else:
        print(f"  ✅ Dependencies installed")


def register_hooks(project_dir: Path, scripts_subdir: str, non_interactive: bool):
    """Add hook registrations to .claude/settings.local.json."""
    settings_path = project_dir / ".claude" / "settings.local.json"
    print(f"\n→ Hook registration: {settings_path}")
    if not ask("  Register cortex hooks in .claude/settings.local.json?", "y", non_interactive):
        print(f"  Skipped. Edit settings.local.json manually if you want hooks active.")
        return

    hooks_to_register = {
        "SessionStart": [
            {
                "matcher": "startup|resume|clear",
                "hooks": [
                    {"type": "command", "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/session-start-reminder.sh"},
                    {"type": "command", "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/session-start-verify.sh"},
                ],
            }
        ],
        "UserPromptSubmit": [
            {
                "hooks": [
                    {"type": "command", "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/memory-protocol-reminder.sh"},
                    {"type": "command", "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/skill-forced-eval.sh"},
                ]
            }
        ],
        "PreToolUse": [
            {
                "matcher": "Write",
                "hooks": [
                    {"type": "command", "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/memory-write-check.sh"}
                ],
            }
        ],
        "PostToolUse": [
            {
                "matcher": "Edit|Write",
                "hooks": [
                    {"type": "command", "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/memory-impact.sh"},
                    {"type": "command", "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/memory-frontmatter-validate.sh"},
                ],
            }
        ],
    }

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"  ⚠️ Existing settings.local.json is invalid JSON. Skipping registration.")
            return
    else:
        settings = {}

    existing_hooks = settings.setdefault("hooks", {})
    added = 0
    for event_name, new_entries in hooks_to_register.items():
        bucket = existing_hooks.setdefault(event_name, [])
        for entry in new_entries:
            # Skip if matcher already registered for this event
            if entry.get("matcher"):
                if any(e.get("matcher") == entry["matcher"] for e in bucket):
                    continue
            bucket.append(entry)
            added += 1

    settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  ✅ {added} hook registration(s) added to settings.local.json")
    if added == 0:
        print(f"  (all matchers were already present — nothing to add)")


def first_index_build(project_dir: Path, scripts_subdir: str, non_interactive: bool):
    """Run vector.py index for the first time."""
    print(f"\n→ First vector index build (may download BGE-M3 ~1 GB)")
    if not ask("  Run `python scripts/.../vector.py index` now?", "n", non_interactive):
        print(f"  Skipped. Run later when ready: cd <project> && python {scripts_subdir}/vector.py index")
        return
    scripts_dir = project_dir / scripts_subdir
    cmd = [sys.executable, str(scripts_dir / "vector.py"), "index"]
    result = subprocess.run(cmd, cwd=project_dir, capture_output=False)
    if result.returncode != 0:
        print(f"  ⚠️ vector.py index failed (exit {result.returncode}).")
    else:
        print(f"  ✅ Vector index built")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project-dir", type=Path, default=Path.cwd(),
                        help="Target project directory (default: cwd)")
    parser.add_argument("--scripts-dir", default="scripts/cortex",
                        help="Sub-directory for cortex Python scripts inside the project (default: scripts/cortex)")
    parser.add_argument("--yes", "-y", action="store_true",
                        help="Non-interactive: accept all defaults")
    parser.add_argument("--skip-deps", action="store_true",
                        help="Skip pip install")
    parser.add_argument("--skip-hooks", action="store_true",
                        help="Skip hook registration in settings.local.json")
    parser.add_argument("--skip-index", action="store_true",
                        help="Skip the first vector index build (BGE-M3 download)")
    args = parser.parse_args()

    project_dir = args.project_dir.resolve()
    print(f"\n┌─ claude-cortex bootstrap ─────────────────────────")
    print(f"│ Repo source : {REPO_ROOT}")
    print(f"│ Project dir : {project_dir}")
    print(f"│ Scripts dir : {project_dir / args.scripts_dir}")
    print(f"│ Project ID  : {normalize_project_id(project_dir)}")
    print(f"└───────────────────────────────────────────────────")

    if not project_dir.exists():
        print(f"\n❌ Project directory does not exist: {project_dir}")
        sys.exit(1)

    # Validate or create .claude/
    claude_dir = project_dir / ".claude"
    if not claude_dir.exists():
        if ask(f"\n.claude/ does not exist at {project_dir}. Create it?", "y", args.yes):
            claude_dir.mkdir(parents=True)
        else:
            print("Aborted — .claude/ is required.")
            sys.exit(1)

    # 1. Copy scripts
    copy_scripts(project_dir, args.scripts_dir, args.yes)

    # 2. Copy hooks
    copy_hooks(project_dir, args.scripts_dir, args.yes)

    # 3. Copy skills
    copy_skills(project_dir, args.scripts_dir, args.yes)

    # 3.5 Copy rules (optional path-scoped rule)
    copy_rules(project_dir, args.scripts_dir, args.yes)

    # 4. Setup config
    setup_config(project_dir, args.yes)

    # 5. Memory dir + protocol + examples
    setup_memory_dir(project_dir, args.yes)

    # 6. Dependencies
    if not args.skip_deps:
        install_dependencies(project_dir / args.scripts_dir, args.yes)

    # 7. Register hooks
    if not args.skip_hooks:
        register_hooks(project_dir, args.scripts_dir, args.yes)

    # 8. First index build
    if not args.skip_index:
        first_index_build(project_dir, args.scripts_dir, args.yes)

    print(f"\n✅ claude-cortex bootstrap complete!")
    print(f"\nNext steps:")
    print(f"  1. Edit cortex_config.yaml to customize MEMORY.md layout (optional)")
    print(f"  2. Create your first memory: python {args.scripts_dir}/note.py \"<your first fact>\"")
    print(f"  3. Search: python {args.scripts_dir}/vector.py search \"<topic>\" --k 3")
    print(f"  4. Build index: python {args.scripts_dir}/rebuild_index.py --write")
    print(f"\nIn Claude Code, use: /sync-memory  /audit-memory  /consolidate-memory  /handoff")


if __name__ == "__main__":
    main()
