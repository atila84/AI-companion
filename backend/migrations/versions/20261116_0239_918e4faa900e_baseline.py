"""Baseline: establishes the alembic_version table.

Deliberately empty. The schema itself belongs to the feature stories that
need it (users to S1.2.1, companions and personas to S1.3.1, and so on);
this revision exists so those have a parent to build on and so
`alembic upgrade head` is meaningful on a fresh database.

Original name: baseline

Revision ID: 918e4faa900e
Revises: 
Create Date: 2026-11-16 02:39:21.609793

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '918e4faa900e'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
