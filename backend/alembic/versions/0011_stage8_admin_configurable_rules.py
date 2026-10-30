"""Stage 8 configurable rules document types and checklists enhancements

Revision ID: 0011_stage8_admin_configurable_rules
Revises: 0010_anomaly_service
Create Date: 2026-10-30 16:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '0011_stage8_admin_configurable_rules'
down_revision: Union[str, None] = '0010_anomaly_service'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add authority_adapter and statutory_verification_applies to document_types
    with op.batch_alter_table('document_types') as batch_op:
        batch_op.add_column(sa.Column('authority_adapter', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('statutory_verification_applies', sa.Boolean(), server_default='0', nullable=True))

    # 2. Add institute_type, min_count, ruleset_id to checklist_items
    with op.batch_alter_table('checklist_items') as batch_op:
        batch_op.add_column(sa.Column('institute_type', sa.String(length=100), server_default='ALL', nullable=True))
        batch_op.add_column(sa.Column('min_count', sa.Integer(), server_default='1', nullable=False))
        batch_op.add_column(sa.Column('ruleset_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_checklist_items_ruleset_id', 'rulesets', ['ruleset_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    with op.batch_alter_table('checklist_items') as batch_op:
        batch_op.drop_constraint('fk_checklist_items_ruleset_id', type_='foreignkey')
        batch_op.drop_column('ruleset_id')
        batch_op.drop_column('min_count')
        batch_op.drop_column('institute_type')

    with op.batch_alter_table('document_types') as batch_op:
        batch_op.drop_column('statutory_verification_applies')
        batch_op.drop_column('authority_adapter')

