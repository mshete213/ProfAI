"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("professor", "student", name="user_role"), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # Courses
    op.create_table(
        "courses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("style_instructions", sa.Text, nullable=True),
        sa.Column("professor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    # Enrollments
    op.create_table(
        "course_enrollments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("enrolled_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("student_id", "course_id", name="uq_enrollment_student_course"),
    )

    # Documents
    source_type_enum = sa.Enum("pdf", "pptx", "docx", "youtube", "drive", "canvas", name="source_type")
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("source_type", source_type_enum, nullable=False),
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column("content_hash", sa.String(128), nullable=False),
        sa.Column("chunk_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("ingested_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_documents_course_id", "documents", ["course_id"])
    op.create_index("ix_documents_content_hash", "documents", ["content_hash"])

    # Ingestion jobs
    op.create_table(
        "ingestion_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", source_type_enum, nullable=False),
        sa.Column(
            "status",
            sa.Enum("queued", "running", "completed", "failed", "skipped_duplicate", name="job_status"),
            nullable=False,
        ),
        sa.Column("total_items", sa.Integer, nullable=False, server_default="0"),
        sa.Column("processed_items", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failed_items", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("payload", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_ingestion_jobs_course_id", "ingestion_jobs", ["course_id"])

    # Chat sessions
    op.create_table(
        "chat_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_chat_sessions_course_id", "chat_sessions", ["course_id"])
    op.create_index("ix_chat_sessions_student_id", "chat_sessions", ["student_id"])

    # Chat messages
    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.Enum("user", "assistant", name="message_role"), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("sources", sa.JSON, nullable=True),
        sa.Column("tokens_used", sa.JSON, nullable=True),
        sa.Column("token_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])

    # Canvas connections
    op.create_table(
        "canvas_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("canvas_domain", sa.String(255), nullable=False),
        sa.Column("canvas_token_encrypted", sa.Text, nullable=False),
        sa.Column("canvas_course_id", sa.Integer, nullable=False),
        sa.Column(
            "sync_mode",
            sa.Enum("polling", "webhook", name="canvas_sync_mode"),
            nullable=False,
            server_default="polling",
        ),
        sa.Column("webhook_subscription_id", sa.String(255), nullable=True),
        sa.Column("webhook_compatible", sa.String(16), nullable=True),
        sa.Column("last_synced_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("course_id", name="uq_canvas_course"),
    )
    op.create_index("ix_canvas_connections_course_id", "canvas_connections", ["course_id"])


def downgrade() -> None:
    op.drop_table("canvas_connections")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("ingestion_jobs")
    op.drop_table("documents")
    op.drop_table("course_enrollments")
    op.drop_table("courses")
    op.drop_table("users")
    sa.Enum(name="canvas_sync_mode").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="message_role").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="job_status").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="source_type").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=False)
