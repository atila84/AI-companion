"""Tests for the Alembic wiring (S1.1.2).

These guard the things that break quietly: a URL drifting out of sync with the
app's, a revision with no downgrade, and the constraint naming convention being
lost — which only shows up much later, when a downgrade cannot name the
constraint it needs to drop.

They are unit tests: no database is touched.
"""

import re
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from src.db import NAMING_CONVENTION, Base

BACKEND_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = BACKEND_ROOT / "alembic.ini"
VERSIONS_DIR = BACKEND_ROOT / "migrations" / "versions"


@pytest.fixture
def script_directory() -> ScriptDirectory:
    return ScriptDirectory.from_config(Config(str(ALEMBIC_INI)))


def test_alembic_config_exists() -> None:
    assert ALEMBIC_INI.is_file()
    assert (BACKEND_ROOT / "migrations" / "env.py").is_file()


def test_ini_does_not_hardcode_a_database_url() -> None:
    """alembic.ini is checked in, so a URL there is both a duplicate source of
    truth and a way to leak credentials into git."""
    active = [
        line
        for line in ALEMBIC_INI.read_text().splitlines()
        if line.strip().startswith("sqlalchemy.url")
    ]

    assert not active, f"alembic.ini sets sqlalchemy.url: {active}"


def test_env_reads_the_url_from_settings() -> None:
    """One source of truth — otherwise migrations can target a different
    database than the app, which is very hard to notice."""
    env = (BACKEND_ROOT / "migrations" / "env.py").read_text()

    assert "get_settings" in env
    assert "Base.metadata" in env


def test_revisions_form_a_single_chain(script_directory: ScriptDirectory) -> None:
    """Multiple heads mean someone branched and `upgrade head` becomes ambiguous."""
    heads = script_directory.get_heads()

    assert len(heads) == 1, f"expected one head, got {heads}"


def test_at_least_one_revision_exists(script_directory: ScriptDirectory) -> None:
    assert list(script_directory.walk_revisions())


def test_every_revision_has_a_downgrade() -> None:
    """A revision that cannot be undone makes the whole chain one-way."""
    missing = [
        path.name
        for path in VERSIONS_DIR.glob("*.py")
        if not re.search(r"def downgrade\(\)", path.read_text())
    ]

    assert not missing, f"revisions without a downgrade: {missing}"


def test_metadata_uses_the_naming_convention() -> None:
    """Autogenerate can only match constraints it can name. Changing this after
    tables exist renames every constraint, so it has to be right from the start."""
    assert Base.metadata.naming_convention == NAMING_CONVENTION


@pytest.mark.parametrize("key", ["ix", "uq", "ck", "fk", "pk"])
def test_naming_convention_covers_every_constraint_type(key: str) -> None:
    assert key in NAMING_CONVENTION
