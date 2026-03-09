"""initial_schema

Create all 12 tables with foreign keys and indexes.

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
    # Create enum types — each in its own op.execute (asyncpg doesn't support multi-statement)
    # DO blocks make these idempotent if partially applied
    op.execute(
        "DO $$ BEGIN CREATE TYPE userrole AS ENUM ('admin', 'ngo', 'donor', 'school', 'student'); EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE ngostatus AS ENUM ('pending', 'verified', 'rejected', 'blacklisted'); EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE programstatus AS ENUM ('active', 'completed'); EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE schoolstatus AS ENUM ('pending', 'verified'); EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE studentstatus AS ENUM ('active', 'graduated', 'blacklisted'); EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE donationtype AS ENUM ('general', 'program', 'student'); EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE invoicestatus AS ENUM ('pending', 'approved', 'rejected'); EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE applicationstatus AS ENUM ('pending', 'accepted', 'rejected'); EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE activitytype AS ENUM ('donation', 'invoice', 'verify', 'allocation', 'program', 'blacklist'); EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )

    # 1. users
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            role userrole NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_id ON users (id)")

    # 2. ngos
    op.execute("""
        CREATE TABLE IF NOT EXISTS ngos (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            location VARCHAR(255) NOT NULL,
            status ngostatus NOT NULL DEFAULT 'pending',
            description VARCHAR(2000),
            tax_doc VARCHAR(500),
            reg_doc VARCHAR(500),
            avatar VARCHAR(500),
            color VARCHAR(50),
            total_funded FLOAT NOT NULL DEFAULT 0.0,
            students_helped INTEGER NOT NULL DEFAULT 0,
            programs_count INTEGER NOT NULL DEFAULT 0,
            registered_date TIMESTAMP NOT NULL DEFAULT now(),
            UNIQUE (user_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_ngos_id ON ngos (id)")

    # 3. programs
    op.execute("""
        CREATE TABLE IF NOT EXISTS programs (
            id SERIAL PRIMARY KEY,
            ngo_id INTEGER NOT NULL REFERENCES ngos(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            description VARCHAR(2000),
            status programstatus NOT NULL DEFAULT 'active',
            categories JSON NOT NULL DEFAULT '[]',
            total_budget FLOAT NOT NULL DEFAULT 0.0,
            allocated FLOAT NOT NULL DEFAULT 0.0,
            students_enrolled INTEGER NOT NULL DEFAULT 0,
            start_date TIMESTAMP,
            end_date TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_programs_id ON programs (id)")

    # 4. schools
    op.execute("""
        CREATE TABLE IF NOT EXISTS schools (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            location VARCHAR(255),
            status schoolstatus NOT NULL DEFAULT 'pending',
            students_in_programs INTEGER NOT NULL DEFAULT 0,
            total_invoiced FLOAT NOT NULL DEFAULT 0.0,
            UNIQUE (user_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_schools_id ON schools (id)")

    # 5. refresh_tokens
    op.execute("""
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token VARCHAR(512) NOT NULL,
            used BOOLEAN NOT NULL DEFAULT false,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_refresh_tokens_token ON refresh_tokens (token)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_refresh_tokens_id ON refresh_tokens (id)")

    # 6. donors
    op.execute("""
        CREATE TABLE IF NOT EXISTS donors (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL,
            total_donated FLOAT NOT NULL DEFAULT 0.0,
            donations_count INTEGER NOT NULL DEFAULT 0,
            UNIQUE (user_id),
            UNIQUE (email)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_donors_id ON donors (id)")

    # 7. students
    op.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id SERIAL PRIMARY KEY,
            ngo_id INTEGER REFERENCES ngos(id) ON DELETE SET NULL,
            program_id INTEGER REFERENCES programs(id) ON DELETE SET NULL,
            name VARCHAR(255) NOT NULL,
            age INTEGER,
            school VARCHAR(255),
            grade VARCHAR(50),
            guardian VARCHAR(255),
            location VARCHAR(255),
            scholarship_id VARCHAR(20),
            wallet_address VARCHAR(100),
            wallet_balance FLOAT NOT NULL DEFAULT 0.0,
            total_received FLOAT NOT NULL DEFAULT 0.0,
            status studentstatus NOT NULL DEFAULT 'active'
        )
    """)
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_students_scholarship_id ON students (scholarship_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_students_id ON students (id)")

    # 8. activity_logs
    op.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            id SERIAL PRIMARY KEY,
            type activitytype NOT NULL,
            text TEXT NOT NULL,
            timestamp TIMESTAMP NOT NULL DEFAULT now(),
            actor_id INTEGER REFERENCES users(id) ON DELETE SET NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_activity_logs_id ON activity_logs (id)")

    # 9. file_records
    op.execute("""
        CREATE TABLE IF NOT EXISTS file_records (
            id SERIAL PRIMARY KEY,
            original_name VARCHAR(255) NOT NULL,
            stored_path VARCHAR(500) NOT NULL,
            mime_type VARCHAR(100),
            size_bytes BIGINT,
            uploaded_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_file_records_id ON file_records (id)")

    # 10. donations
    op.execute("""
        CREATE TABLE IF NOT EXISTS donations (
            id SERIAL PRIMARY KEY,
            donor_id INTEGER NOT NULL REFERENCES donors(id) ON DELETE CASCADE,
            ngo_id INTEGER NOT NULL REFERENCES ngos(id) ON DELETE CASCADE,
            program_id INTEGER REFERENCES programs(id) ON DELETE SET NULL,
            student_id INTEGER REFERENCES students(id) ON DELETE SET NULL,
            amount FLOAT NOT NULL,
            date TIMESTAMP NOT NULL DEFAULT now(),
            type donationtype NOT NULL,
            message TEXT,
            tx_hash VARCHAR(128)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_donations_id ON donations (id)")

    # 11. invoices
    op.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id SERIAL PRIMARY KEY,
            school_id INTEGER NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
            ngo_id INTEGER NOT NULL REFERENCES ngos(id) ON DELETE CASCADE,
            program_id INTEGER REFERENCES programs(id) ON DELETE SET NULL,
            school_name VARCHAR(255) NOT NULL,
            amount FLOAT NOT NULL,
            category VARCHAR(100) NOT NULL,
            status invoicestatus NOT NULL DEFAULT 'pending',
            items JSON NOT NULL DEFAULT '[]',
            date TIMESTAMP NOT NULL DEFAULT now(),
            approved_date TIMESTAMP,
            supporting_doc VARCHAR(500),
            tx_hash VARCHAR(128)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_invoices_id ON invoices (id)")

    # 12. scholarship_applications
    op.execute("""
        CREATE TABLE IF NOT EXISTS scholarship_applications (
            id SERIAL PRIMARY KEY,
            program_id INTEGER NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
            student_name VARCHAR(255) NOT NULL,
            age INTEGER,
            grade VARCHAR(50),
            school_name VARCHAR(255),
            school_district VARCHAR(255),
            guardian_name VARCHAR(255),
            guardian_relation VARCHAR(100),
            guardian_contact VARCHAR(100),
            reason TEXT,
            status applicationstatus NOT NULL DEFAULT 'pending',
            applied_date TIMESTAMP NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_scholarship_applications_id ON scholarship_applications (id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS scholarship_applications")
    op.execute("DROP TABLE IF EXISTS invoices")
    op.execute("DROP TABLE IF EXISTS donations")
    op.execute("DROP TABLE IF EXISTS file_records")
    op.execute("DROP TABLE IF EXISTS activity_logs")
    op.execute("DROP TABLE IF EXISTS students")
    op.execute("DROP TABLE IF EXISTS donors")
    op.execute("DROP TABLE IF EXISTS refresh_tokens")
    op.execute("DROP TABLE IF EXISTS schools")
    op.execute("DROP TABLE IF EXISTS programs")
    op.execute("DROP TABLE IF EXISTS ngos")
    op.execute("DROP TABLE IF EXISTS users")
    op.execute("DROP TYPE IF EXISTS applicationstatus")
    op.execute("DROP TYPE IF EXISTS invoicestatus")
    op.execute("DROP TYPE IF EXISTS donationtype")
    op.execute("DROP TYPE IF EXISTS studentstatus")
    op.execute("DROP TYPE IF EXISTS schoolstatus")
    op.execute("DROP TYPE IF EXISTS programstatus")
    op.execute("DROP TYPE IF EXISTS ngostatus")
    op.execute("DROP TYPE IF EXISTS activitytype")
    op.execute("DROP TYPE IF EXISTS userrole")
