"""align_enums_language

Revision ID: 003_align_enums_language
Revises: 002_add_reviews_consultation_id
Create Date: 2026-11-07 12:38:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_align_enums_language'
down_revision: Union[str, None] = '002_add_reviews_consultation_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

consultation_status_enum = sa.Enum('PENDING', 'CONFIRMED', 'COMPLETED', 'CANCELLED', name='consultation_status')
user_roles_enum = sa.Enum('USER', 'LAWYER', 'ADMIN', name='user_roles')

def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Create native enums in PostgreSQL if they do not exist
    if is_postgres:
        consultation_status_enum.create(bind, checkfirst=True)
        user_roles_enum.create(bind, checkfirst=True)

    # 2. Alter consultations.status to Enum
    if is_postgres:
        # Clear server default before type change in PG
        op.execute("ALTER TABLE consultations ALTER COLUMN status DROP DEFAULT;")
        op.alter_column(
            'consultations', 'status',
            existing_type=sa.VARCHAR(length=50),
            type_=consultation_status_enum,
            existing_nullable=False,
            postgresql_using="status::consultation_status"
        )
        op.execute("ALTER TABLE consultations ALTER COLUMN status SET DEFAULT 'PENDING'::consultation_status;")
    else:
        with op.batch_alter_table('consultations') as batch_op:
            batch_op.alter_column('status', existing_type=sa.VARCHAR(length=50), type_=consultation_status_enum, existing_nullable=False)

    # 3. Alter user_profiles.preferred_language to nullable=True
    if is_postgres:
        op.alter_column(
            'user_profiles', 'preferred_language',
            existing_type=sa.VARCHAR(length=50),
            nullable=True,
            existing_server_default=sa.text("'English'::character varying")
        )
    else:
        with op.batch_alter_table('user_profiles') as batch_op:
            batch_op.alter_column('preferred_language', existing_type=sa.VARCHAR(length=50), nullable=True)

    # 4. Alter users.role to Enum
    if is_postgres:
        op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT;")
        op.alter_column(
            'users', 'role',
            existing_type=sa.VARCHAR(length=50),
            type_=user_roles_enum,
            existing_nullable=False,
            postgresql_using="role::user_roles"
        )
        op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'USER'::user_roles;")
    else:
        with op.batch_alter_table('users') as batch_op:
            batch_op.alter_column('role', existing_type=sa.VARCHAR(length=50), type_=user_roles_enum, existing_nullable=False)

def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT;")
        op.alter_column(
            'users', 'role',
            existing_type=user_roles_enum,
            type_=sa.VARCHAR(length=50),
            existing_nullable=False,
            postgresql_using="role::character varying"
        )
        op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'USER'::character varying;")

        op.alter_column(
            'user_profiles', 'preferred_language',
            existing_type=sa.VARCHAR(length=50),
            nullable=False,
            existing_server_default=sa.text("'English'::character varying")
        )

        op.execute("ALTER TABLE consultations ALTER COLUMN status DROP DEFAULT;")
        op.alter_column(
            'consultations', 'status',
            existing_type=consultation_status_enum,
            type_=sa.VARCHAR(length=50),
            existing_nullable=False,
            postgresql_using="status::character varying"
        )
        op.execute("ALTER TABLE consultations ALTER COLUMN status SET DEFAULT 'PENDING'::character varying;")

        # Drop enum types in PG
        user_roles_enum.drop(bind, checkfirst=True)
        consultation_status_enum.drop(bind, checkfirst=True)
    else:
        with op.batch_alter_table('users') as batch_op:
            batch_op.alter_column('role', existing_type=user_roles_enum, type_=sa.VARCHAR(length=50), existing_nullable=False)
        with op.batch_alter_table('user_profiles') as batch_op:
            batch_op.alter_column('preferred_language', existing_type=sa.VARCHAR(length=50), nullable=False)
        with op.batch_alter_table('consultations') as batch_op:
            batch_op.alter_column('status', existing_type=consultation_status_enum, type_=sa.VARCHAR(length=50), existing_nullable=False)
