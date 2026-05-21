"""empty message

Revision ID: 551545ea69c6
Revises: 75930797f6f4
Create Date: 2026-04-21 10:21:49.802120

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '551545ea69c6'
down_revision = '75930797f6f4'
branch_labels = None
depends_on = None


def upgrade():
    # Drop old tables only if they exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if 'reward_points' in existing_tables:
        op.drop_table('reward_points')
    if 'reward_history' in existing_tables:
        op.drop_table('reward_history')

    with op.batch_alter_table('testimonial', schema=None) as batch_op:
        batch_op.add_column(sa.Column('rating', sa.Integer(), nullable=False, server_default='5'))
        batch_op.add_column(sa.Column('headline', sa.String(length=120), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('body', sa.Text(), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('product_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('order_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'))
        batch_op.add_column(sa.Column('admin_note', sa.String(length=300), nullable=True))
        batch_op.add_column(sa.Column('is_featured', sa.Boolean(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('display_name', sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column('moderated_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('moderated_by_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))
        batch_op.create_unique_constraint('unique_user_testimonial', ['user_id'])
        batch_op.create_foreign_key('fk_testimonial_product', 'product', ['product_id'], ['id'])
        batch_op.create_foreign_key('fk_testimonial_moderator', 'users', ['moderated_by_id'], ['id'])
        batch_op.create_foreign_key('fk_testimonial_order', 'order', ['order_id'], ['id'])
        batch_op.drop_column('is_approved')
        batch_op.drop_column('message')
        batch_op.drop_column('role')
        batch_op.drop_column('name')


def downgrade():
    with op.batch_alter_table('testimonial', schema=None) as batch_op:
        batch_op.add_column(sa.Column('name', sa.VARCHAR(length=100), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('role', sa.VARCHAR(length=100), nullable=True))
        batch_op.add_column(sa.Column('message', sa.TEXT(), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('is_approved', sa.BOOLEAN(), nullable=True))
        batch_op.drop_constraint('fk_testimonial_product', type_='foreignkey')
        batch_op.drop_constraint('fk_testimonial_moderator', type_='foreignkey')
        batch_op.drop_constraint('fk_testimonial_order', type_='foreignkey')
        batch_op.drop_constraint('unique_user_testimonial', type_='unique')
        batch_op.drop_column('updated_at')
        batch_op.drop_column('moderated_by_id')
        batch_op.drop_column('moderated_at')
        batch_op.drop_column('display_name')
        batch_op.drop_column('is_featured')
        batch_op.drop_column('admin_note')
        batch_op.drop_column('status')
        batch_op.drop_column('order_id')
        batch_op.drop_column('product_id')
        batch_op.drop_column('body')
        batch_op.drop_column('headline')
        batch_op.drop_column('rating')

    op.create_table('reward_history',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('user_id', sa.INTEGER(), nullable=False),
        sa.Column('points', sa.INTEGER(), nullable=False),
        sa.Column('reason', sa.VARCHAR(length=200), nullable=True),
        sa.Column('created_at', sa.DATETIME(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('reward_points',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('user_id', sa.INTEGER(), nullable=False),
        sa.Column('points', sa.INTEGER(), nullable=True),
        sa.Column('updated_at', sa.DATETIME(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )