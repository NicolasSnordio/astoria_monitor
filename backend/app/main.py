from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend.app.config import get_settings
from backend.app.routers import agent, auth, dashboard


BASE_DIR = Path(__file__).resolve().parent


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
    app.state.templates = Jinja2Templates(directory=BASE_DIR / "templates")
    app.include_router(auth.router)
    app.include_router(dashboard.router)
    app.include_router(agent.router)
    return app


app = create_app()
