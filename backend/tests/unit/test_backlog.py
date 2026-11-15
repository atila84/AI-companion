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


# --- automatic status advancement from commit messages -------------------------


@pytest.fixture
def backlog_copy(tmp_path: Path) -> Path:
    copy = tmp_path / "tasks.md"
    shutil.copy(tasks.TASKS_PATH, copy)
    return copy


def _status(path: Path, story_id: str) -> str:
    return tasks.find_story(tasks.parse_stories(tasks.read_lines(path)), story_id).status


def _a_todo(path: Path) -> str:
    """Any story currently TODO.

    Picked dynamically: hardcoding an id couples the test to the live backlog's
    current state, which the post-commit hook changes underneath it.
    """
    return next(s.id for s in tasks.parse_stories(tasks.read_lines(path)) if s.status == "TODO")


def test_reference_moves_todo_to_wip(backlog_copy: Path) -> None:
    """Committing against a story is unambiguous evidence work started."""
    story_id = _a_todo(backlog_copy)

    changes = tasks.advance_from_message(f"feat: add thing ({story_id})", path=backlog_copy)

    assert changes == [(story_id, "TODO", "WIP")]
    assert _status(backlog_copy, story_id) == "WIP"


def test_close_keyword_moves_to_done(backlog_copy: Path) -> None:
    story_id = _a_todo(backlog_copy)

    changes = tasks.advance_from_message(f"feat: add thing, closes {story_id}", path=backlog_copy)

    assert changes == [(story_id, "TODO", "DONE")]
    assert _status(backlog_copy, story_id) == "DONE"


@pytest.mark.parametrize("verb", ["closes", "Closed", "fixes", "fix", "completes", "resolved"])
def test_close_verbs_are_recognised(verb: str, backlog_copy: Path) -> None:
    story_id = _a_todo(backlog_copy)

    tasks.advance_from_message(f"work: {verb} {story_id}", path=backlog_copy)

    assert _status(backlog_copy, story_id) == "DONE"


def test_bare_reference_never_marks_done(backlog_copy: Path) -> None:
    """A false DONE is worse than a stale TODO — never infer completion."""
    story_id = _a_todo(backlog_copy)

    tasks.advance_from_message(f"wip: first pass at {story_id}", path=backlog_copy)

    assert _status(backlog_copy, story_id) == "WIP"


def test_blocked_and_deferred_are_left_alone(backlog_copy: Path) -> None:
    """Those are deliberate states, not staleness."""
    tasks.set_status("S4.1.1", "BLOCKED", path=backlog_copy)

    changes = tasks.advance_from_message("chore: poke S4.1.1", path=backlog_copy)

    assert changes == []
    assert _status(backlog_copy, "S4.1.1") == "BLOCKED"


def test_already_done_is_not_rewritten(backlog_copy: Path) -> None:
    changes = tasks.advance_from_message("chore: note E0.1", path=backlog_copy)

    assert changes == []


def test_unknown_ids_are_ignored(backlog_copy: Path) -> None:
    before = backlog_copy.read_text(encoding="utf-8")

    assert tasks.advance_from_message("feat: thing (S99.99.99)", path=backlog_copy) == []
    assert backlog_copy.read_text(encoding="utf-8") == before


def test_message_with_no_reference_changes_nothing(backlog_copy: Path) -> None:
    before = backlog_copy.read_text(encoding="utf-8")

    assert tasks.advance_from_message("docs: tidy readme", path=backlog_copy) == []
    assert backlog_copy.read_text(encoding="utf-8") == before


def test_multiple_stories_in_one_message(backlog_copy: Path) -> None:
    todos = [s.id for s in tasks.parse_stories(tasks.read_lines(backlog_copy)) if s.status == "TODO"]
    first, second = todos[0], todos[1]

    changes = tasks.advance_from_message(
        f"feat: groundwork for {second}, closes {first}", path=backlog_copy
    )

    assert dict((c[0], c[2]) for c in changes) == {first: "DONE", second: "WIP"}


# --- regression: rows with a trailing note after the status --------------------


def test_row_with_trailing_note_parses(stories: list[tasks.Story]) -> None:
    """Regression: `| S4.1.1 | ... | `BLOCKED` — external lead time |` was silently
    skipped by a stricter pattern, making the story invisible to the tooling."""
    story = tasks.find_story(stories, "S4.1.1")

    assert story.status == "BLOCKED"


def test_every_row_shaped_like_a_story_actually_parses(lines: list[str]) -> None:
    """The dangerous failure is a row the parser skips without complaint."""
    parsed = {s.line_no for s in tasks.parse_stories(lines)}
    missed = [
        f"line {i}: {line.strip()[:60]}"
        for i, line in enumerate(lines, start=1)
        if tasks.LOOSE_ROW_PATTERN.match(line) and i not in parsed
    ]

    assert not missed, f"Rows invisible to the tooling: {missed}"


def test_set_status_preserves_a_trailing_note(backlog_copy: Path) -> None:
    tasks.set_status("S4.1.1", "WIP", path=backlog_copy)

    row = next(l for l in tasks.read_lines(backlog_copy) if l.startswith("| S4.1.1 "))
    assert "`WIP`" in row
    assert "external lead time" in row, "the trailing note was destroyed"


def test_validate_reports_a_row_it_cannot_parse(tmp_path: Path) -> None:
    copy = tmp_path / "tasks.md"
    copy.write_text(
        "**Status key**: `TODO` · `DONE`\n\n"
        "| S1.1.1 | fine | `TODO` |\n"
        "| S1.1.2 | status cell is malformed | TODO |\n",
        encoding="utf-8",
    )

    problems = tasks.validate(path=copy)

    assert any("did not parse" in p for p in problems), problems


def test_body_only_mention_does_not_advance(backlog_copy: Path) -> None:
    """Regression, found by dogfooding: a commit explaining *why* a test
    referenced S1.1.1 advanced it to WIP. Commit bodies discuss ids as prose."""
    story_id = _a_todo(backlog_copy)

    changes = tasks.advance_from_message(
        f"chore: tooling\n\nthe test hardcoded {story_id} as TODO, which broke", path=backlog_copy
    )

    assert changes == []
    assert _status(backlog_copy, story_id) == "TODO"


def test_subject_mention_still_advances(backlog_copy: Path) -> None:
    story_id = _a_todo(backlog_copy)

    changes = tasks.advance_from_message(
        f"feat: add thing ({story_id})\n\nsome body text", path=backlog_copy
    )

    assert changes == [(story_id, "TODO", "WIP")]


def test_close_in_body_still_closes(backlog_copy: Path) -> None:
    """Closing is explicit, so it counts anywhere — that's the conventional place."""
    story_id = _a_todo(backlog_copy)

    changes = tasks.advance_from_message(f"feat: finish it\n\ncloses {story_id}", path=backlog_copy)

    assert changes == [(story_id, "TODO", "DONE")]
