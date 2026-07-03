"""REST routes for chat sessions."""

from uuid import uuid4

from fastapi import APIRouter, Request

from api.schemas import AuthRequest, AuthResponse, ChatRequest, ChatStartResponse

router = APIRouter()


class SessionState:
    """一个聊天会话的运行时状态。"""

    def __init__(self, request: ChatRequest) -> None:
        self.request = request
        self.is_executing = False
        self.messages: list[dict[str, str]] = []


SESSIONS: dict[str, SessionState] = {}


@router.get("/health")
async def health() -> dict[str, str]:
    """Health check for local and deployment probes."""
    return {"status": "ok"}


@router.post("/api/v1/chat")
async def start_chat(request: ChatRequest) -> ChatStartResponse:
    """Create a lightweight chat session."""
    session_id = str(uuid4())
    SESSIONS[session_id] = SessionState(request=request)
    return ChatStartResponse(session_id=session_id)


@router.post("/api/v1/auth")
async def verify_passphrase(request: Request, payload: AuthRequest) -> AuthResponse:
    """Verify a passphrase and return the scoped user ID."""
    auth = getattr(request.app.state, "auth", None)
    if auth is None:
        return AuthResponse(user_id="anonymous", valid=True)

    user_id = auth.verify(payload.passphrase)
    if user_id is None:
        return AuthResponse(user_id="", valid=False)
    return AuthResponse(user_id=user_id, valid=True)
