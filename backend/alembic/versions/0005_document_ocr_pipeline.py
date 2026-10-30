"""Document OCR pipeline and document pages

Revision ID: 0005_document_ocr_pipeline
Revises: 0004_configurable_rule_engine
Create Date: 2026-10-30 06:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '0005_document_ocr_pipeline'
down_revision: Union[str, None] = '0004_configurable_rule_engine'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extend documents table
    with op.batch_alter_table('documents') as batch_op:
        batch_op.add_column(sa.Column('document_type_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('ocr_status', sa.String(length=50), nullable=False, server_default='PENDING'))
        batch_op.add_column(sa.Column('ocr_engine', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('ocr_confidence', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('page_count', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('language', sa.String(length=20), nullable=True, server_default='en'))
        batch_op.add_column(sa.Column('processed_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('error_message', sa.Text(), nullable=True))
        batch_op.create_foreign_key('fk_documents_document_type_id', 'document_types', ['document_type_id'], ['id'])
        batch_op.create_index('ix_documents_document_type_id', ['document_type_id'])

    # 2. Create document_pages table
    op.create_table(
        'document_pages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('page_no', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False, server_default=''),
        sa.Column('words_json', sa.JSON(), nullable=False),
        sa.Column('width', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('height', sa.Float(), nullable=False, server_default='0.0'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_document_pages_id', 'document_pages', ['id'], unique=False)
    op.create_index('ix_document_pages_document_id', 'document_pages', ['document_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_document_pages_document_id', table_name='document_pages')
    op.drop_index('ix_document_pages_id', table_name='document_pages')
    op.drop_table('document_pages')

    with op.batch_alter_table('documents') as batch_op:
        batch_op.drop_index('ix_documents_document_type_id')
        batch_op.drop_constraint('fk_documents_document_type_id', type_='foreignkey')
        batch_op.drop_column('error_message')
        batch_op.drop_column('processed_at')
        batch_op.drop_column('language')
        batch_op.drop_column('page_count')
        batch_op.drop_column('ocr_confidence')
        batch_op.drop_column('ocr_engine')
        batch_op.drop_column('ocr_status')
        batch_op.drop_column('document_type_id')

