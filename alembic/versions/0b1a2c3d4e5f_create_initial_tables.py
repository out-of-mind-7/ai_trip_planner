
"""create initial tables"""

from alembic import op
import sqlalchemy as sa

revision = "0b1a2c3d4e5f"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "trips",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("city", sa.Text(), nullable=False),
        sa.Column("travellers", sa.Integer(), nullable=False),
        sa.Column("budget_of_a_person", sa.Integer(), nullable=False),
        sa.Column("days", sa.Integer(), nullable=False),

        sa.PrimaryKeyConstraint("id"),

        sa.CheckConstraint(
            "travellers >= 1",
            name="check_travellers_positive",
        ),
        sa.CheckConstraint(
            "days >= 1",
            name="check_days_positive",
        ),
        sa.CheckConstraint(
            "budget_of_a_person > 0",
            name="check_budget_positive",
        ),
    )

    op.create_table(
        "itinerary_days",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trip_id", sa.Uuid(), nullable=False),
        sa.Column("day_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),

        sa.PrimaryKeyConstraint("id"),

        sa.ForeignKeyConstraint(
            ["trip_id"],
            ["trips.id"],
        ),
    )


def downgrade():
    op.drop_table("itinerary_days")
    op.drop_table("trips")
