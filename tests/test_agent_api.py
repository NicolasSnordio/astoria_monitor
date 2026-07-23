import os
from pathlib import Path
from tempfile import NamedTemporaryFile

tmp_db = NamedTemporaryFile(delete=False, suffix=".db")
tmp_db.close()
os.environ["DATABASE_URL"] = f"sqlite:///{Path(tmp_db.name).as_posix()}"

from fastapi.testclient import TestClient

from backend.app.database import Base, engine
from backend.app.main import app


def setup_module() -> None:
    Base.metadata.create_all(bind=engine)


def teardown_module() -> None:
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    Path(tmp_db.name).unlink(missing_ok=True)


def test_heartbeat_creates_station_and_metric() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/agent/heartbeat",
        json={
            "hostname": "ASTORIA-TESTE",
            "ip_address": "192.168.1.10",
            "username": "ASTORIA\\usuario",
            "os_name": "Microsoft Windows",
            "os_version": "11",
            "cpu_count": 8,
            "total_memory_mb": 16384,
            "cpu_percent": 12.5,
            "memory_percent": 44.2,
            "disk_total_gb": 250,
            "disk_free_gb": 100,
            "uptime_seconds": 3600,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "online"
    assert response.json()["station_id"] >= 1

    protected = client.get("/", follow_redirects=False)
    assert protected.status_code == 303
    assert protected.headers["location"] == "/login"

    login = client.post(
        "/login",
        content="username=admin&password=admin",
        headers={"content-type": "application/x-www-form-urlencoded"},
        follow_redirects=False,
    )
    assert login.status_code == 303

    dashboard = client.get("/")
    assert dashboard.status_code == 200
    assert "Visao geral dos computadores" in dashboard.text

    assets = client.get("/assets")
    assert assets.status_code == 200
    assert "ASTORIA-TESTE" in assets.text
