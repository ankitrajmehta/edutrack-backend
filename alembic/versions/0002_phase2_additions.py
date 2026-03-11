"""phase2_additions

Add color to activity_logs; rejection_reason + submitted_by_user_id to scholarship_applications.

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-09
"""

from typing import Sequence, Union
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add color column to activity_logs
    op.execute("ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS color VARCHAR(50)")
    # Add rejection_reason to scholarship_applications
    op.execute(
        "ALTER TABLE scholarship_applications ADD COLUMN IF NOT EXISTS rejection_reason TEXT"
    )
    # Add submitted_by_user_id FK to scholarship_applications
    op.execute(
        "ALTER TABLE scholarship_applications ADD COLUMN IF NOT EXISTS submitted_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL"
    )
    # Index for the new FK column for efficient student application filtering
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_scholarship_applications_submitted_by_user_id ON scholarship_applications (submitted_by_user_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_scholarship_applications_submitted_by_user_id")
    op.execute(
        "ALTER TABLE scholarship_applications DROP COLUMN IF EXISTS submitted_by_user_id"
    )
    op.execute(
        "ALTER TABLE scholarship_applications DROP COLUMN IF EXISTS rejection_reason"
    )
    op.execute("ALTER TABLE activity_logs DROP COLUMN IF EXISTS color")
