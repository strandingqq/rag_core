import uuid
from dataclasses import asdict
from datetime import datetime

from api.agents.orchestrator import run_orchestrator
from api.agents.orchestrator_schemas import OrchestratorAction, RequestEvent
from api.dependencies import get_db, get_llm
from api.domain.models import InterviewPlan, InterviewSession, InterviewTurn
from api.errors import InterviewStateError
from api.services.answer_relevance_service import classify_main_answer_relevance
from api.services.interviewer_service import generate_followup_with_interviewer_agent
from api.schemas.interviews import (
    AnswerRequest,
    CreateInterviewRequest,
    CreateInterviewResponse,
    CurrentQuestionResponse,
    FollowupAnswerResponse,
    FollowupQuestionResponse,
    MainAnswerResponse,
    ReportResponse,
)
from api.services.evaluator import (
    build_evaluation_materials,
    build_followup_materials,
    evaluate_turn,
    generate_followup_question,
)
from api.services.planner import build_interview_plan
from api.services.report import generate_interview_report
from api.session_store import get_session as load_session
from api.session_store import save_session, update_session
from langsmith import traceable

def create_interview(request: CreateInterviewRequest) -> CreateInterviewResponse:
    print("now is in create_interview")
    db = get_db()
    plan = build_interview_plan(
        db=db,
        role=request.role,
        topics=request.topics,
        num_questions=request.num_questions,
        difficulty=request.difficulty,
    )
    session = init_interview_session(user_id=request.user_id, interview_plan=plan)
    save_session(session)

    return CreateInterviewResponse(
        session_id=session.session_id,
        status=session.status,
        current_index=session.current_index,
        total_questions=len(session.turns),
        current_question=_get_current_question_text(session),
    )


def get_current_question(session_id: str) -> CurrentQuestionResponse:
    session = load_session(session_id)
    if session.status == "completed":
        return CurrentQuestionResponse(
            session_id=session.session_id,
            status=session.status,
            current_index=session.current_index,
            question_type="none",
            question=None,
        )

    turn = get_current_turn(session)
    return CurrentQuestionResponse(
        session_id=session.session_id,
        status=session.status,
        current_index=session.current_index,
        question_type=_get_question_type(turn),
        question=_get_current_question_text(session),
    )

@traceable(name="SubmitMainAnswerWorkflow", run_type="chain")
def submit_main_answer(
    session_id: str,
    request: AnswerRequest,
) -> MainAnswerResponse:
    session = load_session(session_id)
    decision = run_orchestrator(
        RequestEvent.SUBMIT_MAIN_ANSWER,
        session=session,
        answer=request.answer,
    )
    if not decision.allowed:
        raise InterviewStateError(decision.error_message or decision.reason)
    if decision.action != OrchestratorAction.ACCEPT_MAIN_ANSWER:
        raise InterviewStateError(
            f"orchestrator returned unexpected action: {decision.action}"
        )

    # session = _submit_main_answer(session, request.answer, llm=get_llm())
    # update_session(session)
    # turn = get_current_turn(session)

    # return MainAnswerResponse(
    #     session_id=session.session_id,
    #     status=session.status,
    #     current_index=session.current_index,
    #     turn_status=turn.status,
    #     followup_question=turn.followup_question,
    # )
    turn = get_current_turn(session)
    llm = get_llm()

    relevance = classify_main_answer_relevance(
        session=session,
        turn=turn,
        answer=request.answer,
        llm=llm,
    )

    if relevance.suggested_action != "continue_interview":
        return MainAnswerResponse(
            session_id=session.session_id,
            status=session.status,
            current_index=session.current_index,
            turn_status=turn.status,
            followup_question=None,
            answer_category=relevance.category,
            suggested_action=relevance.suggested_action,
            response_to_user=relevance.response_to_user,
            answer_relevance_confidence=relevance.confidence,
        )

    session = _submit_main_answer(session, request.answer, llm=llm)
    update_session(session)
    turn = get_current_turn(session)

    return MainAnswerResponse(
        session_id=session.session_id,
        status=session.status,
        current_index=session.current_index,
        turn_status=turn.status,
        followup_question=turn.followup_question,
        answer_category=relevance.category,
        suggested_action=relevance.suggested_action,
        response_to_user=None,
        answer_relevance_confidence=relevance.confidence,
    )


def get_followup_question(session_id: str) -> FollowupQuestionResponse:
    session = load_session(session_id)
    turn = get_current_turn(session)
    if turn.status != "waiting_followup_answer":
        raise InterviewStateError(
            f"current turn does not allow reading followup question: {turn.status}"
        )
    if not turn.followup_question:
        raise InterviewStateError("followup question has not been generated")

    return FollowupQuestionResponse(
        session_id=session.session_id,
        current_index=session.current_index,
        question_type="followup",
        question=turn.followup_question,
    )


def submit_followup_answer(
    session_id: str,
    request: AnswerRequest,
) -> FollowupAnswerResponse:
    session = load_session(session_id)
    completed_turn_index = session.current_index
    session = _submit_followup_answer(session, request.answer, llm=get_llm())
    update_session(session)
    completed_turn = session.turns[completed_turn_index]

    next_question = None
    if session.status != "completed":
        next_question = _get_current_question_text(session)

    return FollowupAnswerResponse(
        session_id=session.session_id,
        status=session.status,
        completed_turn_index=completed_turn_index,
        score=completed_turn.score or 0,
        current_index=session.current_index,
        next_question=next_question,
    )


def get_report(session_id: str) -> ReportResponse:
    session = load_session(session_id)
    if session.status != "completed":
        raise InterviewStateError("interview is not completed")
    if not session.final_report:
        raise InterviewStateError("interview report is not available")

    return ReportResponse(
        session_id=session.session_id,
        status=session.status,
        report=session.final_report,
    )


def init_interview_session(
    user_id: str,
    interview_plan: InterviewPlan,
) -> InterviewSession:
    turns: list[InterviewTurn] = []
    for item in interview_plan.items:
        turns.append(
            InterviewTurn(
                index=item.index,
                question_id=item.question_id,
                topic=item.topic,
                main_question=item.question.question,
                status="not_started",
            )
        )

    if turns:
        turns[0].status = "waiting_main_answer"

    now = _now()
    return InterviewSession(
        session_id=str(uuid.uuid4()),
        user_id=user_id,
        plan=interview_plan,
        current_index=0,
        turns=turns,
        created_time=now,
        updated_time=now,
        status="in_progress",
    )


def get_current_turn(session: InterviewSession) -> InterviewTurn:
    if session.status != "in_progress":
        raise InterviewStateError(
            f"current interview status is not in_progress: {session.status}"
        )
    if session.current_index >= len(session.turns):
        raise InterviewStateError(f"current_index out of range: {session.current_index}")
    return session.turns[session.current_index]


def _submit_main_answer(
    session: InterviewSession,
    answer: str,
    llm,
) -> InterviewSession:
    if not answer or not answer.strip():
        raise InterviewStateError("main answer cannot be empty")

    turn = get_current_turn(session)
    if turn.status != "waiting_main_answer":
        raise InterviewStateError(
            f"current turn does not allow submitting main answer: {turn.status}"
        )

    turn.main_answer = answer
    # materials = build_followup_materials(session, turn)
    # turn.followup_question = generate_followup_question(turn, materials, llm=llm)
    interviewer_output = generate_followup_with_interviewer_agent(
        session=session,
        turn=turn,
        llm=llm,
    )
    turn.followup_question = interviewer_output.followup_question
    turn.status = "waiting_followup_answer"
    session.updated_time = _now()
    return session


def _submit_followup_answer(
    session: InterviewSession,
    answer: str,
    llm,
) -> InterviewSession:
    if not answer or not answer.strip():
        raise InterviewStateError("followup answer cannot be empty")

    turn = get_current_turn(session)
    if turn.status != "waiting_followup_answer":
        raise InterviewStateError(
            f"current turn does not allow submitting followup answer: {turn.status}"
        )

    turn.followup_answer = answer
    materials = build_evaluation_materials(session, turn)
    turn.evaluation = evaluate_turn(turn, materials, llm=llm)
    turn.score = turn.evaluation.score
    turn.status = "completed"

    has_next = session.current_index + 1 < len(session.turns)
    if has_next:
        session.current_index += 1
        session.turns[session.current_index].status = "waiting_main_answer"
    else:
        session.status = "completed"
        session.finished_time = _now()
        session.final_report = asdict(generate_interview_report(session, llm=llm))

    session.updated_time = _now()
    return session


def _get_current_question_text(session: InterviewSession) -> str | None:
    if session.status == "completed":
        return None

    turn = get_current_turn(session)
    if turn.status == "waiting_main_answer":
        return turn.main_question
    if turn.status == "waiting_followup_answer":
        return turn.followup_question

    raise InterviewStateError(f"current turn does not have a question: {turn.status}")


def _get_question_type(turn: InterviewTurn) -> str:
    if turn.status == "waiting_main_answer":
        return "main"
    if turn.status == "waiting_followup_answer":
        return "followup"
    raise InterviewStateError(f"current turn does not have a question: {turn.status}")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
