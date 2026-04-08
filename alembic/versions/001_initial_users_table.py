"""Alembic migration: Create initial users table schema."""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "001_initial_users_table"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial users table with all current columns."""
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False, server_default='user'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.current_timestamp()),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('active', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('activity_log', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email'),
    )
    
    # Create indexes for common queries
    op.create_index('ix_users_username', 'users', ['username'])
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_active', 'users', ['active'])


def downgrade() -> None:
    """Drop users table."""
    op.drop_table('users')
