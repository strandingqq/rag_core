import unittest

from api.agents.orchestrator import run_orchestrator
from api.agents.orchestrator_schemas import OrchestratorAction, RequestEvent
from api.domain.models import (
    EvaluationResult,
    InterviewPlan,
    InterviewPlanItem,
    InterviewSession,
    InterviewTurn,
    Question,
)


def make_session(
    session_status: str = "in_progress",
    turn_status: str = "waiting_main_answer",
    final_report: dict | None = None,
) -> InterviewSession:
    question = Question(
        question_id="q-1",
        role="frontend",
        topic="React",
        difficulty="medium",
        question="请解释 useEffect 的依赖数组。",
    )
    plan = InterviewPlan(
        plan_id="plan-1",
        role="frontend",
        topics=["React"],
        difficulty="medium",
        num_questions=1,
        items=[
            InterviewPlanItem(
                index=0,
                question_id=question.question_id,
                topic=question.topic,
                question=question,
            )
        ],
    )
    turn = InterviewTurn(
        index=0,
        question_id=question.question_id,
        topic=question.topic,
        main_question=question.question,
        status=turn_status,
    )

    if turn_status == "waiting_followup_answer":
        turn.main_answer = "useEffect 会在组件渲染后执行。"
        turn.followup_question = "空数组和不传依赖数组有什么区别？"

    if turn_status == "completed":
        turn.main_answer = "useEffect 会在组件渲染后执行。"
        turn.followup_question = "空数组和不传依赖数组有什么区别？"
        turn.followup_answer = "空数组只执行一次，不传依赖数组每次渲染后都执行。"
        turn.score = 85
        turn.evaluation = EvaluationResult(
            score=85,
            reason="回答覆盖了核心概念。",
        )

    return InterviewSession(
        session_id="session-1",
        user_id="user-1",
        plan=plan,
        current_index=0,
        created_time="2026-09-13T00:00:00",
        updated_time="2026-09-13T00:00:00",
        finished_time=(
            "2026-09-13T00:10:00" if session_status == "completed" else None
        ),
        final_report=final_report or {},
        turns=[turn],
        status=session_status,
    )


class OrchestratorTest(unittest.TestCase):
    def test_create_interview_can_create_plan_without_session(self) -> None:
        decision = run_orchestrator(RequestEvent.CREATE_INTERVIEW)

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.action, OrchestratorAction.CREATE_PLAN)

    def test_session_required_for_non_create_event(self) -> None:
        decision = run_orchestrator(RequestEvent.GET_CURRENT_QUESTION)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.action, OrchestratorAction.REJECT_INVALID_REQUEST)
        self.assertEqual(decision.error_code, "SESSION_REQUIRED")

    def test_waiting_main_answer_can_return_main_question(self) -> None:
        session = make_session(turn_status="waiting_main_answer")

        decision = run_orchestrator(
            RequestEvent.GET_CURRENT_QUESTION,
            session=session,
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.action, OrchestratorAction.RETURN_MAIN_QUESTION)

    def test_waiting_main_answer_can_accept_main_answer(self) -> None:
        session = make_session(turn_status="waiting_main_answer")

        decision = run_orchestrator(
            RequestEvent.SUBMIT_MAIN_ANSWER,
            session=session,
            answer="useEffect 会在组件渲染后执行。",
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.action, OrchestratorAction.ACCEPT_MAIN_ANSWER)
        self.assertIn("generate_followup", decision.required_tools)

    def test_empty_main_answer_is_rejected(self) -> None:
        session = make_session(turn_status="waiting_main_answer")

        decision = run_orchestrator(
            RequestEvent.SUBMIT_MAIN_ANSWER,
            session=session,
            answer=" ",
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.action, OrchestratorAction.REJECT_INVALID_REQUEST)
        self.assertEqual(decision.error_code, "EMPTY_ANSWER")

    def test_followup_question_before_main_answer_is_rejected(self) -> None:
        session = make_session(turn_status="waiting_main_answer")

        decision = run_orchestrator(
            RequestEvent.GET_FOLLOWUP_QUESTION,
            session=session,
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.action, OrchestratorAction.REJECT_INVALID_REQUEST)
        self.assertEqual(decision.error_code, "INVALID_TURN_STATUS")

    def test_waiting_followup_answer_can_return_followup_question(self) -> None:
        session = make_session(turn_status="waiting_followup_answer")

        decision = run_orchestrator(
            RequestEvent.GET_FOLLOWUP_QUESTION,
            session=session,
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(
            decision.action,
            OrchestratorAction.RETURN_FOLLOWUP_QUESTION,
        )

    def test_waiting_followup_answer_can_accept_followup_answer(self) -> None:
        session = make_session(turn_status="waiting_followup_answer")

        decision = run_orchestrator(
            RequestEvent.SUBMIT_FOLLOWUP_ANSWER,
            session=session,
            answer="空数组只执行一次。",
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(
            decision.action,
            OrchestratorAction.ACCEPT_FOLLOWUP_ANSWER,
        )

    def test_completed_session_can_return_report_when_available(self) -> None:
        session = make_session(
            session_status="completed",
            turn_status="completed",
            final_report={"summary": "整体表现良好。"},
        )

        decision = run_orchestrator(
            RequestEvent.GET_REPORT,
            session=session,
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.action, OrchestratorAction.RETURN_REPORT)

    def test_completed_session_rejects_main_answer(self) -> None:
        session = make_session(
            session_status="completed",
            turn_status="completed",
            final_report={"summary": "整体表现良好。"},
        )

        decision = run_orchestrator(
            RequestEvent.SUBMIT_MAIN_ANSWER,
            session=session,
            answer="新的回答",
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.action, OrchestratorAction.REJECT_INVALID_REQUEST)
        self.assertEqual(decision.error_code, "INTERVIEW_COMPLETED")


if __name__ == "__main__":
    unittest.main()
