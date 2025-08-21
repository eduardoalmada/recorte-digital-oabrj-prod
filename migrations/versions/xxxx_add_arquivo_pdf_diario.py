"""add arquivo_pdf to DiarioOficial

Revision ID: a1b2c3d4e5f6
Revises: 
Create Date: 2025-08-21 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# Revisão atual
revision = "a1b2c3d4e5f6"
down_revision = None  # coloca a última revision se já existir histórico
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "diarios_oficiais",
        sa.Column("arquivo_pdf", sa.String(), nullable=True)
    )


def downgrade():
    op.drop_column("diarios_oficiais", "arquivo_pdf")
