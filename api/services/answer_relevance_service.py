from typing import Any

from api.agents.answer_relevance import run_answer_relevance_agent
from api.agents.answer_relevance_schemas import AnswerRelevanceResult
from api.agents.answer_relevance_tools import build_answer_relevance_context
from api.domain.models import InterviewSession, InterviewTurn
from api.errors import InterviewStateError


def classify_main_answer_relevance(
    session: InterviewSession,
    turn: InterviewTurn,
    answer: str,
    llm: Any | None = None,
) -> AnswerRelevanceResult:
    """ 
    先做状态检查 然后tool 组织 context
    也就是agent所需的数据
    """
    if session.status != "in_progress":
        raise InterviewStateError(
            f"interview is not in progress: {session.status}"
        )

    if turn.status != "waiting_main_answer":
        raise InterviewStateError(
            f"current turn does not allow main answer classification: {turn.status}"
        )

    if not answer or not answer.strip():
        raise InterviewStateError("main answer cannot be empty")

    context = build_answer_relevance_context(
        session=session,
        turn=turn,
        answer=answer,
    )

    return run_answer_relevance_agent(context, llm=llm)