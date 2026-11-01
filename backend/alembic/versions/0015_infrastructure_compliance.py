"""Stage 6: Infrastructure compliance tables

Revision ID: 0015_infrastructure_compliance
Revises: 0014_stage9_evaluation_and_feedback
Create Date: 2026-10-30 19:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '0015_infrastructure_compliance'
down_revision: Union[str, None] = '0014_stage9_evaluation_and_feedback'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'infrastructure_details',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('institute_id', sa.Integer(), nullable=False),
        sa.Column('application_id', sa.Integer(), nullable=False),
        sa.Column('total_built_up_area', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('land_area', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('classroom_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('average_classroom_area', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('laboratory_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('library_area', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('library_books_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_sanctioned_intake', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('faculty_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('student_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('computers_available', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('internet_bandwidth_mbps', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('barrier_free_facilities', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('fire_safety_installed', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='DRAFT'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['institute_id'], ['institutes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('application_id')
    )
    with op.batch_alter_table('infrastructure_details', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_infrastructure_details_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_infrastructure_details_institute_id'), ['institute_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_infrastructure_details_application_id'), ['application_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_infrastructure_details_status'), ['status'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('infrastructure_details', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_infrastructure_details_status'))
        batch_op.drop_index(batch_op.f('ix_infrastructure_details_application_id'))
        batch_op.drop_index(batch_op.f('ix_infrastructure_details_institute_id'))
        batch_op.drop_index(batch_op.f('ix_infrastructure_details_id'))
    op.drop_table('infrastructure_details')

