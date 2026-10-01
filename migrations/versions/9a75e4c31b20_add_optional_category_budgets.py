"""add optional category budgets

Revision ID: 9a75e4c31b20
Revises: 291678c335f0
Create Date: 2026-10-01 15:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9a75e4c31b20"
down_revision: Union[str, Sequence[str], None] = "291678c335f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "presupuestos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("categoria", sa.String(length=50), nullable=False),
        sa.Column("monto_maximo", sa.Float(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("usuario_id", "categoria", name="uq_presupuestos_usuario_categoria"),
    )
    op.create_index(op.f("ix_presupuestos_id"), "presupuestos", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_presupuestos_id"), table_name="presupuestos")
    op.drop_table("presupuestos")
