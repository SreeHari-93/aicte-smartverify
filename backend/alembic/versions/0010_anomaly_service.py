"""Anomaly service models: AnomalyRun and AnomalyFlag

Revision ID: 0010_anomaly_service
Revises: 0009_verification_service
Create Date: 2026-10-30 13:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '0010_anomaly_service'
down_revision: Union[str, None] = '0009_verification_service'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create anomaly_runs table
    op.create_table(
        'anomaly_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('application_id', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('detectors_run', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_anomaly_runs_id', 'anomaly_runs', ['id'], unique=False)
    op.create_index('ix_anomaly_runs_document_id', 'anomaly_runs', ['document_id'], unique=False)
    op.create_index('ix_anomaly_runs_application_id', 'anomaly_runs', ['application_id'], unique=False)

    # 2. Create anomaly_flags table
    op.create_table(
        'anomaly_flags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('detector', sa.String(length=100), nullable=False),
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('evidence_json', sa.JSON(), nullable=False),
        sa.Column('confidence', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('recommended_action', sa.Text(), nullable=False),
        sa.Column('review_status', sa.String(length=50), server_default='OPEN', nullable=False),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('review_note', sa.Text(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('overlay_image_path', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['run_id'], ['anomaly_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_anomaly_flags_id', 'anomaly_flags', ['id'], unique=False)
    op.create_index('ix_anomaly_flags_run_id', 'anomaly_flags', ['run_id'], unique=False)
    op.create_index('ix_anomaly_flags_document_id', 'anomaly_flags', ['document_id'], unique=False)
    op.create_index('ix_anomaly_flags_detector', 'anomaly_flags', ['detector'], unique=False)
    op.create_index('ix_anomaly_flags_code', 'anomaly_flags', ['code'], unique=False)
    op.create_index('ix_anomaly_flags_review_status', 'anomaly_flags', ['review_status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_anomaly_flags_review_status', table_name='anomaly_flags')
    op.drop_index('ix_anomaly_flags_code', table_name='anomaly_flags')
    op.drop_index('ix_anomaly_flags_detector', table_name='anomaly_flags')
    op.drop_index('ix_anomaly_flags_document_id', table_name='anomaly_flags')
    op.drop_index('ix_anomaly_flags_run_id', table_name='anomaly_flags')
    op.drop_index('ix_anomaly_flags_id', table_name='anomaly_flags')
    op.drop_table('anomaly_flags')

    op.drop_index('ix_anomaly_runs_application_id', table_name='anomaly_runs')
    op.drop_index('ix_anomaly_runs_document_id', table_name='anomaly_runs')
    op.drop_index('ix_anomaly_runs_id', table_name='anomaly_runs')
    op.drop_table('anomaly_runs')

