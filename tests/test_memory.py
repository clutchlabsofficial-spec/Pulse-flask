import datetime as dt

import pytest

from jarvis.memory import MemoryError_, ObsidianMemory, slugify, strip_frontmatter


@pytest.fixture
def memory(tmp_path):
    mem = ObsidianMemory(tmp_path, subfolder="JARVIS")
    mem.ensure_vault()
    return mem


def test_ensure_vault_creates_scaffolding(memory, tmp_path):
    assert (tmp_path / "JARVIS" / "Memory" / "People").is_dir()
    assert (tmp_path / "JARVIS" / "Core.md").is_file()
    assert "Core Memory" in memory.core_memory()


def test_remember_writes_a_note(memory, tmp_path):
    path = memory.remember("Pepper Potts", "Runs Stark Industries.", "People")
    note = (tmp_path / path).read_text()
    assert "Runs Stark Industries." in note
    assert "tags:" in note


def test_remember_appends_without_duplicating_frontmatter(memory, tmp_path):
    memory.remember("Pepper Potts", "Runs Stark Industries.", "People")
    path = memory.remember("Pepper Potts", "Allergic to strawberries.", "People")
    note = (tmp_path / path).read_text()
    assert note.count("---\ncreated:") == 1
    assert "strawberries" in note and "Stark Industries" in note


def test_search_ranks_title_matches_first(memory):
    memory.remember("Mark VII", "Repulsor output increased by twelve percent.", "Projects")
    memory.remember("Coffee", "Prefers a flat white after ten in the morning.", "Preferences")
    hits = memory.search("repulsor output")
    assert hits and "Mark VII" in hits[0].title
    assert "repulsor" in hits[0].excerpt.lower()


def test_search_requires_a_real_term(memory):
    assert memory.search("the and of") == []


def test_search_scores_multi_term_matches_higher(memory):
    memory.write_note("JARVIS/Memory/Facts/A.md", "repulsor", mode="overwrite")
    memory.write_note("JARVIS/Memory/Facts/B.md", "repulsor calibration schedule", mode="overwrite")
    hits = memory.search("repulsor calibration")
    assert hits[0].title == "B"


def test_forget_removes_only_matching_lines(memory, tmp_path):
    path = memory.remember("Pepper Potts", "Lives in Malibu.", "People")
    memory.remember("Pepper Potts", "Allergic to strawberries.", "People")
    removed = memory.forget(path, "Malibu")
    assert removed == 1
    note = (tmp_path / path).read_text()
    assert "Malibu" not in note
    assert "strawberries" in note


def test_forget_refuses_empty_needle(memory):
    path = memory.remember("X", "y", "Facts")
    with pytest.raises(MemoryError_):
        memory.forget(path, "   ")


def test_path_traversal_is_refused(memory):
    with pytest.raises(MemoryError_):
        memory.resolve("../../etc/passwd")
    with pytest.raises(MemoryError_):
        memory.write_note("../escape.md", "nope")


def test_write_note_modes(memory, tmp_path):
    memory.write_note("JARVIS/Notes.md", "first", mode="overwrite")
    memory.write_note("JARVIS/Notes.md", "second", mode="append")
    memory.write_note("JARVIS/Notes.md", "zeroth", mode="prepend")
    body = (tmp_path / "JARVIS" / "Notes.md").read_text()
    assert body.index("zeroth") < body.index("first") < body.index("second")


def test_write_note_rejects_bad_mode(memory):
    with pytest.raises(MemoryError_):
        memory.write_note("JARVIS/Notes.md", "x", mode="delete")


def test_log_exchange_uses_todays_note(memory, tmp_path):
    memory.log_exchange("Are the repulsors ready?", "Calibrated and ready, sir.")
    today = dt.date.today().isoformat()
    note = (tmp_path / "JARVIS" / "Conversations" / f"{today}.md").read_text()
    assert "Calibrated and ready" in note


def test_read_note_missing(memory):
    with pytest.raises(MemoryError_):
        memory.read_note("JARVIS/Nope.md")


def test_cache_invalidates_on_change(memory, tmp_path):
    memory.write_note("JARVIS/Memory/Facts/Q.md", "alpha", mode="overwrite")
    assert memory.search("alpha")
    note = tmp_path / "JARVIS" / "Memory" / "Facts" / "Q.md"
    note.write_text("---\n---\nbravo\n")
    import os, time
    os.utime(note, (time.time() + 2, time.time() + 2))
    assert memory.search("bravo")


def test_slugify_strips_path_characters():
    assert "/" not in slugify("Projects/../../etc")
    assert slugify("  Mark VII  ") == "Mark VII"


def test_strip_frontmatter():
    assert strip_frontmatter("---\ntags: [a]\n---\nbody\n").strip() == "body"


def test_stats_reports_counts(memory):
    memory.remember("A", "one", "Facts")
    stats = memory.stats()
    assert stats["available"] is True
    assert stats["notes"] >= 1
