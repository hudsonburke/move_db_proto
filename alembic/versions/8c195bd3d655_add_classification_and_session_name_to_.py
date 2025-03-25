"""Add classification and session_name to C3DFile

Revision ID: 8c195bd3d655
Revises: 
Create Date: 2025-03-23 14:11:30.937269

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c195bd3d655'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('c3dfile')
    op.create_table('c3dfile',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('frame_count', sa.Integer(), nullable=False),
        sa.Column('sample_rate', sa.Float(), nullable=False),
        sa.Column('subject_name', sa.String(), nullable=False),
        sa.Column('classification', sa.String(), nullable=True),
        sa.Column('session_name', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('has_marker_data', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('has_analog_data', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('has_event_data', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('date_created', sa.DateTime(), nullable=False, server_default='2025-01-01 00:00:00'),
        sa.Column('date_modified', sa.DateTime(), nullable=False, server_default='2025-01-01 00:00:00'),
        sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('c3dfile', sa.Column('file_metadata', sa.VARCHAR(), nullable=False))
    op.add_column('c3dfile', sa.Column('date_added', sa.DATETIME(), nullable=False))
    op.add_column('c3dfile', sa.Column('filepath', sa.VARCHAR(), nullable=False))
    op.add_column('c3dfile', sa.Column('duration', sa.FLOAT(), nullable=False))
    op.alter_column('c3dfile', 'session_name',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('c3dfile', 'classification',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('c3dfile', 'subject_name',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.drop_column('c3dfile', 'description')
    op.drop_column('c3dfile', 'date_modified')
    op.drop_column('c3dfile', 'date_created')
    op.drop_column('c3dfile', 'has_event_data')
    op.drop_column('c3dfile', 'has_analog_data')
    op.drop_column('c3dfile', 'has_marker_data')
    # ### end Alembic commands ###
