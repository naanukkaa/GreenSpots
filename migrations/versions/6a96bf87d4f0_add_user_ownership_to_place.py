"""Add user ownership to Place

Revision ID: 6a96bf87d4f0
Revises: 
Create Date: 2026-01-15 17:33:12.922930

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6a96bf87d4f0'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('place', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('user_id', sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            'fk_place_user_id',
            'user',
            ['user_id'],
            ['id']
        )


def downgrade():
    with op.batch_alter_table('place', schema=None) as batch_op:
        batch_op.drop_constraint(
            'fk_place_user_id',
            type_='foreignkey'
        )
        batch_op.drop_column('user_id')

