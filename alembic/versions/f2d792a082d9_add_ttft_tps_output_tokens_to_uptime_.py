"""add ttft tps output_tokens to uptime_checks

Revision ID: f2d792a082d9
Revises: 02f5d910ae59
Create Date: 2026-02-04 03:31:51.221911

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2d792a082d9"
down_revision: Union[str, Sequence[str], None] = "02f5d910ae59"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add TTFT, TPS, and output_tokens columns to uptime_checks table.

    These columns enable meaningful performance comparisons across models:
    - ttft_ms: Time To First Token (responsiveness, comparable across models)
    - tps: Tokens Per Second (generation speed, normalized by token count)
    - output_tokens: Number of tokens generated (for verification)
    """
    op.add_column("uptime_checks", sa.Column("ttft_ms", sa.Float(), nullable=True))
    op.add_column("uptime_checks", sa.Column("tps", sa.Float(), nullable=True))
    op.add_column("uptime_checks", sa.Column("output_tokens", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Remove TTFT, TPS, and output_tokens columns from uptime_checks table."""
    op.drop_column("uptime_checks", "output_tokens")
    op.drop_column("uptime_checks", "tps")
    op.drop_column("uptime_checks", "ttft_ms")
