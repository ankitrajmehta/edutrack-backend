"""initial_schema

Create all 12 tables with foreign keys and indexes.

This migration was created without a live database connection.
After starting the database, run: alembic revision --autogenerate -m "initial_schema"
to regenerate with proper table definitions.

Revision ID: 0001
Revises:
Create Date: 2026-03-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This migration will be regenerated with --autogenerate once DB is available
    # Tables to create:
    # - users (with email unique index)
    # - refresh_tokens (with token unique index, user_id FK)
    # - ngos (with user_id FK)
    # - programs (with ngo_id FK)
    # - students (with ngo_id FK, program_id FK, scholarship_id unique index)
    # - donors (with user_id FK, email unique index)
    # - donations (with donor_id, ngo_id, program_id, student_id FKs)
    # - invoices (with school_id, ngo_id, program_id FKs)
    # - schools (with user_id FK)
    # - scholarship_applications (with program_id FK)
    # - activity_logs (with actor_id FK)
    # - file_records (with uploaded_by FK)
    pass


def downgrade() -> None:
    pass
