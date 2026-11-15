#!/usr/bin/env python3
"""Read and update the backlog in `product/tasks.md`.

Keeps the backlog honest: it is the single place story status changes, and the
same validations run here and in `backend/tests/unit/test_backlog.py`.

Deliberately **stdlib-only**, using `dataclasses` rather than Pydantic v2. This
is a narrow, intentional exception to the project standard: `scripts/hooks/commit-msg`
imports this module, and git hooks run with a bare environment where
`backend/.venv` may not exist (a fresh clone has none). Everything else about the
house style — full type annotations, Google-style docstrings — still applies.

Usage:
    python3 scripts/tasks.py next
    python3 scripts/tasks.py list --status TODO --epic 1
    python3 scripts/tasks.py show S1.1.1
    python3 scripts/tasks.py set S1.1.1 DONE
    python3 scripts/tasks.py check
    python3 scripts/tasks.py install-hooks
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TASKS_PATH = REPO_ROOT / "product" / "tasks.md"

#: Rows look like: ``| S1.1.1 | As a developer, … | `TODO` |``
#: Anchored to the line so prose tables elsewhere in the file are ignored.
ROW_PATTERN = re.compile(
    r"^\|\s*(?P<id>[SE]\d+(?:\.\d+)+)\s*\|\s*(?P<title>.+?)\s*\|"
    r"\s*`(?P<status>[A-Z]+)`(?P<note>[^|]*)\|$"
)

#: Anything *shaped* like a story row. Compared against ROW_PATTERN so a row the
#: strict parser silently skips is reported rather than quietly dropped -- a
#: story invisible to the tooling is exactly the rot this module exists to stop.
LOOSE_ROW_PATTERN = re.compile(r"^\|\s*[SE]\d+(?:\.\d+)+\s*\|")

#: The legend line that defines which statuses are legal.
LEGEND_PATTERN = re.compile(r"^\*\*Status key\*\*:\s*(?P<statuses>.+)$")

#: Any story/epic reference inside free text, e.g. a commit message.
STORY_PATTERN = re.compile(r"\b[SE]\d+(?:\.\d+)+\b")

#: An explicit statement that a story is finished. "Done" is a judgement, so it
#: is never inferred from a bare reference — only from one of these verbs.
CLOSE_PATTERN = re.compile(
    r"\b(?:close[sd]?|fixe[sd]?|fix|complete[sd]?|resolve[sd]?)\s+(?P<id>[SE]\d+(?:\.\d+)+)\b",
    re.IGNORECASE,
)

#: Statuses that mean "not currently actionable".
PARKED_STATUSES = frozenset({"BLOCKED", "DEFERRED", "DONE"})

#: Docs whose internal links are validated.
LINKED_DOCS = ("README.md", "product/product.md", "product/tasks.md")


@dataclass(frozen=True)
class Story:
    """One backlog row.

    Attributes:
        id: Story or epic identifier, e.g. `"S1.1.1"` or `"E0.3"`.
        title: The row's description cell.
        status: Current status marker, e.g. `"TODO"`.
        line_no: 1-based line number in the source file.
    """

    id: str
    title: str
    status: str
    line_no: int

    @property
    def epic(self) -> str:
        """The epic number this story belongs to, as a string."""
        return self.id[1:].split(".")[0]


class BacklogError(Exception):
    """Raised when the backlog file is missing, malformed, or inconsistent."""


def read_lines(path: Path = TASKS_PATH) -> list[str]:
    """Read the backlog file as a list of lines without trailing newlines.

    Args:
        path: Backlog file to read.

    Returns:
        The file's lines.

    Raises:
        BacklogError: The file does not exist.
    """
    if not path.is_file():
        raise BacklogError(f"Backlog not found at {path}")
    return path.read_text(encoding="utf-8").splitlines()


def parse_statuses(lines: list[str]) -> set[str]:
    """Extract the legal status markers from the file's legend line.

    The legend is the single source of truth — the allowed set is never
    duplicated in code, so adding a status to the file is enough.

    Args:
        lines: Lines of the backlog file.

    Returns:
        The legal status markers.

    Raises:
        BacklogError: No legend line was found.
    """
    for line in lines:
        match = LEGEND_PATTERN.match(line)
        if match:
            return set(re.findall(r"`([A-Z]+)`", match.group("statuses")))
    raise BacklogError("No '**Status key**:' legend line found in the backlog")


def parse_stories(lines: list[str]) -> list[Story]:
    """Parse every story/epic row in the backlog.

    Args:
        lines: Lines of the backlog file.

    Returns:
        Stories in file order.
    """
    stories: list[Story] = []
    for index, line in enumerate(lines, start=1):
        match = ROW_PATTERN.match(line)
        if match:
            stories.append(
                Story(
                    id=match.group("id"),
                    title=match.group("title"),
                    status=match.group("status"),
                    line_no=index,
                )
            )
    return stories


def find_story(stories: list[Story], story_id: str) -> Story:
    """Look up one story by id.

    Args:
        stories: Parsed stories.
        story_id: Identifier to find, case-insensitive.

    Returns:
        The matching story.

    Raises:
        BacklogError: No story has that id.
    """
    wanted = story_id.upper()
    for story in stories:
        if story.id.upper() == wanted:
            return story
    raise BacklogError(f"No story with id {story_id!r}")


def set_status(story_id: str, status: str, path: Path = TASKS_PATH) -> Story:
    """Change one story's status in place, leaving every other byte untouched.

    Only the status cell of the matching row is rewritten, so the diff is
    always exactly one line.

    Args:
        story_id: Story to update.
        status: New status marker; must appear in the file's legend.
        path: Backlog file to update.

    Returns:
        The story as it now stands.

    Raises:
        BacklogError: The story or status is unknown.
    """
    lines = read_lines(path)
    legal = parse_statuses(lines)
    new_status = status.upper()
    if new_status not in legal:
        raise BacklogError(f"Unknown status {status!r}; expected one of {sorted(legal)}")

    story = find_story(parse_stories(lines), story_id)
    original = lines[story.line_no - 1]
    # Replace only the final status cell, preserving the rest of the row.
    updated = re.sub(r"`[A-Z]+`([^|]*\|)$", f"`{new_status}`\\1", original)
    if updated == original and story.status != new_status:  # pragma: no cover - defensive
        raise BacklogError(f"Could not rewrite status on line {story.line_no}")

    lines[story.line_no - 1] = updated
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return Story(id=story.id, title=story.title, status=new_status, line_no=story.line_no)


def advance_from_message(message: str, path: Path = TASKS_PATH) -> list[tuple[str, str, str]]:
    """Advance story statuses implied by a commit message.

    Two rules, both deliberately conservative:

    - A story referenced at all moves `TODO` -> `WIP`. Committing against a
      story is unambiguous evidence that work started.
    - A story moves to `DONE` only when the message says so explicitly
      ("closes S1.1.1", "fixes S1.1.1"). Finishing is a judgement no tool can
      make, and a false `DONE` is worse than a stale `TODO`.

    Anything already `BLOCKED` or `DEFERRED` is left alone — those are
    deliberate states, not staleness.

    Args:
        message: Full commit message.
        path: Backlog file to update.

    Returns:
        One `(id, old_status, new_status)` tuple per story actually changed.
    """
    try:
        stories = parse_stories(read_lines(path))
    except BacklogError:
        return []

    by_id = {s.id.upper(): s for s in stories}
    closed = {m.group("id").upper() for m in CLOSE_PATTERN.finditer(message)}
    referenced = {r.upper() for r in STORY_PATTERN.findall(message)}

    changes: list[tuple[str, str, str]] = []
    for story_id in sorted(referenced):
        story = by_id.get(story_id)
        if story is None:
            continue
        if story_id in closed:
            target = "DONE"
        elif story.status == "TODO":
            target = "WIP"
        else:
            continue
        if story.status == target:
            continue
        set_status(story.id, target, path=path)
        changes.append((story.id, story.status, target))
    return changes


def internal_links(doc: Path) -> list[str]:
    """Return the relative markdown links in a document, ignoring anchors.

    Args:
        doc: Markdown file to scan.

    Returns:
        Link targets as written in the file.
    """
    text = doc.read_text(encoding="utf-8")
    return [m for m in re.findall(r"\]\(([^)#]+\.md)\)", text) if "://" not in m]


def validate(path: Path = TASKS_PATH) -> list[str]:
    """Check the backlog and its sibling docs for rot.

    Args:
        path: Backlog file to validate.

    Returns:
        Human-readable problems; empty means everything is consistent.
    """
    problems: list[str] = []
    lines = read_lines(path)
    legal = parse_statuses(lines)
    stories = parse_stories(lines)

    if not stories:
        problems.append("No story rows parsed — the table format may be broken")

    parsed_lines = {s.line_no for s in stories}
    for index, line in enumerate(lines, start=1):
        if LOOSE_ROW_PATTERN.match(line) and index not in parsed_lines:
            problems.append(
                f"Line {index}: looks like a story row but did not parse, so it is "
                f"invisible to the backlog tooling: {line.strip()[:70]}"
            )

    seen: dict[str, int] = {}
    for story in stories:
        if story.id in seen:
            problems.append(
                f"Duplicate id {story.id} on lines {seen[story.id]} and {story.line_no}"
            )
        seen[story.id] = story.line_no
        if story.status not in legal:
            problems.append(
                f"Line {story.line_no}: {story.id} has status {story.status!r}, "
                f"not in the legend {sorted(legal)}"
            )

    for name in LINKED_DOCS:
        doc = REPO_ROOT / name
        if not doc.is_file():
            problems.append(f"Missing document: {name}")
            continue
        for link in internal_links(doc):
            if not (doc.parent / link).is_file():
                problems.append(f"{name}: broken link -> {link}")

    return problems


def done_without_commits(stories: list[Story]) -> list[Story]:
    """Find DONE stories with no commit referencing their id.

    Informational only — Epic 0 predates the commit convention, so this is
    never a hard failure.

    Args:
        stories: Parsed stories.

    Returns:
        DONE stories whose id appears in no commit message.
    """
    try:
        log = subprocess.run(
            ["git", "log", "--format=%s%n%b"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return [s for s in stories if s.status == "DONE" and s.id not in log]


def _cmd_list(args: argparse.Namespace) -> int:
    stories = parse_stories(read_lines())
    if args.status:
        stories = [s for s in stories if s.status == args.status.upper()]
    if args.epic:
        stories = [s for s in stories if s.epic == str(args.epic)]
    if not stories:
        print("No matching stories.")
        return 0
    for story in stories:
        print(f"{story.id:<8} {story.status:<9} {story.title}")
    return 0


def _cmd_next(args: argparse.Namespace) -> int:
    for story in parse_stories(read_lines()):
        if story.status not in PARKED_STATUSES:
            print(f"{story.id:<8} {story.status:<9} {story.title}")
            return 0
    print("Nothing actionable — every story is DONE, BLOCKED or DEFERRED.")
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    story = find_story(parse_stories(read_lines()), args.id)
    print(f"{story.id}  [{story.status}]  (line {story.line_no})")
    print(story.title)
    return 0


def _cmd_set(args: argparse.Namespace) -> int:
    story = set_status(args.id, args.status)
    print(f"{story.id} -> {story.status}")
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    problems = validate()
    for problem in problems:
        print(f"FAIL  {problem}")

    stale = done_without_commits(parse_stories(read_lines()))
    for story in stale:
        print(f"note  {story.id} is DONE but no commit references it")

    if problems:
        print(f"\n{len(problems)} problem(s).")
        return 1
    print("Backlog OK.")
    return 0


def _cmd_install_hooks(args: argparse.Namespace) -> int:
    subprocess.run(
        ["git", "config", "core.hooksPath", "scripts/hooks"],
        cwd=REPO_ROOT,
        check=True,
    )
    print("Hooks enabled: commit messages must reference a story id.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Returns:
        The configured parser.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="list stories")
    p_list.add_argument("--status", help="filter by status, e.g. TODO")
    p_list.add_argument("--epic", help="filter by epic number, e.g. 1")
    p_list.set_defaults(func=_cmd_list)

    sub.add_parser("next", help="show the next actionable story").set_defaults(func=_cmd_next)

    p_show = sub.add_parser("show", help="show one story")
    p_show.add_argument("id")
    p_show.set_defaults(func=_cmd_show)

    p_set = sub.add_parser("set", help="change a story's status")
    p_set.add_argument("id")
    p_set.add_argument("status")
    p_set.set_defaults(func=_cmd_set)

    sub.add_parser("check", help="validate the backlog").set_defaults(func=_cmd_check)
    sub.add_parser("install-hooks", help="enable the repo's git hooks").set_defaults(
        func=_cmd_install_hooks
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI.

    Args:
        argv: Argument list; defaults to `sys.argv[1:]`.

    Returns:
        Process exit code.
    """
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except BacklogError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
