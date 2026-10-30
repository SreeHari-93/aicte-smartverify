"""Verification service models: VerificationResult, AuthoritySource, MockRegisterEntry

Revision ID: 0009_verification_service
Revises: 0008_validation_explanations_and_notes
Create Date: 2026-10-30 11:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '0009_verification_service'
down_revision: Union[str, None] = '0008_validation_explanations_and_notes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create authority_sources table
    op.create_table(
        'authority_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('base_url', sa.String(length=255), nullable=False),
        sa.Column('auth_type', sa.String(length=50), nullable=False, server_default='NONE'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('env_secret_key', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_authority_sources_id', 'authority_sources', ['id'], unique=False)
    op.create_index('ix_authority_sources_name', 'authority_sources', ['name'], unique=True)

    # 2. Create mock_register_entries table
    op.create_table(
        'mock_register_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('authority', sa.String(length=100), nullable=False),
        sa.Column('certificate_number', sa.String(length=100), nullable=False),
        sa.Column('institute_name', sa.String(length=255), nullable=False),
        sa.Column('issue_date', sa.String(length=50), nullable=True),
        sa.Column('expiry_date', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='VALID'),
        sa.Column('data_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_mock_register_entries_id', 'mock_register_entries', ['id'], unique=False)
    op.create_index('ix_mock_register_entries_authority', 'mock_register_entries', ['authority'], unique=False)
    op.create_index('ix_mock_register_entries_certificate_number', 'mock_register_entries', ['certificate_number'], unique=False)

    # 3. Create verification_results table
    op.create_table(
        'verification_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('source_name', sa.String(length=255), nullable=False),
        sa.Column('source_ref', sa.String(length=255), nullable=True),
        sa.Column('checked_at', sa.DateTime(), nullable=False),
        sa.Column('details_json', sa.JSON(), nullable=False),
        sa.Column('response_hash', sa.String(length=64), nullable=True),
        sa.Column('triggered_by', sa.Integer(), nullable=True),
        sa.Column('manual_decision', sa.String(length=50), nullable=True),
        sa.Column('manual_reason', sa.Text(), nullable=True),
        sa.Column('manual_reviewed_by', sa.Integer(), nullable=True),
        sa.Column('manual_reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['triggered_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['manual_reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_verification_results_id', 'verification_results', ['id'], unique=False)
    op.create_index('ix_verification_results_document_id', 'verification_results', ['document_id'], unique=False)
    op.create_index('ix_verification_results_status', 'verification_results', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_verification_results_status', table_name='verification_results')
    op.drop_index('ix_verification_results_document_id', table_name='verification_results')
    op.drop_index('ix_verification_results_id', table_name='verification_results')
    op.drop_table('verification_results')

    op.drop_index('ix_mock_register_entries_certificate_number', table_name='mock_register_entries')
    op.drop_index('ix_mock_register_entries_authority', table_name='mock_register_entries')
    op.drop_index('ix_mock_register_entries_id', table_name='mock_register_entries')
    op.drop_table('mock_register_entries')

    op.drop_index('ix_authority_sources_name', table_name='authority_sources')
    op.drop_index('ix_authority_sources_id', table_name='authority_sources')
    op.drop_table('authority_sources')

