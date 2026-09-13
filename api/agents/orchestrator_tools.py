from api.agents.orchestrator_schemas import PayloadSummary, SessionSnapshot
from api.domain.models import InterviewSession


def build_session_snapshot(session: InterviewSession) -> SessionSnapshot:
    """  
    组织状态摘要
    """
    current_turn = None
    if session.turns and 0 <= session.current_index < len(session.turns):
        current_turn = session.turns[session.current_index]

    return SessionSnapshot(
        session_id=session.session_id,
        user_id=session.user_id,
        session_status=session.status,
        current_index=session.current_index,
        total_turns=len(session.turns),
        current_turn_status=current_turn.status if current_turn else None,
        current_question_id=current_turn.question_id if current_turn else None,
        current_topic=current_turn.topic if current_turn else None,
        has_main_answer=bool(current_turn and current_turn.main_answer),
        has_followup_question=bool(current_turn and current_turn.followup_question),
        has_followup_answer=bool(current_turn and current_turn.followup_answer),
        has_evaluation=bool(current_turn and current_turn.evaluation),
        has_final_report=bool(session.final_report),
    )


def build_payload_summary(answer: str | None = None) -> PayloadSummary:
    """ 
    组织流程判断
    """
    normalized_answer = (answer or "").strip()

    return PayloadSummary(
        has_answer=bool(normalized_answer),
        answer_length=len(normalized_answer),
        answer_preview=normalized_answer[:80],
    )