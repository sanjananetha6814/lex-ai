"""initial models migration

Revision ID: 001_initial_models
Revises: 
Create Date: 2026-10-30 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '001_initial_models'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='USER'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # 2. User Profiles
    op.create_table(
        'user_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('phone_number', sa.String(length=50), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('preferred_language', sa.String(length=50), nullable=False, server_default='English'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_user_profiles_id'), 'user_profiles', ['id'], unique=False)

    # 3. Lawyers
    op.create_table(
        'lawyers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('bar_council_id', sa.String(length=100), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('bar_council_id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_lawyers_city'), 'lawyers', ['city'], unique=False)
    op.create_index(op.f('ix_lawyers_id'), 'lawyers', ['id'], unique=False)
    op.create_index(op.f('ix_lawyers_name'), 'lawyers', ['name'], unique=False)

    # 4. Lawyer Profiles
    op.create_table(
        'lawyer_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lawyer_id', sa.Integer(), nullable=False),
        sa.Column('specialty', sa.String(length=255), nullable=False),
        sa.Column('experience_years', sa.String(length=50), nullable=False),
        sa.Column('consultation_fee', sa.String(length=50), nullable=False, server_default='₹1,500'),
        sa.Column('fee_number', sa.Integer(), nullable=False, server_default='1500'),
        sa.Column('languages', sa.String(length=255), nullable=False, server_default='English · Hindi'),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('practice_summary', sa.Text(), nullable=True),
        sa.Column('practice_areas', sa.JSON(), nullable=True),
        sa.Column('qualifications', sa.JSON(), nullable=True),
        sa.Column('availability_status', sa.String(length=100), nullable=False, server_default='Available Today'),
        sa.Column('next_slot', sa.String(length=100), nullable=False, server_default='Today at 4:00 PM'),
        sa.Column('rating', sa.Float(), nullable=False, server_default='4.9'),
        sa.Column('review_count', sa.String(length=50), nullable=False, server_default='120+'),
        sa.Column('initials', sa.String(length=10), nullable=False, server_default='AR'),
        sa.Column('tone', sa.String(length=20), nullable=False, server_default='sage'),
        sa.Column('slots', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['lawyer_id'], ['lawyers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lawyer_id')
    )
    op.create_index(op.f('ix_lawyer_profiles_id'), 'lawyer_profiles', ['id'], unique=False)
    op.create_index(op.f('ix_lawyer_profiles_specialty'), 'lawyer_profiles', ['specialty'], unique=False)

    # 5. Consultations
    op.create_table(
        'consultations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('reference_no', sa.String(length=50), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('lawyer_id', sa.Integer(), nullable=False),
        sa.Column('client_name', sa.String(length=255), nullable=False),
        sa.Column('client_email', sa.String(length=255), nullable=False),
        sa.Column('client_phone', sa.String(length=50), nullable=False),
        sa.Column('client_language', sa.String(length=50), nullable=False, server_default='English'),
        sa.Column('format', sa.String(length=50), nullable=False, server_default='video'),
        sa.Column('scheduled_date', sa.String(length=50), nullable=False),
        sa.Column('scheduled_slot', sa.String(length=50), nullable=False),
        sa.Column('issue_description', sa.Text(), nullable=False),
        sa.Column('is_urgent', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('fee', sa.String(length=50), nullable=False, server_default='₹1,500'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['lawyer_id'], ['lawyers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_consultations_id'), 'consultations', ['id'], unique=False)
    op.create_index(op.f('ix_consultations_lawyer_id'), 'consultations', ['lawyer_id'], unique=False)
    op.create_index(op.f('ix_consultations_reference_no'), 'consultations', ['reference_no'], unique=True)

    # 6. Documents
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('file_type', sa.String(length=100), nullable=True),
        sa.Column('storage_path', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PROCESSED'),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('risk_level', sa.String(length=50), nullable=False, server_default='LOW'),
        sa.Column('findings', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_documents_id'), 'documents', ['id'], unique=False)
    op.create_index(op.f('ix_documents_user_id'), 'documents', ['user_id'], unique=False)

    # 7. Conversations
    op.create_table(
        'conversations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False, server_default='New Legal Query'),
        sa.Column('language', sa.String(length=50), nullable=False, server_default='English'),
        sa.Column('is_saved', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conversations_id'), 'conversations', ['id'], unique=False)
    op.create_index(op.f('ix_conversations_user_id'), 'conversations', ['user_id'], unique=False)

    # 8. Messages
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('sources', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_messages_conversation_id'), 'messages', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_messages_id'), 'messages', ['id'], unique=False)

    # 9. Reviews
    op.create_table(
        'reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lawyer_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('client_name', sa.String(length=255), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('comment', sa.Text(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['lawyer_id'], ['lawyers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reviews_id'), 'reviews', ['id'], unique=False)
    op.create_index(op.f('ix_reviews_lawyer_id'), 'reviews', ['lawyer_id'], unique=False)

    # 10. Notifications
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False, server_default='INFO'),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_table('notifications')
    op.drop_table('reviews')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('documents')
    op.drop_table('consultations')
    op.drop_table('lawyer_profiles')
    op.drop_table('lawyers')
    op.drop_table('user_profiles')
    op.drop_table('users')
