"""add_c3dfile_analysis_link_table

Revision ID: 2b439025ea97
Revises: 570323dbc186
Create Date: 2025-03-24 03:36:33.137159

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b439025ea97'
down_revision: Union[str, None] = '570323dbc186'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the c3dfile_analysis_link table
    op.create_table(
        'c3dfile_analysis_link',
        sa.Column('c3dfile_id', sa.Integer, sa.ForeignKey('c3dfile.id'), primary_key=True),
        sa.Column('analysis_id', sa.Integer, sa.ForeignKey('analysis.id'), primary_key=True)
    )


def downgrade() -> None:
    # Drop the c3dfile_analysis_link table
    op.drop_table('c3dfile_analysis_link')
