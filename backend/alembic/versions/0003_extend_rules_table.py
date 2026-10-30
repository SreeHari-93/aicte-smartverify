"""Extend rules table with type, ai_checks, evidence, applies_to, version_history and updated_at

Revision ID: 0003_extend_rules_table
Revises: 0002_step2_institute_portal_tables
Create Date: 2026-10-30 04:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '0003_extend_rules_table'
down_revision: Union[str, None] = '0002_step2_institute_portal_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to rules table
    with op.batch_alter_table('rules') as batch_op:
        batch_op.add_column(sa.Column('rule_type', sa.String(length=20), server_default='MANDATORY', nullable=False))
        batch_op.add_column(sa.Column('ai_checks', sa.JSON(), server_default='[]', nullable=False))
        batch_op.add_column(sa.Column('evidence_required', sa.JSON(), server_default='[]', nullable=False))
        batch_op.add_column(sa.Column('applies_to', sa.JSON(), server_default='[]', nullable=False))
        batch_op.add_column(sa.Column('version_history', sa.JSON(), server_default='[]', nullable=False))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False))


def downgrade() -> None:
    with op.batch_alter_table('rules') as batch_op:
        batch_op.drop_column('updated_at')
        batch_op.drop_column('version_history')
        batch_op.drop_column('applies_to')
        batch_op.drop_column('evidence_required')
        batch_op.drop_column('ai_checks')
        batch_op.drop_column('rule_type')

