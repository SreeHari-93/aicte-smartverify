"""Stage 7: reports enhancement with application_id, language, and generated_by

Revision ID: 0013_stage7_reports_enhancement
Revises: 0012_stage8_admin_review_workspaces
Create Date: 2026-10-30 17:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '0013_stage7_reports_enhancement'
down_revision: Union[str, None] = '0012_stage8_admin_review_workspaces'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('reports') as batch_op:
        batch_op.add_column(sa.Column('application_id', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('language', sa.String(length=10), server_default='en', nullable=True))
        batch_op.add_column(sa.Column('generated_by', sa.String(length=100), server_default='INSTITUTE', nullable=True))
        batch_op.create_index('ix_reports_application_id', ['application_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('reports') as batch_op:
        batch_op.drop_index('ix_reports_application_id')
        batch_op.drop_column('generated_by')
        batch_op.drop_column('language')
        batch_op.drop_column('application_id')

