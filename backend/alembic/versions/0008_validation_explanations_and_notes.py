"""Validation explanations and finding notes tables

Revision ID: 0008_validation_explanations_and_notes
Revises: 0007_validation_runs_and_findings
Create Date: 2026-10-30 08:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '0008_validation_explanations_and_notes'
down_revision: Union[str, None] = '0007_validation_runs_and_findings'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add waiver columns to validation_findings table
    with op.batch_alter_table('validation_findings') as batch_op:
        batch_op.add_column(sa.Column('is_waived', sa.Boolean(), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('waived_by', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('waiver_reason', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('waived_at', sa.DateTime(), nullable=True))
        batch_op.create_foreign_key('fk_validation_findings_waived_by_users', 'users', ['waived_by'], ['id'], ondelete='SET NULL')

    # 2. Create validation_explanations table
    op.create_table(
        'validation_explanations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('explanation_json', sa.JSON(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='TEMPLATE'),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('prompt_hash', sa.String(length=64), nullable=True),
        sa.Column('lang', sa.String(length=10), nullable=False, server_default='en'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['validation_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_validation_explanations_id', 'validation_explanations', ['id'], unique=False)
    op.create_index('ix_validation_explanations_run_id', 'validation_explanations', ['run_id'], unique=False)
    op.create_index('ix_validation_explanations_prompt_hash', 'validation_explanations', ['prompt_hash'], unique=False)

    # 3. Create finding_notes table
    op.create_table(
        'finding_notes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('finding_id', sa.Integer(), nullable=False),
        sa.Column('application_id', sa.Integer(), nullable=False),
        sa.Column('rule_code', sa.String(length=100), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=True),
        sa.Column('author_role', sa.String(length=50), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['finding_id'], ['validation_findings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_finding_notes_id', 'finding_notes', ['id'], unique=False)
    op.create_index('ix_finding_notes_finding_id', 'finding_notes', ['finding_id'], unique=False)
    op.create_index('ix_finding_notes_application_id', 'finding_notes', ['application_id'], unique=False)
    op.create_index('ix_finding_notes_rule_code', 'finding_notes', ['rule_code'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_finding_notes_rule_code', table_name='finding_notes')
    op.drop_index('ix_finding_notes_application_id', table_name='finding_notes')
    op.drop_index('ix_finding_notes_finding_id', table_name='finding_notes')
    op.drop_index('ix_finding_notes_id', table_name='finding_notes')
    op.drop_table('finding_notes')

    op.drop_index('ix_validation_explanations_prompt_hash', table_name='validation_explanations')
    op.drop_index('ix_validation_explanations_run_id', table_name='validation_explanations')
    op.drop_index('ix_validation_explanations_id', table_name='validation_explanations')
    op.drop_table('validation_explanations')

    with op.batch_alter_table('validation_findings') as batch_op:
        batch_op.drop_constraint('fk_validation_findings_waived_by_users', type_='foreignkey')
        batch_op.drop_column('waived_at')
        batch_op.drop_column('waiver_reason')
        batch_op.drop_column('waived_by')
        batch_op.drop_column('is_waived')

