from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Station(Base):
    __tablename__ = "stations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"), index=True)
    hostname: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    username: Mapped[str | None] = mapped_column(String(160))
    os_name: Mapped[str | None] = mapped_column(String(120))
    os_version: Mapped[str | None] = mapped_column(String(120))
    manufacturer: Mapped[str | None] = mapped_column(String(120))
    model: Mapped[str | None] = mapped_column(String(160))
    serial_number: Mapped[str | None] = mapped_column(String(120), index=True)
    cpu_count: Mapped[int | None] = mapped_column(Integer)
    total_memory_mb: Mapped[int | None] = mapped_column(Integer)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(24), default="unknown", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    metrics: Mapped[list["StationMetric"]] = relationship(
        back_populates="station",
        cascade="all, delete-orphan",
        order_by="StationMetric.collected_at.desc()",
    )
    alerts: Mapped[list["Alert"]] = relationship(back_populates="station", cascade="all, delete-orphan")
    asset: Mapped["Asset | None"] = relationship(back_populates="stations")


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    expected_hostname: Mapped[str | None] = mapped_column(String(120), unique=True, index=True)
    sector: Mapped[str | None] = mapped_column(String(120), index=True)
    assigned_user: Mapped[str | None] = mapped_column(String(160), index=True)
    patrimony_code: Mapped[str | None] = mapped_column(String(80), index=True)
    equipment_type_model: Mapped[str | None] = mapped_column(String(180))
    service_tag: Mapped[str | None] = mapped_column(String(120), index=True)
    purchase_date: Mapped[date | None] = mapped_column(Date)
    warranty_end_date: Mapped[date | None] = mapped_column(Date, index=True)
    monitor_description: Mapped[str | None] = mapped_column(String(180))
    monitor_patrimony_code: Mapped[str | None] = mapped_column(String(80))
    office_version: Mapped[str | None] = mapped_column(String(120))
    office_activation_email: Mapped[str | None] = mapped_column(String(180))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    stations: Mapped[list[Station]] = relationship(back_populates="asset")


class StationMetric(Base):
    __tablename__ = "station_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id", ondelete="CASCADE"), index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    cpu_percent: Mapped[float | None] = mapped_column(Float)
    memory_percent: Mapped[float | None] = mapped_column(Float)
    disk_total_gb: Mapped[float | None] = mapped_column(Float)
    disk_free_gb: Mapped[float | None] = mapped_column(Float)
    uptime_seconds: Mapped[int | None] = mapped_column(Integer)

    station: Mapped[Station] = relationship(back_populates="metrics")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id", ondelete="CASCADE"), index=True)
    alert_type: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[str] = mapped_column(String(24), default="warning")
    message: Mapped[str] = mapped_column(Text)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    station: Mapped[Station] = relationship(back_populates="alerts")
