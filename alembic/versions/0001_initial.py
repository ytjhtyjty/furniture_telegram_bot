"""initial schema (как её создавал create_all до Alembic)

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("firstname", sa.String(), nullable=True),
        sa.Column("lastname", sa.String(), nullable=True),
        sa.Column("registration_date", sa.DateTime(), nullable=True),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_categories_id", "categories", ["id"], unique=False)

    op.create_table(
        "furniture",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category_name", sa.String(), nullable=False),
        sa.Column("country_origin", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["category_name"], ["categories.name"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_furniture_id", "furniture", ["id"], unique=False)

    op.create_table(
        "furniture_photos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("furniture_id", sa.Integer(), nullable=False),
        sa.Column("file_id", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["furniture_id"], ["furniture.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_furniture_photos_id", "furniture_photos", ["id"], unique=False)

    op.create_table(
        "cooperations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("is_processed", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cooperations_id", "cooperations", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_cooperations_id", table_name="cooperations")
    op.drop_table("cooperations")
    op.drop_index("ix_furniture_photos_id", table_name="furniture_photos")
    op.drop_table("furniture_photos")
    op.drop_index("ix_furniture_id", table_name="furniture")
    op.drop_table("furniture")
    op.drop_index("ix_categories_id", table_name="categories")
    op.drop_table("categories")
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_table("users")
