"""Stage 10: AICTE Workflow Management Module

Revision ID: 0016_workflow_module
Revises: 0015_infrastructure_compliance
Create Date: 2026-10-31 10:00:00.000000

"""
from typing import Sequence, Union
from datetime import datetime, timezone, timedelta
from alembic import op
import sqlalchemy as sa


revision: str = '0016_workflow_module'
down_revision: Union[str, None] = '0015_infrastructure_compliance'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add region to users table if not exists
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    user_columns = [col['name'] for col in inspector.get_columns('users')]
    if 'region' not in user_columns:
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.add_column(sa.Column('region', sa.String(length=100), nullable=True))

    # 2. Create workflow_templates table
    op.create_table(
        'workflow_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    with op.batch_alter_table('workflow_templates', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_workflow_templates_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_workflow_templates_code'), ['code'], unique=True)

    # 3. Create workflow_template_stages table
    op.create_table(
        'workflow_template_stages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('stage_code', sa.String(length=50), nullable=False),
        sa.Column('stage_name', sa.String(length=150), nullable=False),
        sa.Column('responsible_role', sa.String(length=50), nullable=False),
        sa.Column('sla_days', sa.Integer(), nullable=False, server_default='7'),
        sa.Column('is_final_decision', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['template_id'], ['workflow_templates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('workflow_template_stages', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_workflow_template_stages_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_workflow_template_stages_template_id'), ['template_id'], unique=False)

    # 4. Create application_workflows table
    op.create_table(
        'application_workflows',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('application_id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('current_stage_id', sa.Integer(), nullable=True),
        sa.Column('current_stage_sequence', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('current_stage_name', sa.String(length=150), nullable=False),
        sa.Column('assigned_officer_id', sa.Integer(), nullable=True),
        sa.Column('assigned_officer_name', sa.String(length=150), nullable=True),
        sa.Column('region', sa.String(length=100), nullable=False, server_default='Southern'),
        sa.Column('stage_start', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('due_date', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='IN_PROGRESS'),
        sa.Column('final_decision', sa.String(length=50), nullable=True),
        sa.Column('final_decision_notes', sa.Text(), nullable=True),
        sa.Column('final_decision_by', sa.String(length=150), nullable=True),
        sa.Column('final_decision_at', sa.DateTime(), nullable=True),
        sa.Column('case_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['workflow_templates.id']),
        sa.ForeignKeyConstraint(['current_stage_id'], ['workflow_template_stages.id']),
        sa.ForeignKeyConstraint(['assigned_officer_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('application_id')
    )
    with op.batch_alter_table('application_workflows', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_application_workflows_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_application_workflows_application_id'), ['application_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_application_workflows_template_id'), ['template_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_application_workflows_region'), ['region'], unique=False)
        batch_op.create_index(batch_op.f('ix_application_workflows_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_application_workflows_assigned_officer_id'), ['assigned_officer_id'], unique=False)

    # 5. Create workflow_histories table
    op.create_table(
        'workflow_histories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workflow_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('from_stage', sa.String(length=150), nullable=True),
        sa.Column('to_stage', sa.String(length=150), nullable=True),
        sa.Column('performed_by_id', sa.Integer(), nullable=True),
        sa.Column('performed_by_role', sa.String(length=50), nullable=False),
        sa.Column('performed_by_name', sa.String(length=150), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['workflow_id'], ['application_workflows.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['performed_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('workflow_histories', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_workflow_histories_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_workflow_histories_workflow_id'), ['workflow_id'], unique=False)

    # 6. Seed the 4 initial templates
    workflow_templates = sa.table(
        'workflow_templates',
        sa.column('id', sa.Integer),
        sa.column('code', sa.String),
        sa.column('name', sa.String),
        sa.column('description', sa.Text),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime),
    )
    stages = sa.table(
        'workflow_template_stages',
        sa.column('id', sa.Integer),
        sa.column('template_id', sa.Integer),
        sa.column('sequence', sa.Integer),
        sa.column('stage_code', sa.String),
        sa.column('stage_name', sa.String),
        sa.column('responsible_role', sa.String),
        sa.column('sla_days', sa.Integer),
        sa.column('is_final_decision', sa.Boolean),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime),
    )

    now = datetime.now(timezone.utc)
    templates_data = [
        {"id": 1, "code": "ONLY_SCRUTINY", "name": "Standard Scrutiny Workflow", "description": "Desktop scrutiny and compliance verification by Regional Office."},
        {"id": 2, "code": "SCRUTINY_EVC", "name": "Scrutiny with Expert Visit Committee (EVC)", "description": "Desktop scrutiny followed by physical on-site Expert Visit Committee inspection."},
        {"id": 3, "code": "EVC_SAC_SHC", "name": "EVC with Standing Hearing and Appeal Committees", "description": "Expert inspection with quasi-judicial Standing Hearing (SHC) and Standing Appeal (SAC) review."},
        {"id": 4, "code": "ONLY_EVC", "name": "Fast-Track Expert Inspection (Only EVC)", "description": "Direct Expert Visit Committee inspection for specialized physical verifications."},
    ]
    for t in templates_data:
        op.bulk_insert(workflow_templates, [{**t, "created_at": now, "updated_at": now}])

    stages_data = [
        # ONLY_SCRUTINY (id: 1)
        {"template_id": 1, "sequence": 1, "stage_code": "SCRUTINY", "stage_name": "Scrutiny & Document Verification", "responsible_role": "REGIONAL_OFFICER", "sla_days": 7, "is_final_decision": False},
        {"template_id": 1, "sequence": 2, "stage_code": "RO_REVIEW", "stage_name": "Regional Officer Recommendation", "responsible_role": "REGIONAL_OFFICER", "sla_days": 5, "is_final_decision": False},
        {"template_id": 1, "sequence": 3, "stage_code": "FINAL_DECISION", "stage_name": "Bureau Final Approval Decision", "responsible_role": "BUREAU_OFFICER", "sla_days": 3, "is_final_decision": True},

        # SCRUTINY_EVC (id: 2)
        {"template_id": 2, "sequence": 1, "stage_code": "SCRUTINY", "stage_name": "Preliminary Scrutiny", "responsible_role": "REGIONAL_OFFICER", "sla_days": 7, "is_final_decision": False},
        {"template_id": 2, "sequence": 2, "stage_code": "EVC", "stage_name": "Expert Visit Committee (EVC) Inspection", "responsible_role": "COMMITTEE_MEMBER", "sla_days": 10, "is_final_decision": False},
        {"template_id": 2, "sequence": 3, "stage_code": "RC_REVIEW", "stage_name": "Regional Committee Evaluation", "responsible_role": "REGIONAL_OFFICER", "sla_days": 5, "is_final_decision": False},
        {"template_id": 2, "sequence": 4, "stage_code": "FINAL_DECISION", "stage_name": "Competent Authority Decision", "responsible_role": "BUREAU_OFFICER", "sla_days": 5, "is_final_decision": True},

        # EVC_SAC_SHC (id: 3)
        {"template_id": 3, "sequence": 1, "stage_code": "EVC", "stage_name": "Expert Visit Committee (EVC)", "responsible_role": "COMMITTEE_MEMBER", "sla_days": 10, "is_final_decision": False},
        {"template_id": 3, "sequence": 2, "stage_code": "SHC", "stage_name": "Standing Hearing Committee (SHC)", "responsible_role": "COMMITTEE_MEMBER", "sla_days": 7, "is_final_decision": False},
        {"template_id": 3, "sequence": 3, "stage_code": "SAC", "stage_name": "Standing Appeal Committee (SAC)", "responsible_role": "COMMITTEE_MEMBER", "sla_days": 7, "is_final_decision": False},
        {"template_id": 3, "sequence": 4, "stage_code": "FINAL_DECISION", "stage_name": "Executive Council Final Decision", "responsible_role": "BUREAU_OFFICER", "sla_days": 5, "is_final_decision": True},

        # ONLY_EVC (id: 4)
        {"template_id": 4, "sequence": 1, "stage_code": "EVC", "stage_name": "Expert Visit Committee (EVC) Inspection", "responsible_role": "COMMITTEE_MEMBER", "sla_days": 10, "is_final_decision": False},
        {"template_id": 4, "sequence": 2, "stage_code": "RO_EVAL", "stage_name": "Regional Officer Evaluation", "responsible_role": "REGIONAL_OFFICER", "sla_days": 5, "is_final_decision": False},
        {"template_id": 4, "sequence": 3, "stage_code": "FINAL_DECISION", "stage_name": "Bureau Competent Authority Decision", "responsible_role": "BUREAU_OFFICER", "sla_days": 3, "is_final_decision": True},
    ]
    for s in stages_data:
        op.bulk_insert(stages, [{**s, "created_at": now, "updated_at": now}])


def downgrade() -> None:
    op.drop_table('workflow_histories')
    op.drop_table('application_workflows')
    op.drop_table('workflow_template_stages')
    op.drop_table('workflow_templates')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('region')

