from datetime import datetime

from pydantic import BaseModel, Field


class HeartbeatPayload(BaseModel):
    hostname: str = Field(min_length=1, max_length=120)
    ip_address: str | None = None
    username: str | None = None
    os_name: str | None = None
    os_version: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    cpu_count: int | None = None
    total_memory_mb: int | None = None
    collected_at: datetime | None = None
    cpu_percent: float | None = Field(default=None, ge=0, le=100)
    memory_percent: float | None = Field(default=None, ge=0, le=100)
    disk_total_gb: float | None = Field(default=None, ge=0)
    disk_free_gb: float | None = Field(default=None, ge=0)
    uptime_seconds: int | None = Field(default=None, ge=0)


class HeartbeatResponse(BaseModel):
    station_id: int
    status: str
    alert_count: int
