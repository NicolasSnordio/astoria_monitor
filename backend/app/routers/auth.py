import base64
import hashlib
import hmac
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse

from backend.app.config import Settings, get_settings

router = APIRouter(tags=["auth"])
SESSION_COOKIE = "astoria_session"


def _sign(value: str, settings: Settings) -> str:
    return hmac.new(settings.app_secret_key.encode(), value.encode(), hashlib.sha256).hexdigest()


def _encode_session(username: str, settings: Settings) -> str:
    payload = f"{username}|100|{settings.admin_display_name}"
    encoded = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    return f"{encoded}.{_sign(encoded, settings)}"


def _decode_session(token: str | None, settings: Settings) -> dict | None:
    if not token or "." not in token:
        return None
    encoded, signature = token.rsplit(".", 1)
    if not hmac.compare_digest(signature, _sign(encoded, settings)):
        return None
    padded = encoded + "=" * (-len(encoded) % 4)
    try:
        username, permission, display_name = base64.urlsafe_b64decode(padded.encode()).decode().split("|", 2)
    except ValueError:
        return None
    return {"username": username, "permission": permission, "display_name": display_name}


def current_user(request: Request, settings: Settings = Depends(get_settings)) -> dict | None:
    return _decode_session(request.cookies.get(SESSION_COOKIE), settings)


def require_user(request: Request, settings: Settings = Depends(get_settings)) -> dict:
    user = current_user(request, settings)
    if user is None:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    return user


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request, settings: Settings = Depends(get_settings), user: dict | None = Depends(current_user)):
    if user is not None:
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"request": request, "settings": settings, "error": None},
    )


@router.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, settings: Settings = Depends(get_settings)):
    body = (await request.body()).decode()
    form = parse_qs(body)
    username = form.get("username", [""])[0].strip()
    password = form.get("password", [""])[0]

    if username != settings.admin_username or password != settings.admin_password:
        return request.app.state.templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"request": request, "settings": settings, "error": "Usuario ou senha invalidos."},
            status_code=401,
        )

    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        SESSION_COOKIE,
        _encode_session(username, settings),
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 10,
    )
    return response


@router.get("/logout")
def logout() -> Response:
    response = RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(SESSION_COOKIE)
    return response
