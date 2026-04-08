"""Alembic migration: Refactor activity log to structured table."""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "002_create_activity_log_table"
down_revision = "001_initial_users_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create activity_log table for structured logging."""
    op.create_table(
        'activity_log',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Create indexes for common queries
    op.create_index('ix_activity_log_user_id', 'activity_log', ['user_id'])
    op.create_index('ix_activity_log_timestamp', 'activity_log', ['timestamp'])
    op.create_index('ix_activity_log_action', 'activity_log', ['action'])
    op.create_index('ix_activity_log_username', 'activity_log', ['username'])


def downgrade() -> None:
    """Drop activity_log table."""
    op.drop_index('ix_activity_log_username', table_name='activity_log')
    op.drop_index('ix_activity_log_action', table_name='activity_log')
    op.drop_index('ix_activity_log_timestamp', table_name='activity_log')
    op.drop_index('ix_activity_log_user_id', table_name='activity_log')
    op.drop_table('activity_log')
