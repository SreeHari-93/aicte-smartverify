"""Stage 9: evaluation runs and AI feedback tables

Revision ID: 0014_stage9_evaluation_and_feedback
Revises: 0013_stage7_reports_enhancement
Create Date: 2026-10-30 18:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '0014_stage9_evaluation_and_feedback'
down_revision: Union[str, None] = '0013_stage7_reports_enhancement'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. evaluation_runs table
    op.create_table(
        'evaluation_runs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('dataset_version', sa.String(length=50), server_default='v1.0', nullable=False),
        sa.Column('status', sa.String(length=50), server_default='COMPLETED', nullable=False),
        sa.Column('overall_accuracy', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('total_samples', sa.Integer(), server_default='0', nullable=False),
        sa.Column('passed_samples', sa.Integer(), server_default='0', nullable=False),
        sa.Column('metrics_json', sa.JSON(), nullable=False),
        sa.Column('failed_cases_json', sa.JSON(), nullable=False),
        sa.Column('git_commit', sa.String(length=40), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), server_default='0.0', nullable=False),
    )
    op.create_index('ix_evaluation_runs_id', 'evaluation_runs', ['id'], unique=False)
    op.create_index('ix_evaluation_runs_status', 'evaluation_runs', ['status'], unique=False)

    # 2. ai_feedback table
    op.create_table(
        'ai_feedback',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('target_type', sa.String(length=50), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), sa.ForeignKey('documents.id'), nullable=True),
        sa.Column('is_correct', sa.Boolean(), nullable=False),
        sa.Column('correction_notes', sa.Text(), nullable=True),
        sa.Column('feedback_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_ai_feedback_id', 'ai_feedback', ['id'], unique=False)
    op.create_index('ix_ai_feedback_user_id', 'ai_feedback', ['user_id'], unique=False)
    op.create_index('ix_ai_feedback_target_type', 'ai_feedback', ['target_type'], unique=False)
    op.create_index('ix_ai_feedback_target_id', 'ai_feedback', ['target_id'], unique=False)
    op.create_index('ix_ai_feedback_document_id', 'ai_feedback', ['document_id'], unique=False)
    op.create_index('ix_ai_feedback_created_at', 'ai_feedback', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('ai_feedback')
    op.drop_table('evaluation_runs')

