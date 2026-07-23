"""assets inventory schema

Revision ID: 20260723_0002
Revises: 20260722_0001
Create Date: 2026-07-23 09:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260723_0002"
down_revision: str | None = "20260722_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("expected_hostname", sa.String(length=120), nullable=True),
        sa.Column("sector", sa.String(length=120), nullable=True),
        sa.Column("assigned_user", sa.String(length=160), nullable=True),
        sa.Column("patrimony_code", sa.String(length=80), nullable=True),
        sa.Column("equipment_type_model", sa.String(length=180), nullable=True),
        sa.Column("service_tag", sa.String(length=120), nullable=True),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("warranty_end_date", sa.Date(), nullable=True),
        sa.Column("monitor_description", sa.String(length=180), nullable=True),
        sa.Column("monitor_patrimony_code", sa.String(length=80), nullable=True),
        sa.Column("office_version", sa.String(length=120), nullable=True),
        sa.Column("office_activation_email", sa.String(length=180), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("expected_hostname"),
    )
    op.create_index(op.f("ix_assets_assigned_user"), "assets", ["assigned_user"], unique=False)
    op.create_index(op.f("ix_assets_expected_hostname"), "assets", ["expected_hostname"], unique=False)
    op.create_index(op.f("ix_assets_patrimony_code"), "assets", ["patrimony_code"], unique=False)
    op.create_index(op.f("ix_assets_sector"), "assets", ["sector"], unique=False)
    op.create_index(op.f("ix_assets_service_tag"), "assets", ["service_tag"], unique=False)
    op.create_index(op.f("ix_assets_warranty_end_date"), "assets", ["warranty_end_date"], unique=False)

    with op.batch_alter_table("stations") as batch_op:
        batch_op.add_column(sa.Column("asset_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("manufacturer", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("model", sa.String(length=160), nullable=True))
        batch_op.add_column(sa.Column("serial_number", sa.String(length=120), nullable=True))
        batch_op.create_index(op.f("ix_stations_asset_id"), ["asset_id"], unique=False)
        batch_op.create_index(op.f("ix_stations_serial_number"), ["serial_number"], unique=False)
        batch_op.create_foreign_key(
            "fk_stations_asset_id_assets",
            "assets",
            ["asset_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("stations") as batch_op:
        batch_op.drop_constraint("fk_stations_asset_id_assets", type_="foreignkey")
        batch_op.drop_index(op.f("ix_stations_serial_number"))
        batch_op.drop_index(op.f("ix_stations_asset_id"))
        batch_op.drop_column("serial_number")
        batch_op.drop_column("model")
        batch_op.drop_column("manufacturer")
        batch_op.drop_column("asset_id")

    op.drop_index(op.f("ix_assets_warranty_end_date"), table_name="assets")
    op.drop_index(op.f("ix_assets_service_tag"), table_name="assets")
    op.drop_index(op.f("ix_assets_sector"), table_name="assets")
    op.drop_index(op.f("ix_assets_patrimony_code"), table_name="assets")
    op.drop_index(op.f("ix_assets_expected_hostname"), table_name="assets")
    op.drop_index(op.f("ix_assets_assigned_user"), table_name="assets")
    op.drop_table("assets")
