"""listing provenance: source URL and retrieval date for imported real listings

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-20 14:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('properties') as batch:
        batch.add_column(sa.Column('source_url', sa.String(length=500), nullable=True))
        batch.add_column(sa.Column('source_retrieved_on', sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('properties') as batch:
        batch.drop_column('source_retrieved_on')
        batch.drop_column('source_url')
