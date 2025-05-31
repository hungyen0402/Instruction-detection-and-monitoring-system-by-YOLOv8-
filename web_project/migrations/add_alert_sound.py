"""add alert sound column

Revision ID: add_alert_sound
Revises: 
Create Date: 2024-03-19

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_alert_sound'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Thêm cột alert_sound vào bảng camera
    op.add_column('camera', sa.Column('alert_sound', sa.String(128), nullable=True, server_default='alert.mp3'))

def downgrade():
    # Xóa cột alert_sound khỏi bảng camera
    op.drop_column('camera', 'alert_sound') 