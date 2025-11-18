"""initial_schema

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create metadata_extract table
    op.create_table(
        'metadata_extract',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('metadata_id', sa.String(length=64), nullable=False),
        sa.Column('src_doc_name', sa.String(length=512), nullable=False),
        sa.Column('src_doc_path', sa.String(length=512), nullable=False),
        sa.Column('metadata_json', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='uploaded'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_metadata_extract_metadata_id'), 'metadata_extract', ['metadata_id'], unique=True)
    op.create_index(op.f('ix_metadata_extract_status'), 'metadata_extract', ['status'], unique=False)

    # Create ddl_generated table
    op.create_table(
        'ddl_generated',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('metadata_id', sa.Integer(), nullable=False),
        sa.Column('thread_id', sa.String(length=128), nullable=False),
        sa.Column('ddl_statement', sa.Text(), nullable=False),
        sa.Column('ddl_file_path', sa.String(length=512), nullable=True),
        sa.Column('validation_score', sa.Float(), nullable=True),
        sa.Column('accuracy_score', sa.Float(), nullable=True),
        sa.Column('validation_details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('feedback_iteration', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('user_feedback', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['metadata_id'], ['metadata_extract.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ddl_generated_metadata_id'), 'ddl_generated', ['metadata_id'], unique=False)
    op.create_index(op.f('ix_ddl_generated_thread_id'), 'ddl_generated', ['thread_id'], unique=False)
    op.create_index(op.f('ix_ddl_generated_status'), 'ddl_generated', ['status'], unique=False)

    # Create testdata_generated table
    op.create_table(
        'testdata_generated',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('metadata_id', sa.Integer(), nullable=False),
        sa.Column('ddl_id', sa.Integer(), nullable=True),
        sa.Column('thread_id', sa.String(length=128), nullable=False),
        sa.Column('file_path', sa.String(length=512), nullable=True),
        sa.Column('synthetic_json', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('row_count', sa.Integer(), nullable=True),
        sa.Column('data_type', sa.String(length=32), nullable=True),
        sa.Column('validation_score', sa.Float(), nullable=True),
        sa.Column('validation_details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('feedback_iteration', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('user_feedback', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['ddl_id'], ['ddl_generated.id'], ),
        sa.ForeignKeyConstraint(['metadata_id'], ['metadata_extract.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_testdata_generated_metadata_id'), 'testdata_generated', ['metadata_id'], unique=False)
    op.create_index(op.f('ix_testdata_generated_ddl_id'), 'testdata_generated', ['ddl_id'], unique=False)
    op.create_index(op.f('ix_testdata_generated_thread_id'), 'testdata_generated', ['thread_id'], unique=False)
    op.create_index(op.f('ix_testdata_generated_status'), 'testdata_generated', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_testdata_generated_status'), table_name='testdata_generated')
    op.drop_index(op.f('ix_testdata_generated_thread_id'), table_name='testdata_generated')
    op.drop_index(op.f('ix_testdata_generated_ddl_id'), table_name='testdata_generated')
    op.drop_index(op.f('ix_testdata_generated_metadata_id'), table_name='testdata_generated')
    op.drop_table('testdata_generated')

    op.drop_index(op.f('ix_ddl_generated_status'), table_name='ddl_generated')
    op.drop_index(op.f('ix_ddl_generated_thread_id'), table_name='ddl_generated')
    op.drop_index(op.f('ix_ddl_generated_metadata_id'), table_name='ddl_generated')
    op.drop_table('ddl_generated')

    op.drop_index(op.f('ix_metadata_extract_status'), table_name='metadata_extract')
    op.drop_index(op.f('ix_metadata_extract_metadata_id'), table_name='metadata_extract')
    op.drop_table('metadata_extract')
