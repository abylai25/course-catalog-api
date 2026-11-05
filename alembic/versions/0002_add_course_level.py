"""add course level

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-30

Adds the required NOT NULL column `level` to the courses table.

A NOT NULL column cannot be added directly to a populated table because
PostgreSQL cannot assign a value to existing rows.  This migration uses the
standard three-step pattern:

  Step 1  Add the column as nullable so existing rows are valid (NULL).
  Step 2  Back-fill every existing row with a sensible default:
            - elective courses  → 'beginner'
            - non-elective courses → 'intermediate'
  Step 3  Enforce NOT NULL now that every row has a value.

Downgrade simply drops the column (level values are lost on rollback).
Run `alembic upgrade 0001:0002 --sql` to review the generated SQL before
applying.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1 – add nullable so existing rows pass the NOT NULL constraint.
    op.add_column("courses", sa.Column("level", sa.Text(), nullable=True))

    # Step 2 – back-fill existing rows before enforcing NOT NULL.
    op.execute(
        "UPDATE courses "
        "SET level = CASE WHEN is_elective THEN 'beginner' ELSE 'intermediate' END"
    )

    # Step 3 – now every row has a value; enforce NOT NULL.
    op.alter_column("courses", "level", nullable=False)


def downgrade() -> None:
    # Dropping the column is intentional: level values are not preserved on
    # rollback.  A production downgrade should archive them first.
    op.drop_column("courses", "level")
