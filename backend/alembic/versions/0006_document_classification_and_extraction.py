"""Document classification and field extraction

Revision ID: 0006_classification_extraction
Revises: 0005_document_ocr_pipeline
Create Date: 2026-10-30 07:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '0006_classification_extraction'
down_revision: Union[str, None] = '0005_document_ocr_pipeline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create document_classifications table
    op.create_table(
        'document_classifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('predicted_type', sa.String(length=50), nullable=False),
        sa.Column('score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('candidates_json', sa.JSON(), nullable=False),
        sa.Column('mismatch_flag', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('warning_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_document_classifications_id', 'document_classifications', ['id'], unique=False)
    op.create_index('ix_document_classifications_document_id', 'document_classifications', ['document_id'], unique=True)

    # 2. Create extracted_fields table
    op.create_table(
        'extracted_fields',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('normalized_value', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('page_no', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('bbox_json', sa.JSON(), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='rule'),
        sa.Column('needs_review', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('verified_by_user', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('corrected_value', sa.Text(), nullable=True),
        sa.Column('corrected_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['corrected_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_extracted_fields_id', 'extracted_fields', ['id'], unique=False)
    op.create_index('ix_extracted_fields_document_id', 'extracted_fields', ['document_id'], unique=False)
    op.create_index('ix_extracted_fields_key', 'extracted_fields', ['key'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_extracted_fields_key', table_name='extracted_fields')
    op.drop_index('ix_extracted_fields_document_id', table_name='extracted_fields')
    op.drop_index('ix_extracted_fields_id', table_name='extracted_fields')
    op.drop_table('extracted_fields')

    op.drop_index('ix_document_classifications_document_id', table_name='document_classifications')
    op.drop_index('ix_document_classifications_id', table_name='document_classifications')
    op.drop_table('document_classifications')

