"""Invalidate extraction cache when the parser changes."""
from alembic import op
import sqlalchemy as sa
revision = '003'
down_revision = '002'


def upgrade():
    op.add_column('crawl_results', sa.Column('parser_version', sa.String(20), nullable=False, server_default='1.0'))


def downgrade():
    op.drop_column('crawl_results','parser_version')
