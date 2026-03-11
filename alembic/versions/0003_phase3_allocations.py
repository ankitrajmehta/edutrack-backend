"""phase3_allocations

Add allocations table for NGO fund allocation tracking.

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-09
"""

from typing import Sequence, Union
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS allocations (
            id SERIAL PRIMARY KEY,
            ngo_id INTEGER NOT NULL REFERENCES ngos(id) ON DELETE CASCADE,
            student_id INTEGER REFERENCES students(id) ON DELETE SET NULL,
            program_id INTEGER REFERENCES programs(id) ON DELETE SET NULL,
            amount FLOAT NOT NULL,
            date TIMESTAMP NOT NULL DEFAULT NOW(),
            tx_hash VARCHAR(128)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_allocations_id ON allocations (id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_allocations_ngo_id ON allocations (ngo_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_allocations_student_id ON allocations (student_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_allocations_program_id ON allocations (program_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_allocations_program_id")
    op.execute("DROP INDEX IF EXISTS ix_allocations_student_id")
    op.execute("DROP INDEX IF EXISTS ix_allocations_ngo_id")
    op.execute("DROP INDEX IF EXISTS ix_allocations_id")
    op.execute("DROP TABLE IF EXISTS allocations")
