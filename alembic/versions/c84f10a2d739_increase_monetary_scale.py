"""Store BTC amounts, USD amounts, and prices with 10 decimal places.

Revision ID: c84f10a2d739
Revises: 95c6431702c6
"""

from alembic import op
import sqlalchemy as sa


revision = "c84f10a2d739"
down_revision = "95c6431702c6"
branch_labels = None
depends_on = None


# Preserve the existing number of whole-number digits as scale increases.
COLUMNS = {
    "companies": (("balance", 8, False), ("btc", 6, False)),
    "trades": (
        ("btc_amount", 6, False),
        ("entry_price", 2, False),
        ("entry_usd_amount", 8, False),
        ("exit_price", 2, True),
        ("exit_usd_amount", 8, True),
    ),
}


def upgrade() -> None:
    for table, columns in COLUMNS.items():
        with op.batch_alter_table(table) as batch_op:
            for column, scale, nullable in columns:
                batch_op.alter_column(
                    column,
                    existing_type=sa.Numeric(18, scale),
                    type_=sa.Numeric(18 + 10 - scale, 10),
                    existing_nullable=nullable,
                )


def downgrade() -> None:
    for table, columns in COLUMNS.items():
        with op.batch_alter_table(table) as batch_op:
            for column, scale, nullable in columns:
                batch_op.alter_column(
                    column,
                    existing_type=sa.Numeric(18 + 10 - scale, 10),
                    type_=sa.Numeric(18, scale),
                    existing_nullable=nullable,
                )
