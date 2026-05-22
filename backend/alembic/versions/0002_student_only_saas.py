"""student-only SaaS: drop professor role, add api_key, drop enrollments

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users: add api_key, drop role
    op.add_column("users", sa.Column("api_key", sa.String(255), nullable=True))
    op.create_index("ix_users_api_key", "users", ["api_key"], unique=True)
    op.drop_column("users", "role")
    sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=True)

    # Courses: rename professor_id -> owner_id
    op.alter_column("courses", "professor_id", new_column_name="owner_id")

    # Drop enrollments table
    op.drop_table("course_enrollments")


def downgrade() -> None:
    # Recreate enrollments
    op.create_table(
        "course_enrollments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "student_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "course_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("enrolled_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("student_id", "course_id", name="uq_enrollment_student_course"),
    )

    # Rename owner_id -> professor_id
    op.alter_column("courses", "owner_id", new_column_name="professor_id")

    # Re-add role column
    user_role = sa.Enum("professor", "student", name="user_role")
    user_role.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "users",
        sa.Column("role", user_role, nullable=False, server_default="student"),
    )

    # Drop api_key
    op.drop_index("ix_users_api_key", table_name="users")
    op.drop_column("users", "api_key")
