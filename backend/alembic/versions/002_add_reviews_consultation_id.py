"""add consultation_id to reviews table

Revision ID: 002_add_reviews_consultation_id
Revises: 001_initial_models
Create Date: 2026-11-01 18:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '002_add_reviews_consultation_id'
down_revision: Union[str, None] = '001_initial_models'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add consultation_id foreign key column to reviews
    op.add_column('reviews', sa.Column('consultation_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_reviews_consultation_id',
        'reviews', 'consultations',
        ['consultation_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_reviews_consultation_id', 'reviews', type_='foreignkey')
    op.drop_column('reviews', 'consultation_id')

