"""Create MDM schema and tables

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.execute("CREATE SCHEMA IF NOT EXISTS mdm_meta")
    
    op.create_table(
        'mdm_users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, default='viewer'),
        sa.Column('allowed_entities', postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email'),
        schema='mdm_meta'
    )
    op.create_index(op.f('ix_mdm_users_username'), 'mdm_users', ['username'], unique=True, schema='mdm_meta')
    
    op.create_table(
        'mdm_schemas',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_code', sa.String(length=100), nullable=False),
        sa.Column('entity_name', sa.String(length=255), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.Column('json_schema', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=False),
        sa.Column('description', sa.String(length=1000)),
        sa.Column('created_by', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        schema='mdm_meta'
    )
    op.create_index(op.f('ix_mdm_schemas_entity_code'), 'mdm_schemas', ['entity_code'], unique=False, schema='mdm_meta')
    op.create_index(op.f('ix_mdm_schemas_is_active'), 'mdm_schemas', ['is_active'], unique=False, schema='mdm_meta')
    op.create_index('idx_entity_version', 'mdm_schemas', ['entity_code', 'version'], schema='mdm_meta')
    
    op.create_table(
        'mdm_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_code', sa.String(length=100), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), default=False),
        sa.Column('created_by', sa.String(length=100), nullable=False),
        sa.Column('updated_by', sa.String(length=100)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_mdm_records_entity_code'), 'mdm_records', ['entity_code'], unique=False)
    op.create_index(op.f('ix_mdm_records_is_deleted'), 'mdm_records', ['is_deleted'], unique=False)
    op.create_index('idx_entity_deleted', 'mdm_records', ['entity_code', 'is_deleted'])
    op.create_index('idx_data_gin', 'mdm_records', ['data'], using='gin')
    
    op.create_table(
        'mdm_record_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('record_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('payload_before', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('payload_after', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['record_id'], ['mdm_records.id'], )
    )
    op.create_index(op.f('ix_mdm_record_history_record_id'), 'mdm_record_history', ['record_id'], unique=False)
    op.create_index(op.f('ix_mdm_record_history_timestamp'), 'mdm_record_history', ['timestamp'], unique=False)
    
    op.create_table(
        'mdm_audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('entity_code', sa.String(length=100)),
        sa.Column('record_id', postgresql.UUID(as_uuid=True)),
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='mdm_meta'
    )
    op.create_index(op.f('ix_mdm_audit_log_event_type'), 'mdm_audit_log', ['event_type'], unique=False, schema='mdm_meta')
    op.create_index(op.f('ix_mdm_audit_log_timestamp'), 'mdm_audit_log', ['timestamp'], unique=False, schema='mdm_meta')


def downgrade():
    op.drop_table('mdm_audit_log', schema='mdm_meta')
    op.drop_table('mdm_record_history')
    op.drop_table('mdm_records')
    op.drop_table('mdm_schemas', schema='mdm_meta')
    op.drop_table('mdm_users', schema='mdm_meta')
    op.execute("DROP SCHEMA IF EXISTS mdm_meta")
