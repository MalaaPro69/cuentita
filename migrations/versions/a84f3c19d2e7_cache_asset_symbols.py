"""cache asset symbols identified for investments

Revision ID: a84f3c19d2e7
Revises: 9a75e4c31b20
Create Date: 2026-10-01 16:45:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a84f3c19d2e7"
down_revision: Union[str, Sequence[str], None] = "9a75e4c31b20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "simbolos_activos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre_normalizado", sa.String(length=150), nullable=False),
        sa.Column("simbolo", sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "nombre_normalizado",
            name="uq_simbolos_activos_nombre_normalizado",
        ),
    )
    op.create_index(op.f("ix_simbolos_activos_id"), "simbolos_activos", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_simbolos_activos_id"), table_name="simbolos_activos")
    op.drop_table("simbolos_activos")
