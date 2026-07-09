"""Seed default categories.

Revision ID: 20260613_0002
Revises: 20260613_0001
Create Date: 2026-06-13
"""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from alembic import op

revision: str = "20260613_0002"
down_revision: str | Sequence[str] | None = "20260613_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_CATEGORIES = (
    ("00000000-0000-4000-8000-000000000001", "未分类", "暂未确定领域的知识", "#8A938D", 0),
    ("00000000-0000-4000-8000-000000000002", "生活", "生活经验与个人事务", "#B77945", 10),
    ("00000000-0000-4000-8000-000000000003", "工作", "工作资料与职业知识", "#176B4D", 20),
    ("00000000-0000-4000-8000-000000000004", "学习", "课程、阅读与学习资料", "#526EA6", 30),
)


def upgrade() -> None:
    categories = sa.table(
        "categories",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("color", sa.String()),
        sa.column("is_system", sa.Boolean()),
        sa.column("sort_order", sa.Integer()),
    )
    op.bulk_insert(
        categories,
        [
            {
                "id": category_id,
                "name": name,
                "description": description,
                "color": color,
                "is_system": True,
                "sort_order": sort_order,
            }
            for category_id, name, description, color, sort_order in DEFAULT_CATEGORIES
        ],
    )


def downgrade() -> None:
    categories = sa.table("categories", sa.column("id", sa.Uuid()))
    category_ids = [UUID(category_id) for category_id, *_ in DEFAULT_CATEGORIES]
    op.execute(categories.delete().where(categories.c.id.in_(category_ids)))
