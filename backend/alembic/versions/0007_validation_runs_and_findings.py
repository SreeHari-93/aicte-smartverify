"""Validation runs and findings tables

Revision ID: 0007_validation_runs_and_findings
Revises: 0006_classification_extraction
Create Date: 2026-10-30 07:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '0007_validation_runs_and_findings'
down_revision: Union[str, None] = '0006_classification_extraction'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create validation_runs table
    op.create_table(
        'validation_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('application_id', sa.Integer(), nullable=False),
        sa.Column('ruleset_id', sa.Integer(), nullable=True),
        sa.Column('ruleset_version', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='COMPLETED'),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('triggered_by', sa.Integer(), nullable=True),
        sa.Column('overall_status', sa.String(length=50), nullable=False),
        sa.Column('score', sa.Float(), nullable=False, server_default='100.0'),
        sa.Column('blocker_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('major_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('minor_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('advisory_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('diff_json', sa.JSON(), nullable=True),
        sa.Column('summary_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['ruleset_id'], ['rulesets.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['triggered_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_validation_runs_id', 'validation_runs', ['id'], unique=False)
    op.create_index('ix_validation_runs_application_id', 'validation_runs', ['application_id'], unique=False)
    op.create_index('ix_validation_runs_ruleset_id', 'validation_runs', ['ruleset_id'], unique=False)

    # 2. Create validation_findings table
    op.create_table(
        'validation_findings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('rule_code', sa.String(length=100), nullable=False),
        sa.Column('rule_version', sa.String(length=50), nullable=True),
        sa.Column('rule_title', sa.String(length=255), nullable=True),
        sa.Column('severity', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('evidence_json', sa.JSON(), nullable=False),
        sa.Column('suggested_action', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['validation_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_validation_findings_id', 'validation_findings', ['id'], unique=False)
    op.create_index('ix_validation_findings_run_id', 'validation_findings', ['run_id'], unique=False)
    op.create_index('ix_validation_findings_rule_code', 'validation_findings', ['rule_code'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_validation_findings_rule_code', table_name='validation_findings')
    op.drop_index('ix_validation_findings_run_id', table_name='validation_findings')
    op.drop_index('ix_validation_findings_id', table_name='validation_findings')
    op.drop_table('validation_findings')

    op.drop_index('ix_validation_runs_ruleset_id', table_name='validation_runs')
    op.drop_index('ix_validation_runs_application_id', table_name='validation_runs')
    op.drop_index('ix_validation_runs_id', table_name='validation_runs')
    op.drop_table('validation_runs')

