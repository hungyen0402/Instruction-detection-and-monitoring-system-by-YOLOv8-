"""rename cooldown column

Revision ID: rename_cooldown_column
Revises: 
Create Date: 2024-03-19

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'rename_cooldown_column'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Đổi tên cột từ cooldown_minutes thành cooldown_seconds
    with op.batch_alter_table('alert_settings') as batch_op:
        batch_op.alter_column('cooldown_minutes',
                            new_column_name='cooldown_seconds',
                            existing_type=sa.Integer(),
                            existing_server_default=sa.text('5'))

def downgrade():
    # Đổi tên cột từ cooldown_seconds thành cooldown_minutes
    with op.batch_alter_table('alert_settings') as batch_op:
        batch_op.alter_column('cooldown_seconds',
                            new_column_name='cooldown_minutes',
                            existing_type=sa.Integer(),
                            existing_server_default=sa.text('5')) 