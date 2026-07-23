from datetime import datetime, timedelta, timezone

from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.config import Settings, get_settings
from backend.app.database import get_db
from backend.app.models import Alert, Asset, Station, StationMetric
from backend.app.routers.auth import require_user

router = APIRouter(tags=["dashboard"])


def _is_online(last_seen_at: datetime | None, settings: Settings) -> bool:
    if last_seen_at is None:
        return False
    last_seen = last_seen_at
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    return last_seen >= datetime.now(timezone.utc) - timedelta(minutes=settings.offline_after_minutes)


def _status_for_station(station: Station, open_alerts: list[Alert], settings: Settings) -> tuple[str, str]:
    online = _is_online(station.last_seen_at, settings)
    if station.last_seen_at is None:
        return "Sem coleta", "is-muted"
    if not online:
        return "Offline", "is-offline"
    if open_alerts:
        return "Atencao", "is-warning"
    return "Online", "is-online"


def _best_station(stations: list[Station]) -> Station | None:
    if not stations:
        return None
    def station_key(station: Station) -> datetime:
        if station.last_seen_at is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        if station.last_seen_at.tzinfo is None:
            return station.last_seen_at.replace(tzinfo=timezone.utc)
        return station.last_seen_at

    return sorted(stations, key=station_key, reverse=True)[0]


def _risk_for(status_label: str, alert: str, disk_free_gb: float, warranty_end: datetime | None) -> str:
    if disk_free_gb and disk_free_gb <= 15:
        return "Armazenamento"
    if alert:
        return "Monitoramento"
    if status_label == "Offline":
        return "Conectividade"
    if status_label == "Sem coleta":
        return "Coleta"
    if warranty_end and warranty_end < datetime.now(timezone.utc).date():
        return "Garantia"
    if status_label == "Atencao":
        return "Performance"
    return "Saudavel"


def _device_type_from(text: str | None) -> str:
    value = (text or "").lower()
    if "notebook" in value or "latitude" in value or "inspiron" in value or "xps" in value:
        return "notebook"
    return "desktop"


def _asset_rows(assets: list[Asset], settings: Settings) -> list[dict]:
    rows = []
    for asset in assets:
        station = _best_station(asset.stations)
        if station is None:
            rows.append(
                {
                    "asset_code": asset.patrimony_code or f"AST-{asset.id:06d}",
                    "equipment": asset.expected_hostname or asset.equipment_type_model or "Ativo sem hostname",
                    "username": asset.assigned_user or "-",
                    "sector": asset.sector or "-",
                    "status_label": "Sem coleta",
                    "status_class": "is-muted",
                    "device_type": _device_type_from(asset.equipment_type_model),
                    "last_seen": "-",
                    "alert": "Aguardando primeira coleta do agente",
                    "risk": "Coleta",
                    "disk_free_gb": 0,
                    "cpu_percent": 0,
                    "memory_percent": 0,
                    "software": asset.office_version or "-",
                    "os_name": "-",
                    "detail_url": "/assets",
                }
            )
            continue

        latest_metric = station.metrics[0] if station.metrics else None
        open_alerts = [alert for alert in station.alerts if alert.closed_at is None]
        status_label, status_class = _status_for_station(station, open_alerts, settings)
        alert_message = open_alerts[0].message if open_alerts else ""
        disk_free_gb = latest_metric.disk_free_gb if latest_metric and latest_metric.disk_free_gb is not None else 0
        rows.append(
            {
                "asset_code": asset.patrimony_code or f"AST-{asset.id:06d}",
                "equipment": asset.equipment_type_model or station.model or station.hostname,
                "username": asset.assigned_user or station.username or "-",
                "sector": asset.sector or "-",
                "status_label": status_label,
                "status_class": status_class,
                "device_type": _device_type_from(asset.equipment_type_model or station.model),
                "last_seen": station.last_seen_at.strftime("%d/%m/%Y %H:%M") if station.last_seen_at else "-",
                "alert": alert_message,
                "risk": _risk_for(status_label, alert_message, float(disk_free_gb or 0), asset.warranty_end_date),
                "disk_free_gb": disk_free_gb,
                "cpu_percent": latest_metric.cpu_percent if latest_metric and latest_metric.cpu_percent is not None else 0,
                "memory_percent": latest_metric.memory_percent if latest_metric and latest_metric.memory_percent is not None else 0,
                "software": asset.office_version or "Agente Astoria Monitor",
                "os_name": station.os_name or "-",
                "detail_url": f"/stations/{station.id}",
            }
        )
    return rows


def _all_rows(db: Session, settings: Settings, risk_only: bool = False) -> list[dict]:
    assets = db.scalars(
        select(Asset)
        .options(selectinload(Asset.stations).selectinload(Station.metrics), selectinload(Asset.stations).selectinload(Station.alerts))
        .order_by(Asset.expected_hostname.asc())
    ).all()

    rows = _asset_rows(assets, settings)

    unmatched_stations = db.scalars(
        select(Station)
        .options(selectinload(Station.metrics), selectinload(Station.alerts))
        .where(Station.asset_id.is_(None))
        .order_by(Station.hostname.asc())
    ).all()
    for station in unmatched_stations:
        latest_metric = station.metrics[0] if station.metrics else None
        open_alerts = [alert for alert in station.alerts if alert.closed_at is None]
        status_label, status_class = _status_for_station(station, open_alerts, settings)
        alert_message = open_alerts[0].message if open_alerts else "Maquina coletada sem cadastro patrimonial"
        rows.append(
            {
                "asset_code": f"COLETA-{station.id:06d}",
                "equipment": station.hostname,
                "username": station.username or "-",
                "sector": "Nao cadastrado",
                "status_label": "Atencao" if status_label == "Online" else status_label,
                "status_class": "is-warning" if status_label == "Online" else status_class,
                "device_type": _device_type_from(station.model),
                "last_seen": station.last_seen_at.strftime("%d/%m/%Y %H:%M") if station.last_seen_at else "-",
                "alert": alert_message,
                "risk": "Cadastro",
                "disk_free_gb": latest_metric.disk_free_gb if latest_metric and latest_metric.disk_free_gb is not None else 0,
                "cpu_percent": latest_metric.cpu_percent if latest_metric and latest_metric.cpu_percent is not None else 0,
                "memory_percent": latest_metric.memory_percent if latest_metric and latest_metric.memory_percent is not None else 0,
                "software": "Agente Astoria Monitor",
                "os_name": station.os_name or "-",
                "detail_url": f"/stations/{station.id}",
            }
        )

    if risk_only:
        return [row for row in rows if row["status_label"] != "Online"]
    return rows


def _summary(rows: list[dict]) -> dict:
    total_stations = len(rows)
    online_count = sum(1 for row in rows if row["status_label"] == "Online")
    attention_count = sum(1 for row in rows if row["status_label"] == "Atencao")
    offline_count = sum(1 for row in rows if row["status_label"] == "Offline")
    no_collect_count = sum(1 for row in rows if row["status_label"] == "Sem coleta")

    def pct(value: int) -> int:
        if total_stations == 0:
            return 0
        return round((value / total_stations) * 100)

    return {
        "total_stations": total_stations,
        "online_count": online_count,
        "attention_count": attention_count,
        "offline_count": offline_count,
        "no_collect_count": no_collect_count,
        "online_pct": pct(online_count),
        "attention_pct": pct(attention_count),
        "offline_pct": pct(offline_count),
        "no_collect_pct": pct(no_collect_count),
        "health_online_end": pct(online_count),
        "health_warning_end": pct(online_count) + pct(attention_count),
        "health_critical_end": pct(online_count) + pct(attention_count) + pct(offline_count),
    }


def _pct(value: int | float, total: int | float) -> int:
    if total == 0:
        return 0
    return round((value / total) * 100)


def _count_by(rows: list[dict], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get(field) or "Nao informado")
        counts[key] = counts.get(key, 0) + 1
    return counts


def _bar_height(value: int, max_value: int) -> int:
    if max_value <= 0 or value <= 0:
        return 8
    return max(14, round((value / max_value) * 52))


def _status_bars(rows: list[dict], status_label: str) -> list[int]:
    sectors = sorted({row["sector"] for row in rows})
    values = [sum(1 for row in rows if row["sector"] == sector and row["status_label"] == status_label) for sector in sectors]
    if not values:
        values = [0, 0, 0, 0]
    while len(values) < 4:
        values.append(0)
    max_value = max(values)
    return [_bar_height(value, max_value) for value in values[:7]]


def _summary_cards(rows: list[dict]) -> list[dict]:
    summary = _summary(rows)
    return [
        {
            "label": "Online",
            "count": summary["online_count"],
            "pct": summary["online_pct"],
            "tone": "tone-success",
            "bars": _status_bars(rows, "Online"),
        },
        {
            "label": "Atencao",
            "count": summary["attention_count"],
            "pct": summary["attention_pct"],
            "tone": "tone-warning",
            "bars": _status_bars(rows, "Atencao"),
        },
        {
            "label": "Offline",
            "count": summary["offline_count"],
            "pct": summary["offline_pct"],
            "tone": "tone-danger",
            "bars": _status_bars(rows, "Offline"),
        },
        {
            "label": "Sem coleta",
            "count": summary["no_collect_count"],
            "pct": summary["no_collect_pct"],
            "tone": "tone-muted",
            "bars": _status_bars(rows, "Sem coleta"),
        },
    ]


def _report_context(rows: list[dict]) -> dict:
    total = len(rows)
    risk_rows = [row for row in rows if row["status_label"] != "Online"]
    status_counts = _count_by(rows, "status_label")
    status_order = [
        ("Online", "success"),
        ("Atencao", "warning"),
        ("Offline", "danger"),
        ("Sem coleta", "muted"),
    ]
    status_segments = [
        {
            "label": label,
            "count": status_counts.get(label, 0),
            "pct": _pct(status_counts.get(label, 0), total),
            "tone": tone,
        }
        for label, tone in status_order
    ]

    sector_counts = _count_by(risk_rows, "sector")
    max_sector = max(sector_counts.values(), default=0)
    sector_risk = [
        {"label": sector, "count": count, "pct": _pct(count, max_sector)}
        for sector, count in sorted(sector_counts.items(), key=lambda item: item[1], reverse=True)
    ]

    risk_counts = _count_by(risk_rows, "risk")
    max_risk = max(risk_counts.values(), default=0)
    risk_types = [
        {"label": risk, "count": count, "pct": _pct(count, max_risk)}
        for risk, count in sorted(risk_counts.items(), key=lambda item: item[1], reverse=True)
    ]

    storage_rows = sorted(rows, key=lambda row: float(row.get("disk_free_gb") or 0))[:6]
    storage_chart = [
        {
            "asset_code": row["asset_code"],
            "equipment": row["equipment"],
            "disk_free_gb": row["disk_free_gb"],
            "pct": min(100, _pct(float(row.get("disk_free_gb") or 0), 120)),
            "status_label": row["status_label"],
        }
        for row in storage_rows
    ]

    device_counts = _count_by(rows, "device_type")
    device_mix = [
        {"label": "Notebooks", "count": device_counts.get("notebook", 0), "pct": _pct(device_counts.get("notebook", 0), total)},
        {"label": "Desktops", "count": device_counts.get("desktop", 0), "pct": _pct(device_counts.get("desktop", 0), total)},
    ]

    cpu_avg = round(sum(float(row.get("cpu_percent") or 0) for row in rows) / total) if total else 0
    memory_avg = round(sum(float(row.get("memory_percent") or 0) for row in rows) / total) if total else 0
    disk_low_count = sum(1 for row in rows if float(row.get("disk_free_gb") or 0) <= 15)

    return {
        "status_segments": status_segments,
        "sector_risk": sector_risk,
        "risk_types": risk_types,
        "storage_chart": storage_chart,
        "device_mix": device_mix,
        "cpu_avg": cpu_avg,
        "memory_avg": memory_avg,
        "disk_low_count": disk_low_count,
        "risk_total": len(risk_rows),
    }


def _recent_alerts(rows: list[dict]) -> list[dict]:
    alerts = [row for row in rows if row["alert"]]
    return [
        {
            "message": row["alert"],
            "equipment": row["equipment"],
            "time": row["last_seen"].split(" ")[-1],
            "severity": "danger" if row["status_label"] == "Offline" else "warning",
        }
        for row in alerts[:3]
    ]


def _base_context(
    request: Request,
    settings: Settings,
    user: dict,
    active_page: str,
    rows: list[dict] | None = None,
) -> dict:
    rows = rows or []
    return {
        "request": request,
        "settings": settings,
        "user": user,
        "active_page": active_page,
        "rows": rows,
        **_summary(rows),
        "open_alerts_total": sum(1 for row in rows if row["alert"]),
        "metrics_count": len(rows),
        "recent_alerts": _recent_alerts(rows),
        "summary_cards": _summary_cards(rows),
    }


@router.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: dict = Depends(require_user),
):
    all_rows = _all_rows(db, settings, risk_only=False)
    risk_rows = [row for row in all_rows if row["status_label"] != "Online"]
    context = _base_context(request, settings, user, "dashboard", risk_rows)
    context.update(_summary(all_rows))
    context["all_assets_count"] = len(all_rows)
    context["dashboard_mode"] = "risk"
    context["open_alerts_total"] = sum(1 for row in risk_rows if row["alert"])
    context["metrics_count"] = len(all_rows)
    context["recent_alerts"] = _recent_alerts(risk_rows)
    context["summary_cards"] = _summary_cards(all_rows)

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=context,
    )


@router.get("/assets", response_class=HTMLResponse)
def assets_page(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: dict = Depends(require_user),
):
    rows = _all_rows(db, settings, risk_only=False)
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="module_table.html",
        context={
            **_base_context(request, settings, user, "assets", rows),
            "title": "Ativos",
            "subtitle": "Cadastro operacional dos computadores, notebooks e desktops monitorados.",
            "table_title": "Todos os ativos",
        },
    )


@router.post("/assets")
async def create_asset(
    request: Request,
    settings: Settings = Depends(get_settings),
    user: dict = Depends(require_user),
    db: Session = Depends(get_db),
):
    body = (await request.body()).decode()
    form = parse_qs(body)

    asset = Asset(
        patrimony_code=(form.get("patrimony_code", [""])[0].strip() or None),
        expected_hostname=(form.get("expected_hostname", [""])[0].strip().upper() or None),
        assigned_user=(form.get("assigned_user", [""])[0].strip() or None),
        sector=(form.get("sector", [""])[0].strip() or None),
        equipment_type_model=(form.get("equipment_type_model", [""])[0].strip() or None),
        service_tag=(form.get("service_tag", [""])[0].strip().upper() or None),
    )
    db.add(asset)
    db.commit()
    return RedirectResponse("/assets", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/reports", response_class=HTMLResponse)
def reports_page(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: dict = Depends(require_user),
):
    rows = _all_rows(db, settings, risk_only=False)
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="reports.html",
        context={
            **_base_context(request, settings, user, "reports", rows),
            **_report_context(rows),
            "title": "Relatorios",
        },
    )


@router.get("/alerts", response_class=HTMLResponse)
def alerts_page(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: dict = Depends(require_user),
):
    rows = [row for row in _all_rows(db, settings, risk_only=False) if row["alert"]]
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="alerts.html",
        context={**_base_context(request, settings, user, "alerts", rows), "title": "Alertas"},
    )


@router.get("/inventory", response_class=HTMLResponse)
def inventory_page(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: dict = Depends(require_user),
):
    rows = _all_rows(db, settings, risk_only=False)
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="inventory.html",
        context={**_base_context(request, settings, user, "inventory", rows), "title": "Inventario"},
    )


@router.get("/users", response_class=HTMLResponse)
def users_page(request: Request, settings: Settings = Depends(get_settings), user: dict = Depends(require_user)):
    users = [
        {
            "name": settings.admin_display_name,
            "username": settings.admin_username,
            "profile": "Administrador",
            "permission": "100%",
            "status": "Ativo",
        },
        {
            "name": "Operador Monitoramento",
            "username": "monitor",
            "profile": "Leitura",
            "permission": "40%",
            "status": "Pendente",
        },
    ]
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="users.html",
        context={
            "request": request,
            "settings": settings,
            "user": user,
            "active_page": "users",
            "users": users,
        },
    )


@router.get("/stations/{station_id}", response_class=HTMLResponse)
def station_detail(
    station_id: int,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: dict = Depends(require_user),
):
    station = db.get(Station, station_id)
    if station is None:
        return request.app.state.templates.TemplateResponse(
            request=request,
            name="not_found.html",
            context={"request": request, "settings": settings, "user": user, "active_page": "assets"},
            status_code=404,
        )

    metrics = db.scalars(
        select(StationMetric)
        .where(StationMetric.station_id == station.id)
        .order_by(StationMetric.collected_at.desc())
        .limit(25)
    ).all()
    alerts = db.scalars(
        select(Alert)
        .where(Alert.station_id == station.id)
        .order_by(Alert.opened_at.desc())
        .limit(25)
    ).all()

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="station_detail.html",
        context={
            "request": request,
            "station": station,
            "metrics": metrics,
            "alerts": alerts,
            "online": _is_online(station.last_seen_at, settings),
            "settings": settings,
            "user": user,
            "active_page": "assets",
        },
    )
