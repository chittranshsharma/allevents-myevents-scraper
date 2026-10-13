"""Initial schema. Metadata is frozen in schema_v1 for reproducible migration."""
from alembic import op
from migrations.schema_v1 import metadata

revision = '001'
down_revision = None


def upgrade():
    metadata.create_all(op.get_bind())


def downgrade():
    metadata.drop_all(op.get_bind())
