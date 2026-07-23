"""initial schema

Revision ID: 20260722_0001
Revises:
Create Date: 2026-07-22 17:20:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260722_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hostname", sa.String(length=120), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("username", sa.String(length=160), nullable=True),
        sa.Column("os_name", sa.String(length=120), nullable=True),
        sa.Column("os_version", sa.String(length=120), nullable=True),
        sa.Column("cpu_count", sa.Integer(), nullable=True),
        sa.Column("total_memory_mb", sa.Integer(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hostname"),
    )
    op.create_index(op.f("ix_stations_hostname"), "stations", ["hostname"], unique=False)
    op.create_index(op.f("ix_stations_last_seen_at"), "stations", ["last_seen_at"], unique=False)
    op.create_index(op.f("ix_stations_status"), "stations", ["status"], unique=False)

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("station_id", sa.Integer(), nullable=False),
        sa.Column("alert_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=24), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["station_id"], ["stations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alerts_alert_type"), "alerts", ["alert_type"], unique=False)
    op.create_index(op.f("ix_alerts_closed_at"), "alerts", ["closed_at"], unique=False)
    op.create_index(op.f("ix_alerts_opened_at"), "alerts", ["opened_at"], unique=False)
    op.create_index(op.f("ix_alerts_station_id"), "alerts", ["station_id"], unique=False)

    op.create_table(
        "station_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("station_id", sa.Integer(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cpu_percent", sa.Float(), nullable=True),
        sa.Column("memory_percent", sa.Float(), nullable=True),
        sa.Column("disk_total_gb", sa.Float(), nullable=True),
        sa.Column("disk_free_gb", sa.Float(), nullable=True),
        sa.Column("uptime_seconds", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["station_id"], ["stations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_station_metrics_collected_at"), "station_metrics", ["collected_at"], unique=False)
    op.create_index(op.f("ix_station_metrics_station_id"), "station_metrics", ["station_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_station_metrics_station_id"), table_name="station_metrics")
    op.drop_index(op.f("ix_station_metrics_collected_at"), table_name="station_metrics")
    op.drop_table("station_metrics")
    op.drop_index(op.f("ix_alerts_station_id"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_opened_at"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_closed_at"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_alert_type"), table_name="alerts")
    op.drop_table("alerts")
    op.drop_index(op.f("ix_stations_status"), table_name="stations")
    op.drop_index(op.f("ix_stations_last_seen_at"), table_name="stations")
    op.drop_index(op.f("ix_stations_hostname"), table_name="stations")
    op.drop_table("stations")
