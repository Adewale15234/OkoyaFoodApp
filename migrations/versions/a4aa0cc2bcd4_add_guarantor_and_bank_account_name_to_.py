"""Add guarantor, bank_account_name, and amount_of_salary to Worker

Revision ID: a4aa0cc2bcd4
Revises: 58a4d88e41f3
Create Date: 2025-09-27 19:24:39.743526
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a4aa0cc2bcd4'
down_revision = '58a4d88e41f3'
branch_labels = None
depends_on = None


def upgrade():
    """Add new columns to workers table."""
    with op.batch_alter_table('workers', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('amount_of_salary', sa.Integer(), nullable=False, server_default='0')
        )
        batch_op.add_column(
            sa.Column('guarantor', sa.String(length=100), nullable=False, server_default='Unknown')
        )
        batch_op.add_column(
            sa.Column('bank_account_name', sa.String(length=100), nullable=False, server_default='Unknown')
        )


def downgrade():
    """Remove columns from workers table."""
    with op.batch_alter_table('workers', schema=None) as batch_op:
        batch_op.drop_column('bank_account_name')
        batch_op.drop_column('guarantor')
        batch_op.drop_column('amount_of_salary')
