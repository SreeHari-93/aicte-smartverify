"""Configurable rule engine document catalog and checklists

Revision ID: 0004_configurable_rule_engine
Revises: 0003_extend_rules_table
Create Date: 2026-10-30 05:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '0004_configurable_rule_engine'
down_revision: Union[str, None] = '0003_extend_rules_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. document_types
    op.create_table(
        'document_types',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('issuing_authority', sa.String(length=255), nullable=True),
        sa.Column('accepted_formats', sa.JSON(), nullable=False),
        sa.Column('max_size_mb', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('has_expiry', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('default_validity_months', sa.Integer(), nullable=False, server_default='12'),
        sa.Column('verification_method', sa.String(length=50), nullable=False, server_default='MANUAL'),
        sa.Column('extraction_schema', sa.JSON(), nullable=False),
        sa.Column('keywords', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_types_code'), 'document_types', ['code'], unique=True)
    op.create_index(op.f('ix_document_types_id'), 'document_types', ['id'], unique=False)

    # 2. application_categories
    op.create_table(
        'application_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_application_categories_code'), 'application_categories', ['code'], unique=True)
    op.create_index(op.f('ix_application_categories_id'), 'application_categories', ['id'], unique=False)

    # 3. checklist_items
    op.create_table(
        'checklist_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('document_type_id', sa.Integer(), nullable=False),
        sa.Column('is_mandatory', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('condition', sa.JSON(), nullable=True),
        sa.Column('min_validity_days_remaining', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('max_age_days', sa.Integer(), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('help_text', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['category_id'], ['application_categories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_type_id'], ['document_types.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_checklist_items_category_id'), 'checklist_items', ['category_id'], unique=False)
    op.create_index(op.f('ix_checklist_items_document_type_id'), 'checklist_items', ['document_type_id'], unique=False)
    op.create_index(op.f('ix_checklist_items_id'), 'checklist_items', ['id'], unique=False)

    # 4. Alter rules with batch mode for SQLite support
    with op.batch_alter_table('rules') as batch_op:
        batch_op.add_column(sa.Column('severity', sa.String(length=50), server_default='MAJOR', nullable=False))
        batch_op.add_column(sa.Column('applies_to_categories', sa.JSON(), server_default='[]', nullable=False))
        batch_op.add_column(sa.Column('definition', sa.JSON(), server_default='{}', nullable=False))
        batch_op.add_column(sa.Column('suggested_action', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('status', sa.String(length=50), server_default='PUBLISHED', nullable=False))
        batch_op.add_column(sa.Column('current_version', sa.Integer(), server_default='1', nullable=False))
        batch_op.add_column(sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False))
        batch_op.add_column(sa.Column('created_by', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('updated_by', sa.Integer(), nullable=True))

    # 5. rule_versions
    op.create_table(
        'rule_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rule_id', sa.Integer(), nullable=False),
        sa.Column('version_no', sa.Integer(), nullable=False),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.Column('change_note', sa.Text(), nullable=True),
        sa.Column('changed_by', sa.Integer(), nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['rule_id'], ['rules.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rule_versions_id'), 'rule_versions', ['id'], unique=False)
    op.create_index(op.f('ix_rule_versions_rule_id'), 'rule_versions', ['rule_id'], unique=False)

    # 6. rulesets
    op.create_table(
        'rulesets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('version_label', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PUBLISHED'),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('published_by', sa.Integer(), nullable=True),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rulesets_id'), 'rulesets', ['id'], unique=False)

    # 7. rule_change_requests
    op.create_table(
        'rule_change_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rule_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('proposed_payload', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('requested_by', sa.Integer(), nullable=False),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['rule_id'], ['rules.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rule_change_requests_id'), 'rule_change_requests', ['id'], unique=False)

    # 8. Add document_type_code and extracted_data to documents
    with op.batch_alter_table('documents') as batch_op:
        batch_op.add_column(sa.Column('document_type_code', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('extracted_data', sa.JSON(), server_default='{}', nullable=True))
        batch_op.create_index(batch_op.f('ix_documents_document_type_code'), ['document_type_code'], unique=False)

    # 9. Add details column to audit_logs
    with op.batch_alter_table('audit_logs') as batch_op:
        batch_op.add_column(sa.Column('details', sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('audit_logs') as batch_op:
        batch_op.drop_column('details')

    with op.batch_alter_table('documents') as batch_op:
        batch_op.drop_index(batch_op.f('ix_documents_document_type_code'))
        batch_op.drop_column('extracted_data')
        batch_op.drop_column('document_type_code')

    op.drop_table('rule_change_requests')
    op.drop_table('rulesets')
    op.drop_table('rule_versions')

    with op.batch_alter_table('rules') as batch_op:
        batch_op.drop_column('updated_by')
        batch_op.drop_column('created_by')
        batch_op.drop_column('is_active')
        batch_op.drop_column('current_version')
        batch_op.drop_column('status')
        batch_op.drop_column('suggested_action')
        batch_op.drop_column('definition')
        batch_op.drop_column('applies_to_categories')
        batch_op.drop_column('severity')

    op.drop_table('checklist_items')
    op.drop_table('application_categories')
    op.drop_table('document_types')

