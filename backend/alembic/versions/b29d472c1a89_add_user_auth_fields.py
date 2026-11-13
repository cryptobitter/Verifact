"""add_user_auth_fields

Revision ID: b29d472c1a89
Revises: 434230f04867
Create Date: 2026-11-13 16:53:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b29d472c1a89'
down_revision: Union[str, Sequence[str], None] = '434230f04867'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Safely add columns if not already present
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('users')]

    if 'last_login_at' not in columns:
        op.add_column('users', sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True))
    if 'institution' not in columns:
        op.add_column('users', sa.Column('institution', sa.String(length=255), nullable=True))
    if 'license_number' not in columns:
        op.add_column('users', sa.Column('license_number', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'license_number')
    op.drop_column('users', 'institution')
    op.drop_column('users', 'last_login_at')
