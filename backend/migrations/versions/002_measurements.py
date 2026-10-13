"""Persist authorized measurements in the verification audit trail."""
from alembic import op
import sqlalchemy as sa
revision = '002'
down_revision = '001'


def upgrade():
    for name in ('eligible_original_price','measured_remaining_price','mandatory_fees'):
        op.add_column('verification_history', sa.Column(name, sa.Numeric(14,2), nullable=True))


def downgrade():
    for name in ('mandatory_fees','measured_remaining_price','eligible_original_price'):
        op.drop_column('verification_history', name)
