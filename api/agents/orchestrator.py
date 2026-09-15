from api.agents.orchestrator_schemas import (
    OrchestratorAction, # 接下来做什么操作
    OrchestratorDecision, # 最终返回的完整决策对象
    PayloadSummary,
    RequestEvent,
    SessionSnapshot,
)
from api.agents.orchestrator_tools import (
    build_payload_summary, # 分析answer 
    build_session_snapshot, # 分析session
)
from api.domain.models import InterviewSession
from langsmith import traceable

@traceable(name="RuleOrchestrator", run_type="chain")
def run_orchestrator(
    request_event: RequestEvent | str, # 请求事件
    session: InterviewSession | None = None, # session
    answer: str | None = None, # 用户答案
) -> OrchestratorDecision:
    """ 
    根据用户请求、当前面试 Session 和用户答案，决定这个请求该不该执行，以及应该执行什么操作。
    """
    event = RequestEvent(request_event) # 把输入转换为统一格式 当前 API 事件 在什么
    payload = build_payload_summary(answer) # 把用户输入 整理为流程判断所需要的摘要

    if event == RequestEvent.CREATE_INTERVIEW:
        # 创建一个特殊请求 不需要session修改 所以直接return
        return _allow(
            action=OrchestratorAction.CREATE_PLAN,
            reason="Creating a new interview does not require an existing session.",
            required_tools=["build_interview_plan", "init_interview_session"],
        )

    if session is None:
        return _reject(
            reason="This request requires an existing session.",
            error_code="SESSION_REQUIRED",
            error_message="session is required for this request",
        )

    snapshot = build_session_snapshot(session)

    if event in {
        RequestEvent.SUBMIT_MAIN_ANSWER,
        RequestEvent.SUBMIT_FOLLOWUP_ANSWER,
    } and not payload.has_answer:
        """ 
        如果用户正在提交答案 并且答案为空
        """
        return _reject(
            snapshot=snapshot,
            reason="Answer submission requests require a non-empty answer.",
            error_code="EMPTY_ANSWER",
            error_message="answer cannot be empty",
        )

    if snapshot.session_status == "completed":
        return _route_completed_session(event, snapshot)

    if snapshot.session_status != "in_progress":
        return _reject(
            snapshot=snapshot,
            reason=f"Unsupported session status: {snapshot.session_status}.",
            error_code="INVALID_SESSION_STATUS",
            error_message=f"invalid session status: {snapshot.session_status}",
        )

    if snapshot.current_turn_status == "waiting_main_answer":
        return _route_waiting_main_answer(event, snapshot)

    if snapshot.current_turn_status == "waiting_followup_answer":
        return _route_waiting_followup_answer(event, snapshot)

    return _reject(
        snapshot=snapshot,
        reason=f"Unsupported current turn status: {snapshot.current_turn_status}.",
        error_code="INVALID_TURN_STATUS",
        error_message=f"invalid turn status: {snapshot.current_turn_status}",
    )


def _route_completed_session(
    event: RequestEvent,
    snapshot: SessionSnapshot,
) -> OrchestratorDecision:
    if event == RequestEvent.GET_REPORT:
        if snapshot.has_final_report:
            return _allow(
                snapshot=snapshot,
                action=OrchestratorAction.RETURN_REPORT,
                reason="The interview is completed and a final report is available.",
                required_tools=["get_report"],
            )
        return _reject(
            snapshot=snapshot,
            reason="The interview is completed but no final report is available.",
            error_code="REPORT_NOT_AVAILABLE",
            error_message="interview report is not available",
        )

    if event == RequestEvent.GET_LEARNING_ADVICE:
        return _allow(
            snapshot=snapshot,
            action=OrchestratorAction.RETURN_LEARNING_ADVICE,
            reason="The interview is completed, so learning advice can be generated.",
            required_tools=["run_learning_advisor"],
        )

    if event == RequestEvent.GET_CURRENT_QUESTION:
        return _reject(
            snapshot=snapshot,
            reason="The interview is completed, so there is no current question.",
            error_code="INTERVIEW_COMPLETED",
            error_message="interview is completed",
        )

    return _reject(
        snapshot=snapshot,
        reason="The interview is completed and cannot accept more answers.",
        error_code="INTERVIEW_COMPLETED",
        error_message="interview is completed",
    )


def _route_waiting_main_answer(
    event: RequestEvent,
    snapshot: SessionSnapshot,
) -> OrchestratorDecision:
    if event == RequestEvent.GET_CURRENT_QUESTION:
        return _allow(
            snapshot=snapshot,
            action=OrchestratorAction.RETURN_MAIN_QUESTION,
            reason="The current turn is waiting for a main answer.",
            required_tools=["get_current_turn"],
        )

    if event == RequestEvent.SUBMIT_MAIN_ANSWER:
        return _allow(
            snapshot=snapshot,
            action=OrchestratorAction.ACCEPT_MAIN_ANSWER,
            reason="The current turn is waiting for a main answer and the answer is non-empty.",
            required_tools=["save_main_answer", "generate_followup"],
        )

    return _reject(
        snapshot=snapshot,
        reason="The current turn is waiting for a main answer, so this request is not allowed.",
        error_code="INVALID_TURN_STATUS",
        error_message="current turn is waiting for main answer",
    )


def _route_waiting_followup_answer(
    event: RequestEvent,
    snapshot: SessionSnapshot,
) -> OrchestratorDecision:
    if event in {
        RequestEvent.GET_CURRENT_QUESTION,
        RequestEvent.GET_FOLLOWUP_QUESTION,
    }:
        if not snapshot.has_followup_question:
            return _reject(
                snapshot=snapshot,
                reason="The current turn is waiting for a followup answer, but no followup question is available.",
                error_code="FOLLOWUP_NOT_AVAILABLE",
                error_message="followup question is not available",
            )

        return _allow(
            snapshot=snapshot,
            action=OrchestratorAction.RETURN_FOLLOWUP_QUESTION,
            reason="The current turn is waiting for a followup answer.",
            required_tools=["get_current_turn"],
        )

    if event == RequestEvent.SUBMIT_FOLLOWUP_ANSWER:
        return _allow(
            snapshot=snapshot,
            action=OrchestratorAction.ACCEPT_FOLLOWUP_ANSWER,
            reason="The current turn is waiting for a followup answer and the answer is non-empty.",
            required_tools=["save_followup_answer", "evaluate_turn"],
        )

    return _reject(
        snapshot=snapshot,
        reason="The current turn is waiting for a followup answer, so this request is not allowed.",
        error_code="INVALID_TURN_STATUS",
        error_message="current turn is waiting for followup answer",
    )


def _allow(
    action: OrchestratorAction,
    reason: str,
    snapshot: SessionSnapshot | None = None,
    required_tools: list[str] | None = None,
) -> OrchestratorDecision:
    return OrchestratorDecision(
        action=action,
        allowed=True,
        reason=reason,
        target_turn_index=snapshot.current_index if snapshot else None,
        required_tools=required_tools or [],
        confidence=1.0,
        needs_human_review=False,
    )


def _reject(
    reason: str,
    error_code: str,
    error_message: str,
    snapshot: SessionSnapshot | None = None,
) -> OrchestratorDecision:
    return OrchestratorDecision(
        action=OrchestratorAction.REJECT_INVALID_REQUEST,
        allowed=False,
        reason=reason,
        target_turn_index=snapshot.current_index if snapshot else None,
        required_tools=[],
        confidence=1.0,
        needs_human_review=False,
        error_code=error_code,
        error_message=error_message,
    )