from api.domain.models import InterviewSession
from api.errors import SessionNotFoundError

_sessions: dict[str, InterviewSession] = {}


def save_session(session: InterviewSession) -> None:
    _sessions[session.session_id] = session


def get_session(session_id: str) -> InterviewSession:
    try:
        return _sessions[session_id]
    except KeyError as exc:
        raise SessionNotFoundError(session_id) from exc


def update_session(session: InterviewSession) -> None:
    if session.session_id not in _sessions:
        raise SessionNotFoundError(session.session_id)
    _sessions[session.session_id] = session


def clear_sessions() -> None:
    _sessions.clear()
