"""Add auth and user data isolation columns

Revision ID: 0002_add_auth
Revises: 0001_initial
Create Date: 2026-08-23
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_add_auth"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # 2. Add user_id column and foreign key to candidates
    with op.batch_alter_table("candidates", schema=None) as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_candidates_user", "users", ["user_id"], ["id"])

    # 3. Add user_id column and foreign key to job_descriptions
    with op.batch_alter_table("job_descriptions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_jobs_user", "users", ["user_id"], ["id"])

    # 4. Add user_id column and foreign key to screening_results
    with op.batch_alter_table("screening_results", schema=None) as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_screening_user", "users", ["user_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("screening_results", schema=None) as batch_op:
        batch_op.drop_constraint("fk_screening_user", type_="foreignkey")
        batch_op.drop_column("user_id")

    with op.batch_alter_table("job_descriptions", schema=None) as batch_op:
        batch_op.drop_constraint("fk_jobs_user", type_="foreignkey")
        batch_op.drop_column("user_id")

    with op.batch_alter_table("candidates", schema=None) as batch_op:
        batch_op.drop_constraint("fk_candidates_user", type_="foreignkey")
        batch_op.drop_column("user_id")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
