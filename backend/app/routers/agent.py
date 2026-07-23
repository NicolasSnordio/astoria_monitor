from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.config import Settings, get_settings
from backend.app.database import get_db
from backend.app.models import Alert, Asset, Station, StationMetric
from backend.app.schemas import HeartbeatPayload, HeartbeatResponse

router = APIRouter(prefix="/api/agent", tags=["agent"])


def _check_agent_token(settings: Settings, token: str | None) -> None:
    if settings.agent_shared_token and token != settings.agent_shared_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid agent token.")


def _open_or_close_disk_alert(db: Session, station: Station, disk_free_gb: float | None, threshold_gb: float) -> None:
    alert = db.scalar(
        select(Alert).where(
            Alert.station_id == station.id,
            Alert.alert_type == "disk_low",
            Alert.closed_at.is_(None),
        )
    )

    if disk_free_gb is not None and disk_free_gb <= threshold_gb and alert is None:
        db.add(
            Alert(
                station=station,
                alert_type="disk_low",
                severity="warning",
                message=f"Disco com pouco espaco livre: {disk_free_gb:.1f} GB.",
            )
        )
        return

    if disk_free_gb is not None and disk_free_gb > threshold_gb and alert is not None:
        alert.closed_at = datetime.now(timezone.utc)


@router.post("/heartbeat", response_model=HeartbeatResponse)
def receive_heartbeat(
    payload: HeartbeatPayload,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_agent_token: str | None = Header(default=None),
) -> HeartbeatResponse:
    _check_agent_token(settings, x_agent_token)

    hostname = payload.hostname.strip().upper()
    station = db.scalar(select(Station).where(Station.hostname == hostname))
    if station is None:
        station = Station(hostname=hostname)
        db.add(station)
        db.flush()

    asset = db.scalar(select(Asset).where(Asset.expected_hostname == hostname))
    if asset is None and payload.serial_number:
        service_tag_matches = db.scalars(
            select(Asset).where(Asset.service_tag == payload.serial_number.strip().upper()).limit(2)
        ).all()
        if len(service_tag_matches) == 1:
            asset = service_tag_matches[0]

    if asset is not None:
        station.asset = asset

    station.ip_address = payload.ip_address
    station.username = payload.username
    station.os_name = payload.os_name
    station.os_version = payload.os_version
    station.manufacturer = payload.manufacturer
    station.model = payload.model
    station.serial_number = payload.serial_number.strip().upper() if payload.serial_number else None
    station.cpu_count = payload.cpu_count
    station.total_memory_mb = payload.total_memory_mb
    station.last_seen_at = datetime.now(timezone.utc)
    station.status = "online"

    db.add(
        StationMetric(
            station=station,
            collected_at=payload.collected_at or datetime.now(timezone.utc),
            cpu_percent=payload.cpu_percent,
            memory_percent=payload.memory_percent,
            disk_total_gb=payload.disk_total_gb,
            disk_free_gb=payload.disk_free_gb,
            uptime_seconds=payload.uptime_seconds,
        )
    )

    _open_or_close_disk_alert(db, station, payload.disk_free_gb, settings.disk_low_threshold_gb)
    db.commit()

    open_alerts = db.scalar(
        select(func.count()).select_from(Alert).where(Alert.station_id == station.id, Alert.closed_at.is_(None))
    )
    return HeartbeatResponse(station_id=station.id, status=station.status, alert_count=open_alerts or 0)
