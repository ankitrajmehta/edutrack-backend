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
    # Create all enum types first (before first table that uses each)
    sa.Enum("admin", "ngo", "donor", "school", "student", name="userrole").create(
        op.get_bind()
    )
    sa.Enum("pending", "verified", "rejected", "blacklisted", name="ngostatus").create(
        op.get_bind()
    )
    sa.Enum("active", "completed", name="programstatus").create(op.get_bind())
    sa.Enum("pending", "verified", name="schoolstatus").create(op.get_bind())
    sa.Enum("active", "graduated", "blacklisted", name="studentstatus").create(
        op.get_bind()
    )
    sa.Enum("general", "program", "student", name="donationtype").create(op.get_bind())
    sa.Enum("pending", "approved", "rejected", name="invoicestatus").create(
        op.get_bind()
    )
    sa.Enum("pending", "accepted", "rejected", name="applicationstatus").create(
        op.get_bind()
    )
    sa.Enum(
        "donation",
        "invoice",
        "verify",
        "allocation",
        "program",
        "blacklist",
        name="activitytype",
    ).create(op.get_bind())

    # 1. users (no FKs)
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "admin",
                "ngo",
                "donor",
                "school",
                "student",
                name="userrole",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # 2. ngos (-> users)
    op.create_table(
        "ngos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("location", sa.String(255), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "verified",
                "rejected",
                "blacklisted",
                name="ngostatus",
                create_type=False,
            ),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("description", sa.String(2000), nullable=True),
        sa.Column("tax_doc", sa.String(500), nullable=True),
        sa.Column("reg_doc", sa.String(500), nullable=True),
        sa.Column("avatar", sa.String(500), nullable=True),
        sa.Column("color", sa.String(50), nullable=True),
        sa.Column(
            "total_funded", sa.Float(), nullable=False, server_default=sa.text("0.0")
        ),
        sa.Column(
            "students_helped", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "programs_count", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "registered_date",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_ngos_id", "ngos", ["id"])

    # 3. programs (-> ngos)
    op.create_table(
        "programs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ngo_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(2000), nullable=True),
        sa.Column(
            "status",
            sa.Enum("active", "completed", name="programstatus", create_type=False),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column(
            "categories", sa.JSON(), nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column(
            "total_budget", sa.Float(), nullable=False, server_default=sa.text("0.0")
        ),
        sa.Column(
            "allocated", sa.Float(), nullable=False, server_default=sa.text("0.0")
        ),
        sa.Column(
            "students_enrolled",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("start_date", sa.DateTime(), nullable=True),
        sa.Column("end_date", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["ngo_id"], ["ngos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_programs_id", "programs", ["id"])

    # 4. schools (-> users)
    op.create_table(
        "schools",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "verified", name="schoolstatus", create_type=False),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "students_in_programs",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "total_invoiced", sa.Float(), nullable=False, server_default=sa.text("0.0")
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_schools_id", "schools", ["id"])

    # 5. refresh_tokens (-> users)
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(512), nullable=False),
        sa.Column(
            "used", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_refresh_tokens_id", "refresh_tokens", ["id"])
    op.create_index("ix_refresh_tokens_token", "refresh_tokens", ["token"], unique=True)

    # 6. donors (-> users)
    op.create_table(
        "donors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column(
            "total_donated", sa.Float(), nullable=False, server_default=sa.text("0.0")
        ),
        sa.Column(
            "donations_count", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_donors_id", "donors", ["id"])

    # 7. students (-> ngos, programs)
    op.create_table(
        "students",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ngo_id", sa.Integer(), nullable=True),
        sa.Column("program_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("school", sa.String(255), nullable=True),
        sa.Column("grade", sa.String(50), nullable=True),
        sa.Column("guardian", sa.String(255), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("scholarship_id", sa.String(20), nullable=True),
        sa.Column("wallet_address", sa.String(100), nullable=True),
        sa.Column(
            "wallet_balance", sa.Float(), nullable=False, server_default=sa.text("0.0")
        ),
        sa.Column(
            "total_received", sa.Float(), nullable=False, server_default=sa.text("0.0")
        ),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "graduated",
                "blacklisted",
                name="studentstatus",
                create_type=False,
            ),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.ForeignKeyConstraint(["ngo_id"], ["ngos.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_students_id", "students", ["id"])
    op.create_index(
        "ix_students_scholarship_id", "students", ["scholarship_id"], unique=True
    )

    # 8. activity_logs (-> users)
    op.create_table(
        "activity_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "donation",
                "invoice",
                "verify",
                "allocation",
                "program",
                "blacklist",
                name="activitytype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "timestamp", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_activity_logs_id", "activity_logs", ["id"])

    # 9. file_records (-> users)
    op.create_table(
        "file_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("stored_path", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("uploaded_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_file_records_id", "file_records", ["id"])

    # 10. donations (-> donors, ngos, programs, students)
    op.create_table(
        "donations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("donor_id", sa.Integer(), nullable=False),
        sa.Column("ngo_id", sa.Integer(), nullable=False),
        sa.Column("program_id", sa.Integer(), nullable=True),
        sa.Column("student_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column(
            "date", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "type",
            sa.Enum(
                "general", "program", "student", name="donationtype", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("tx_hash", sa.String(128), nullable=True),
        sa.ForeignKeyConstraint(["donor_id"], ["donors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ngo_id"], ["ngos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_donations_id", "donations", ["id"])

    # 11. invoices (-> schools, ngos, programs)
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("ngo_id", sa.Integer(), nullable=False),
        sa.Column("program_id", sa.Integer(), nullable=True),
        sa.Column("school_name", sa.String(255), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "approved",
                "rejected",
                name="invoicestatus",
                create_type=False,
            ),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("items", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "date", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("approved_date", sa.DateTime(), nullable=True),
        sa.Column("supporting_doc", sa.String(500), nullable=True),
        sa.Column("tx_hash", sa.String(128), nullable=True),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ngo_id"], ["ngos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoices_id", "invoices", ["id"])

    # 12. scholarship_applications (-> programs)
    op.create_table(
        "scholarship_applications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("program_id", sa.Integer(), nullable=False),
        sa.Column("student_name", sa.String(255), nullable=False),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("grade", sa.String(50), nullable=True),
        sa.Column("school_name", sa.String(255), nullable=True),
        sa.Column("school_district", sa.String(255), nullable=True),
        sa.Column("guardian_name", sa.String(255), nullable=True),
        sa.Column("guardian_relation", sa.String(100), nullable=True),
        sa.Column("guardian_contact", sa.String(100), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "accepted",
                "rejected",
                name="applicationstatus",
                create_type=False,
            ),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "applied_date",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_scholarship_applications_id", "scholarship_applications", ["id"]
    )


def downgrade() -> None:
    # Drop tables in reverse order (12 -> 1)
    op.drop_table("scholarship_applications")
    op.drop_table("invoices")
    op.drop_table("donations")
    op.drop_table("file_records")
    op.drop_table("activity_logs")
    op.drop_table("students")
    op.drop_table("donors")
    op.drop_table("refresh_tokens")
    op.drop_table("schools")
    op.drop_table("programs")
    op.drop_table("ngos")
    op.drop_table("users")

    # Drop enum types in reverse dependency order
    sa.Enum(name="applicationstatus").drop(op.get_bind())
    sa.Enum(name="invoicestatus").drop(op.get_bind())
    sa.Enum(name="donationtype").drop(op.get_bind())
    sa.Enum(name="studentstatus").drop(op.get_bind())
    sa.Enum(name="activitytype").drop(op.get_bind())
    sa.Enum(name="schoolstatus").drop(op.get_bind())
    sa.Enum(name="programstatus").drop(op.get_bind())
    sa.Enum(name="ngostatus").drop(op.get_bind())
    sa.Enum(name="userrole").drop(op.get_bind())
