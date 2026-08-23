"""Initial schema: candidates, job_descriptions, screening_results.

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-23
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_name", sa.String(length=200), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.Column("experience", sa.JSON(), nullable=False),
        sa.Column("education", sa.JSON(), nullable=False),
        sa.Column("resume_filename", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=10), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("parsed_data", sa.JSON(), nullable=False),
        sa.Column("parse_provider", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "job_descriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description_text", sa.Text(), nullable=False),
        sa.Column("requirements", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "screening_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "candidate_id", sa.Integer(), sa.ForeignKey("candidates.id"), nullable=False
        ),
        sa.Column(
            "job_description_id",
            sa.Integer(),
            sa.ForeignKey("job_descriptions.id"),
            nullable=False,
        ),
        sa.Column("match_score", sa.Float(), nullable=False),
        sa.Column("shortlisted", sa.Boolean(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("strengths", sa.JSON(), nullable=False),
        sa.Column("missing_skills", sa.JSON(), nullable=False),
        sa.Column("experience_alignment", sa.Text(), nullable=False),
        sa.Column("education_alignment", sa.Text(), nullable=False),
        sa.Column("recommendation", sa.String(length=40), nullable=False),
        sa.Column("confidence", sa.String(length=20), nullable=True),
        sa.Column("shortlist_threshold", sa.Float(), nullable=False),
        sa.Column("llm_provider", sa.String(length=20), nullable=False),
        sa.Column("llm_model", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("candidate_id", "job_description_id", name="uq_candidate_job"),
    )


def downgrade() -> None:
    op.drop_table("screening_results")
    op.drop_table("job_descriptions")
    op.drop_table("candidates")
