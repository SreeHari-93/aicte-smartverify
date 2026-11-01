"""Stage 4: Notification Rules, Escalation Matrix, Scheduler, and Alerts

Revision ID: 0018_stage4_alerts_escalations_scheduler
Revises: 0017_stage3_evc_undertakings_validity
Create Date: 2026-10-31 16:00:00.000000

"""
from typing import Sequence, Union
from datetime import datetime, timezone
from alembic import op
import sqlalchemy as sa


revision: str = '0018_stage4_alerts_escalations_scheduler'
down_revision: Union[str, None] = '0017_stage3_evc_undertakings_validity'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # 1. Update alert_events table with in-app message fields
    if 'alert_events' in existing_tables:
        cols = [c['name'] for c in inspector.get_columns('alert_events')]
        with op.batch_alter_table('alert_events', schema=None) as batch_op:
            if 'title' not in cols:
                batch_op.add_column(sa.Column('title', sa.String(length=255), nullable=True))
            if 'message' not in cols:
                batch_op.add_column(sa.Column('message', sa.Text(), nullable=True))
            if 'link' not in cols:
                batch_op.add_column(sa.Column('link', sa.String(length=255), nullable=True))
            if 'is_read' not in cols:
                batch_op.add_column(sa.Column('is_read', sa.Boolean(), nullable=False, server_default='0'))
            if 'institute_id' not in cols:
                batch_op.add_column(sa.Column('institute_id', sa.Integer(), nullable=True))
            if 'recipient_user_id' not in cols:
                batch_op.add_column(sa.Column('recipient_user_id', sa.Integer(), nullable=True))

    # 2. notification_rules
    if 'notification_rules' not in existing_tables:
        op.create_table(
            'notification_rules',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('event_type', sa.String(length=100), nullable=False),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('offsets_days', sa.JSON(), nullable=False),
            sa.Column('recipient_role', sa.String(length=50), nullable=False, server_default='INSTITUTE'),
            sa.Column('channel', sa.String(length=50), nullable=False, server_default='BOTH'),
            sa.Column('message_template', sa.Text(), nullable=False),
            sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
        )
        op.create_index('ix_notification_rules_id', 'notification_rules', ['id'])
        op.create_index('ix_notification_rules_event_type', 'notification_rules', ['event_type'], unique=True)

    # 3. escalation_matrix
    if 'escalation_matrix' not in existing_tables:
        op.create_table(
            'escalation_matrix',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('event_type', sa.String(length=100), nullable=False),
            sa.Column('level', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('days_overdue', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('designated_role', sa.String(length=50), nullable=False, server_default='REGIONAL_OFFICER'),
            sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
        )
        op.create_index('ix_escalation_matrix_id', 'escalation_matrix', ['id'])
        op.create_index('ix_escalation_matrix_event_type', 'escalation_matrix', ['event_type'])

    # 4. escalation_records
    if 'escalation_records' not in existing_tables:
        op.create_table(
            'escalation_records',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('case_id', sa.String(length=100), nullable=False),
            sa.Column('case_type', sa.String(length=50), nullable=False),
            sa.Column('event_type', sa.String(length=100), nullable=False),
            sa.Column('level', sa.Integer(), nullable=False),
            sa.Column('notified_role', sa.String(length=50), nullable=False),
            sa.Column('notified_user_email', sa.String(length=255), nullable=True),
            sa.Column('days_overdue', sa.Integer(), nullable=False),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='ACTIVE'),
            sa.Column('resolved_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
        )
        op.create_index('ix_escalation_records_id', 'escalation_records', ['id'])
        op.create_index('ix_escalation_records_case_id', 'escalation_records', ['case_id'])
        op.create_index('ix_escalation_records_case_type', 'escalation_records', ['case_type'])
        op.create_index('ix_escalation_records_status', 'escalation_records', ['status'])

    # 5. scheduler_run_logs
    if 'scheduler_run_logs' not in existing_tables:
        op.create_table(
            'scheduler_run_logs',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('run_at', sa.DateTime(), nullable=False),
            sa.Column('simulated_clock', sa.DateTime(), nullable=True),
            sa.Column('items_checked', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('alerts_created', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('escalations_triggered', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='SUCCESS'),
            sa.Column('duration_ms', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('details', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
        )
        op.create_index('ix_scheduler_run_logs_id', 'scheduler_run_logs', ['id'])

    # 6. system_settings
    if 'system_settings' not in existing_tables:
        op.create_table(
            'system_settings',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('key', sa.String(length=100), nullable=False),
            sa.Column('value', sa.Text(), nullable=True),
            sa.Column('description', sa.String(length=255), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
        )
        op.create_index('ix_system_settings_id', 'system_settings', ['id'])
        op.create_index('ix_system_settings_key', 'system_settings', ['key'], unique=True)


def downgrade() -> None:
    op.drop_table('system_settings')
    op.drop_table('scheduler_run_logs')
    op.drop_table('escalation_records')
    op.drop_table('escalation_matrix')
    op.drop_table('notification_rules')

