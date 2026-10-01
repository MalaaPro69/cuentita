"""store original investment currency and exchange rate

Revision ID: b72e4f5a91c3
Revises: a84f3c19d2e7
Create Date: 2026-10-01 17:12:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b72e4f5a91c3"
down_revision: Union[str, Sequence[str], None] = "a84f3c19d2e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("inversiones", sa.Column("moneda_inversion", sa.String(length=3), nullable=True))
    op.add_column("inversiones", sa.Column("monto_invertido_original", sa.Float(), nullable=True))
    op.add_column("inversiones", sa.Column("tipo_cambio_ars_usd", sa.Float(), nullable=True))

    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE inversiones "
            "SET moneda_inversion = 'USD', "
            "monto_invertido_original = monto_invertido, "
            "tipo_cambio_ars_usd = 1"
        )
    )

    with op.batch_alter_table("inversiones") as batch_op:
        batch_op.alter_column(
            "moneda_inversion",
            existing_type=sa.String(length=3),
            nullable=False,
            server_default="USD",
        )
        batch_op.alter_column(
            "monto_invertido_original",
            existing_type=sa.Float(),
            nullable=False,
            server_default="0",
        )
        batch_op.alter_column(
            "tipo_cambio_ars_usd",
            existing_type=sa.Float(),
            nullable=False,
            server_default="1",
        )


def downgrade() -> None:
    with op.batch_alter_table("inversiones") as batch_op:
        batch_op.drop_column("tipo_cambio_ars_usd")
        batch_op.drop_column("monto_invertido_original")
        batch_op.drop_column("moneda_inversion")
