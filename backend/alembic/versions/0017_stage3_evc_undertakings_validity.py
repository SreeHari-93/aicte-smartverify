"""Stage 3: EVC, Undertakings, Document Validity and Alert Events

Revision ID: 0017_stage3_evc_undertakings_validity
Revises: 0016_workflow_module
Create Date: 2026-10-31 15:00:00.000000

"""
from typing import Sequence, Union
from datetime import datetime, timezone, timedelta, date
from alembic import op
import sqlalchemy as sa


revision: str = '0017_stage3_evc_undertakings_validity'
down_revision: Union[str, None] = '0016_workflow_module'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # 1. Alert Events
    if 'alert_events' not in existing_tables:
        op.create_table(
            'alert_events',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('event_type', sa.String(length=100), nullable=False),
            sa.Column('case_id', sa.String(length=100), nullable=False),
            sa.Column('recipient_role', sa.String(length=50), nullable=False),
            sa.Column('due_date', sa.DateTime(), nullable=True),
            sa.Column('offset_days', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('details', sa.JSON(), nullable=True),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
        )
        op.create_index('ix_alert_events_id', 'alert_events', ['id'])
        op.create_index('ix_alert_events_event_type', 'alert_events', ['event_type'])
        op.create_index('ix_alert_events_case_id', 'alert_events', ['case_id'])
        op.create_index('ix_alert_events_recipient_role', 'alert_events', ['recipient_role'])
        op.create_index('ix_alert_events_status', 'alert_events', ['status'])

    # 2. EVC Records
    if 'evc_records' not in existing_tables:
        op.create_table(
            'evc_records',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('application_id', sa.Integer(), sa.ForeignKey('applications.id', ondelete='CASCADE'), nullable=False),
            sa.Column('workflow_id', sa.Integer(), sa.ForeignKey('application_workflows.id', ondelete='CASCADE'), nullable=True),
            sa.Column('is_new_institution', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('committee_members', sa.JSON(), nullable=False),
            sa.Column('proposed_date', sa.DateTime(), nullable=True),
            sa.Column('confirmed_date', sa.DateTime(), nullable=True),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING_SCHEDULING'),
            sa.Column('report_file_path', sa.String(length=500), nullable=True),
            sa.Column('report_original_filename', sa.String(length=255), nullable=True),
            sa.Column('report_document_id', sa.Integer(), sa.ForeignKey('documents.id', ondelete='SET NULL'), nullable=True),
            sa.Column('report_uploaded_at', sa.DateTime(), nullable=True),
            sa.Column('remarks', sa.Text(), nullable=True),
            sa.Column('scheduling_deadline', sa.DateTime(), nullable=False),
            sa.Column('completion_deadline', sa.DateTime(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
        )
        op.create_index('ix_evc_records_id', 'evc_records', ['id'])
        op.create_index('ix_evc_records_application_id', 'evc_records', ['application_id'])
        op.create_index('ix_evc_records_workflow_id', 'evc_records', ['workflow_id'])
        op.create_index('ix_evc_records_confirmed_date', 'evc_records', ['confirmed_date'])
        op.create_index('ix_evc_records_status', 'evc_records', ['status'])

    # 3. Undertakings
    if 'undertakings' not in existing_tables:
        op.create_table(
            'undertakings',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('application_id', sa.Integer(), sa.ForeignKey('applications.id', ondelete='CASCADE'), nullable=False),
            sa.Column('institute_id', sa.Integer(), sa.ForeignKey('institutes.id', ondelete='CASCADE'), nullable=False),
            sa.Column('condition', sa.Text(), nullable=False),
            sa.Column('category', sa.String(length=50), nullable=False, server_default='other'),
            sa.Column('due_date', sa.DateTime(), nullable=False),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='ACTIVE'),
            sa.Column('evidence_file_path', sa.String(length=500), nullable=True),
            sa.Column('evidence_original_filename', sa.String(length=255), nullable=True),
            sa.Column('evidence_document_id', sa.Integer(), sa.ForeignKey('documents.id', ondelete='SET NULL'), nullable=True),
            sa.Column('evidence_remarks', sa.Text(), nullable=True),
            sa.Column('evidence_submitted_at', sa.DateTime(), nullable=True),
            sa.Column('history', sa.JSON(), nullable=False),
            sa.Column('created_by_officer_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('verification_reason', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
        )
        op.create_index('ix_undertakings_id', 'undertakings', ['id'])
        op.create_index('ix_undertakings_application_id', 'undertakings', ['application_id'])
        op.create_index('ix_undertakings_institute_id', 'undertakings', ['institute_id'])
        op.create_index('ix_undertakings_category', 'undertakings', ['category'])
        op.create_index('ix_undertakings_due_date', 'undertakings', ['due_date'])
        op.create_index('ix_undertakings_status', 'undertakings', ['status'])

    # 4. Document Validity Records
    if 'document_validity_records' not in existing_tables:
        op.create_table(
            'document_validity_records',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('document_id', sa.Integer(), sa.ForeignKey('documents.id', ondelete='SET NULL'), nullable=True),
            sa.Column('institute_id', sa.Integer(), sa.ForeignKey('institutes.id', ondelete='CASCADE'), nullable=False),
            sa.Column('application_id', sa.Integer(), sa.ForeignKey('applications.id', ondelete='SET NULL'), nullable=True),
            sa.Column('document_type_code', sa.String(length=50), nullable=False),
            sa.Column('document_name', sa.String(length=255), nullable=False),
            sa.Column('certificate_number', sa.String(length=100), nullable=True),
            sa.Column('issuing_authority', sa.String(length=255), nullable=True),
            sa.Column('issue_date', sa.Date(), nullable=True),
            sa.Column('expiry_date', sa.Date(), nullable=False),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='VALID'),
            sa.Column('days_left', sa.Integer(), nullable=True),
            sa.Column('expiring_soon_window_days', sa.Integer(), nullable=False, server_default='60'),
            sa.Column('renewal_document_id', sa.Integer(), sa.ForeignKey('documents.id', ondelete='SET NULL'), nullable=True),
            sa.Column('renewal_status', sa.String(length=50), nullable=True),
            sa.Column('renewal_submitted_at', sa.DateTime(), nullable=True),
            sa.Column('renewal_decision_reason', sa.Text(), nullable=True),
            sa.Column('renewal_decided_by_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('renewal_decided_at', sa.DateTime(), nullable=True),
            sa.Column('is_lease', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('lessor', sa.String(length=255), nullable=True),
            sa.Column('lessee', sa.String(length=255), nullable=True),
            sa.Column('lease_start', sa.Date(), nullable=True),
            sa.Column('lease_end', sa.Date(), nullable=True),
            sa.Column('property_address', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
        )
        op.create_index('ix_document_validity_records_id', 'document_validity_records', ['id'])
        op.create_index('ix_document_validity_records_document_id', 'document_validity_records', ['document_id'])
        op.create_index('ix_document_validity_records_institute_id', 'document_validity_records', ['institute_id'])
        op.create_index('ix_document_validity_records_application_id', 'document_validity_records', ['application_id'])
        op.create_index('ix_document_validity_records_document_type_code', 'document_validity_records', ['document_type_code'])
        op.create_index('ix_document_validity_records_expiry_date', 'document_validity_records', ['expiry_date'])
        op.create_index('ix_document_validity_records_status', 'document_validity_records', ['status'])
        op.create_index('ix_document_validity_records_is_lease', 'document_validity_records', ['is_lease'])


def downgrade() -> None:
    op.drop_table('document_validity_records')
    op.drop_table('undertakings')
    op.drop_table('evc_records')
    op.drop_table('alert_events')

