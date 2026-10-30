"""Stage 8-ii: admin review workspaces, verification queue, anomalies, complaints, email outbox

Revision ID: 0012_stage8_admin_review_workspaces
Revises: 0011_stage8_admin_configurable_rules
Create Date: 2026-10-30 17:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '0012_stage8_admin_review_workspaces'
down_revision: Union[str, None] = '0011_stage8_admin_configurable_rules'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add priority and assigned_to to complaints
    with op.batch_alter_table('complaints') as batch_op:
        batch_op.add_column(sa.Column('priority', sa.String(length=50), server_default='MEDIUM', nullable=True))
        batch_op.add_column(sa.Column('assigned_to', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_complaints_assigned_to', 'users', ['assigned_to'], ['id'], ondelete='SET NULL')

    # 2. Add is_internal to complaint_events
    with op.batch_alter_table('complaint_events') as batch_op:
        batch_op.add_column(sa.Column('is_internal', sa.Boolean(), server_default='0', nullable=False))

    # 3. Add assigned_officer_id to documents
    with op.batch_alter_table('documents') as batch_op:
        batch_op.add_column(sa.Column('assigned_officer_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_documents_assigned_officer_id', 'users', ['assigned_officer_id'], ['id'], ondelete='SET NULL')

    # 4. Create email_outbox table
    op.create_table(
        'email_outbox',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('recipient', sa.String(length=255), nullable=False, index=True),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='queued (SMTP not configured)', nullable=False, index=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('email_outbox')

    with op.batch_alter_table('documents') as batch_op:
        batch_op.drop_constraint('fk_documents_assigned_officer_id', type_='foreignkey')
        batch_op.drop_column('assigned_officer_id')

    with op.batch_alter_table('complaint_events') as batch_op:
        batch_op.drop_column('is_internal')

    with op.batch_alter_table('complaints') as batch_op:
        batch_op.drop_constraint('fk_complaints_assigned_to', type_='foreignkey')
        batch_op.drop_column('assigned_to')
        batch_op.drop_column('priority')

