"""Tests for rebuild_index.py — idempotent + config-driven layout."""
import importlib


def test_rebuild_idempotent(isolated_cortex, make_memory):
    """Running rebuild twice produces identical content."""
    make_memory("project_a.md", {
        "name": "A", "description": "first", "type": "project",
        "index_entry": {"section": "🧠 Semantic — Design", "order": 10, "label": "A", "hook": "first thing"},
    })
    make_memory("feedback_b.md", {
        "name": "B", "description": "second", "type": "feedback",
        "index_entry": {"section": "⚙️ Procedural — Workflows", "order": 5, "label": "B", "hook": "second thing"},
    })

    import rebuild_index
    importlib.reload(rebuild_index)

    config = rebuild_index.load_config()
    entries = rebuild_index.collect_entries()
    content1 = rebuild_index.render(entries, config)
    content2 = rebuild_index.render(entries, config)
    assert content1 == content2


def test_rebuild_groups_by_section(isolated_cortex, make_memory):
    """Memories appear under their declared section, in order."""
    make_memory("project_a.md", {
        "name": "A", "description": "...", "type": "project",
        "index_entry": {"section": "🧠 Semantic — Design", "order": 20, "label": "A-second", "hook": "h"},
    })
    make_memory("project_b.md", {
        "name": "B", "description": "...", "type": "project",
        "index_entry": {"section": "🧠 Semantic — Design", "order": 10, "label": "B-first", "hook": "h"},
    })

    import rebuild_index
    importlib.reload(rebuild_index)

    config = rebuild_index.load_config()
    entries = rebuild_index.collect_entries()
    content = rebuild_index.render(entries, config)

    # B-first (order 10) must appear before A-second (order 20)
    pos_b = content.find("B-first")
    pos_a = content.find("A-second")
    assert pos_b != -1 and pos_a != -1
    assert pos_b < pos_a


def test_rebuild_skips_memory_without_index_entry(isolated_cortex, make_memory):
    """Memories without index_entry are absent from MEMORY.md."""
    make_memory("project_hidden.md", {
        "name": "Hidden", "description": "no index", "type": "project",
    })
    make_memory("project_visible.md", {
        "name": "Visible", "description": "indexed", "type": "project",
        "index_entry": {"section": "🧠 Semantic — Design", "order": 10, "label": "Visible", "hook": "h"},
    })

    import rebuild_index
    importlib.reload(rebuild_index)

    config = rebuild_index.load_config()
    entries = rebuild_index.collect_entries()
    content = rebuild_index.render(entries, config)

    assert "Visible" in content
    assert "Hidden" not in content


def test_rebuild_writes_subfile(isolated_cortex, make_memory):
    """Sections in subfile config get their own file."""
    make_memory("project_backlog.md", {
        "name": "Backlog item", "description": "...", "type": "project",
        "index_entry": {"section": "🚧 Future work", "order": 10, "label": "Backlog item", "hook": "h"},
    })

    import rebuild_index
    importlib.reload(rebuild_index)

    config = rebuild_index.load_config()
    entries = rebuild_index.collect_entries()

    # Sub-file content
    subfile_content = rebuild_index.render_subfile("MEMORY_BACKLOG.md", entries, config)
    assert "Backlog item" in subfile_content

    # Main MEMORY.md should NOT contain the backlog item (delocated)
    main_content = rebuild_index.render(entries, config)
    assert "Backlog item" not in main_content
    # But should have a Sub-index pointer
    assert "MEMORY_BACKLOG.md" in main_content
