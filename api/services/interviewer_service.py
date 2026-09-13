from typing import Any

from api.agents.interviewer import run_interviewer_agent
from api.agents.interviewer_schemas import InterviewerOutput
from api.agents.interviewer_tools import build_interviewer_context
from api.domain.models import InterviewSession, InterviewTurn
from api.errors import InterviewStateError


def generate_followup_with_interviewer_agent(
    session: InterviewSession,
    turn: InterviewTurn,
    llm: Any | None = None,
) -> InterviewerOutput:
    if session.status != "in_progress":
        raise InterviewStateError(
            f"interview is not in progress: {session.status}"
        )

    if turn.status != "waiting_main_answer":
        raise InterviewStateError(
            f"current turn does not allow generating followup: {turn.status}"
        )

    if not turn.main_answer or not turn.main_answer.strip():
        raise InterviewStateError("main answer cannot be empty")

    context = build_interviewer_context(session, turn)
    return run_interviewer_agent(context, llm=llm)