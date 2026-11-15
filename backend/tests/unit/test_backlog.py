"""Tests that keep `product/tasks.md` and the doc set from silently rotting.

The backlog is only useful if it stays machine-readable and its cross-references
resolve. These run in the normal suite so a hand-edit that breaks the table, or
a renamed document, fails like any other regression.

`scripts/tasks.py` is stdlib-only and not an installed package, so it is
imported by path.
"""

import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import tasks  # noqa: E402


@pytest.fixture
def lines() -> list[str]:
    return tasks.read_lines()


@pytest.fixture
def stories(lines: list[str]) -> list[tasks.Story]:
    return tasks.parse_stories(lines)


def test_backlog_file_exists() -> None:
    assert tasks.TASKS_PATH.is_file(), f"Backlog missing at {tasks.TASKS_PATH}"


def test_rows_parse(stories: list[tasks.Story]) -> None:
    """A broken table silently yields zero rows, which would make every other check vacuous."""
    assert len(stories) > 20, f"Only {len(stories)} rows parsed — table format likely broken"


def test_story_ids_are_unique(stories: list[tasks.Story]) -> None:
    seen: dict[str, int] = {}
    duplicates = []
    for story in stories:
        if story.id in seen:
            duplicates.append(f"{story.id} (lines {seen[story.id]} and {story.line_no})")
        seen[story.id] = story.line_no
    assert not duplicates, f"Duplicate ids: {', '.join(duplicates)}"


def test_statuses_match_the_legend(lines: list[str], stories: list[tasks.Story]) -> None:
    """The legend in the file is the source of truth; code never duplicates the list."""
    legal = tasks.parse_statuses(lines)
    offenders = [f"{s.id}={s.status} (line {s.line_no})" for s in stories if s.status not in legal]
    assert not offenders, f"Statuses outside the legend {sorted(legal)}: {', '.join(offenders)}"


@pytest.mark.parametrize("doc_name", tasks.LINKED_DOCS)
def test_internal_links_resolve(doc_name: str) -> None:
    doc = REPO_ROOT / doc_name
    assert doc.is_file(), f"Missing document: {doc_name}"
    broken = [link for link in tasks.internal_links(doc) if not (doc.parent / link).is_file()]
    assert not broken, f"{doc_name} has broken links: {', '.join(broken)}"


def test_validate_passes_on_the_real_backlog() -> None:
    assert tasks.validate() == []


def test_set_status_changes_exactly_one_line(tmp_path: Path) -> None:
    """`set` must be surgical — a sloppy rewrite would churn the whole file."""
    copy = tmp_path / "tasks.md"
    shutil.copy(tasks.TASKS_PATH, copy)
    before = copy.read_text(encoding="utf-8").splitlines()

    target = next(s for s in tasks.parse_stories(before) if s.status == "TODO")
    tasks.set_status(target.id, "WIP", path=copy)

    after = copy.read_text(encoding="utf-8").splitlines()
    differing = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
    assert len(before) == len(after), "line count changed"
    assert differing == [target.line_no - 1], f"expected 1 changed line, got {len(differing)}"
    assert tasks.find_story(tasks.parse_stories(after), target.id).status == "WIP"


def test_set_status_round_trips(tmp_path: Path) -> None:
    copy = tmp_path / "tasks.md"
    shutil.copy(tasks.TASKS_PATH, copy)
    original = copy.read_text(encoding="utf-8")

    target = next(s for s in tasks.parse_stories(copy.read_text().splitlines()) if s.status == "TODO")
    tasks.set_status(target.id, "DONE", path=copy)
    tasks.set_status(target.id, "TODO", path=copy)

    assert copy.read_text(encoding="utf-8") == original


def test_set_status_rejects_unknown_status(tmp_path: Path) -> None:
    copy = tmp_path / "tasks.md"
    shutil.copy(tasks.TASKS_PATH, copy)
    with pytest.raises(tasks.BacklogError, match="Unknown status"):
        tasks.set_status("S1.1.1", "NOPE", path=copy)


def test_set_status_rejects_unknown_id(tmp_path: Path) -> None:
    copy = tmp_path / "tasks.md"
    shutil.copy(tasks.TASKS_PATH, copy)
    with pytest.raises(tasks.BacklogError, match="No story with id"):
        tasks.set_status("S99.99.99", "DONE", path=copy)


def test_validate_detects_a_duplicate_id(tmp_path: Path) -> None:
    """Proves the validation can actually fail — a check that can't fail is theatre."""
    copy = tmp_path / "tasks.md"
    shutil.copy(tasks.TASKS_PATH, copy)
    rows = copy.read_text(encoding="utf-8").splitlines()
    first_row = next(i for i, line in enumerate(rows) if tasks.ROW_PATTERN.match(line))
    rows.insert(first_row + 1, rows[first_row])
    copy.write_text("\n".join(rows) + "\n", encoding="utf-8")

    problems = tasks.validate(path=copy)

    assert any("Duplicate id" in p for p in problems), problems


def test_validate_detects_a_broken_table(tmp_path: Path) -> None:
    copy = tmp_path / "tasks.md"
    copy.write_text("**Status key**: `TODO` · `DONE`\n\nno rows here\n", encoding="utf-8")

    problems = tasks.validate(path=copy)

    assert any("No story rows parsed" in p for p in problems), problems
