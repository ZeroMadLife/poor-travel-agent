"""V7 cloud authentication routes with server-side session ownership."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, Response

from api.schemas import CloudCurrentUserResponse, CloudDevelopmentLoginRequest
from core.cloud.auth.repository import CloudRepository, new_browser_session_token

router = APIRouter()
_SESSION_COOKIE = "sage_session"
_SESSION_TTL = timedelta(days=7)


def _repository(request: Request) -> CloudRepository:
    repository = getattr(request.app.state, "cloud_repository", None)
    if not isinstance(repository, CloudRepository):
        raise HTTPException(status_code=503, detail="cloud control plane is unavailable")
    return repository


@router.get("/api/v1/cloud/me", response_model=CloudCurrentUserResponse)
async def get_cloud_current_user(request: Request) -> CloudCurrentUserResponse:
    """Return the user resolved from the HttpOnly server session cookie."""
    user = await _repository(request).authenticated_user(request.cookies.get(_SESSION_COOKIE, ""))
    if user is None:
        raise HTTPException(status_code=401, detail="cloud authentication is required")
    return CloudCurrentUserResponse(
        user_id=user.user_id, email=user.email, display_name=user.display_name
    )


@router.post("/api/v1/cloud/auth/dev/login", response_model=CloudCurrentUserResponse)
async def development_login(
    payload: CloudDevelopmentLoginRequest,
    request: Request,
    response: Response,
) -> CloudCurrentUserResponse:
    """Create a development-only session after a one-time invite is consumed."""
    if (
        getattr(request.app.state, "cloud_app_env", "") != "development"
        or not bool(getattr(request.app.state, "cloud_dev_login_enabled", False))
    ):
        raise HTTPException(status_code=404, detail="not found")
    repository = _repository(request)
    try:
        user = await repository.get_or_create_identity(
            provider="development",
            provider_subject=payload.email.strip().lower(),
            email=payload.email,
            display_name=payload.display_name,
            invite_code=payload.invite_code,
            reject_existing_identity=True,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="a valid invite is required") from exc
    token = new_browser_session_token()
    await repository.create_session(
        user.user_id, token, expires_at=datetime.now(UTC) + _SESSION_TTL
    )
    response.set_cookie(
        key=_SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=bool(getattr(request.app.state, "cloud_secure_cookies", False)),
        samesite="lax",
        max_age=int(_SESSION_TTL.total_seconds()),
        path="/",
    )
    return CloudCurrentUserResponse(
        user_id=user.user_id, email=user.email, display_name=user.display_name
    )


@router.post("/api/v1/cloud/auth/logout", status_code=204, response_class=Response)
async def logout_cloud_session(request: Request) -> Response:
    """Revoke the server record and clear the browser's cookie."""
    token = request.cookies.get(_SESSION_COOKIE, "")
    await _repository(request).revoke_session(token)
    response = Response(status_code=204)
    response.delete_cookie(
        key=_SESSION_COOKIE,
        path="/",
        httponly=True,
        secure=bool(getattr(request.app.state, "cloud_secure_cookies", True)),
        samesite="lax",
    )
    return response
