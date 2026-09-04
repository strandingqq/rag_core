import unittest

from fastapi.testclient import TestClient

from api.domain.models import EvaluationResult, InterviewReport
from api.main import app
from api.services import interview_service
from api.session_store import clear_sessions


class FakeQuestionDb:
    def get(self, where=None, include=None, ids=None):
        if where is not None:
            return {"ids": ["react-1"]}

        if ids is not None:
            return {
                "ids": ids,
                "documents": ["请解释 React useEffect 的依赖数组有什么作用？"],
                "metadatas": [
                    {
                        "question_id": "q-react-1",
                        "role": "frontend",
                        "topic": "React",
                        "difficulty": "medium",
                        "question": "请解释 React useEffect 的依赖数组有什么作用？",
                        "expected_answer": "依赖数组控制 effect 重新执行的时机。",
                        "follow_up_angles": '["空数组和不传依赖数组的区别"]',
                    }
                ],
            }

        return {"ids": []}


def fake_generate_followup_question(turn, materials, llm=None) -> str:
    return "如果依赖数组为空和不传依赖数组有什么区别？"


def fake_evaluate_turn(turn, materials, llm=None) -> EvaluationResult:
    return EvaluationResult(
        score=85,
        reason="回答覆盖了核心概念。",
        hit_points=["理解依赖数组"],
        missing_points=[],
        mistakes=[],
        suggestion="可以补充更多边界场景。",
    )


def fake_generate_interview_report(session, llm=None) -> InterviewReport:
    return InterviewReport(
        session_id=session.session_id,
        user_id=session.user_id,
        total_score=85.0,
        level="良好",
        summary="整体表现良好。",
        turn_summaries=[],
    )


class InterviewApiTest(unittest.TestCase):
    def setUp(self) -> None:
        clear_sessions()
        self.client = TestClient(app)
        self.original_get_db = interview_service.get_db
        self.original_get_llm = interview_service.get_llm
        self.original_generate_followup_question = (
            interview_service.generate_followup_question
        )
        self.original_evaluate_turn = interview_service.evaluate_turn
        self.original_generate_interview_report = (
            interview_service.generate_interview_report
        )

        interview_service.get_db = lambda: FakeQuestionDb()
        interview_service.get_llm = lambda: object()
        interview_service.generate_followup_question = fake_generate_followup_question
        interview_service.evaluate_turn = fake_evaluate_turn
        interview_service.generate_interview_report = fake_generate_interview_report

    def tearDown(self) -> None:
        interview_service.get_db = self.original_get_db
        interview_service.get_llm = self.original_get_llm
        interview_service.generate_followup_question = (
            self.original_generate_followup_question
        )
        interview_service.evaluate_turn = self.original_evaluate_turn
        interview_service.generate_interview_report = (
            self.original_generate_interview_report
        )
        clear_sessions()

    def test_full_one_question_interview_flow(self) -> None:
        create_response = self.client.post(
            "/interviews",
            json={
                "user_id": "test_user",
                "role": "frontend",
                "topics": ["React"],
                "difficulty": "medium",
                "num_questions": 1,
            },
        )
        self.assertEqual(create_response.status_code, 201)
        create_data = create_response.json()
        session_id = create_data["session_id"]
        self.assertEqual(create_data["status"], "in_progress")
        self.assertEqual(create_data["current_index"], 0)
        self.assertEqual(create_data["total_questions"], 1)
        self.assertIn("useEffect", create_data["current_question"])

        current_response = self.client.get(
            f"/interviews/{session_id}/current-question"
        )
        self.assertEqual(current_response.status_code, 200)
        self.assertEqual(current_response.json()["question_type"], "main")

        main_answer_response = self.client.post(
            f"/interviews/{session_id}/main-answer",
            json={
                "answer": "useEffect 会在组件渲染后执行，依赖数组控制重新执行时机。"
            },
        )
        self.assertEqual(main_answer_response.status_code, 200)
        self.assertEqual(
            main_answer_response.json()["turn_status"],
            "waiting_followup_answer",
        )

        followup_response = self.client.get(
            f"/interviews/{session_id}/followup-question"
        )
        self.assertEqual(followup_response.status_code, 200)
        self.assertEqual(followup_response.json()["question_type"], "followup")

        followup_answer_response = self.client.post(
            f"/interviews/{session_id}/followup-answer",
            json={"answer": "空数组只执行一次，不传数组每次渲染后都执行。"},
        )
        self.assertEqual(followup_answer_response.status_code, 200)
        self.assertEqual(followup_answer_response.json()["status"], "completed")
        self.assertEqual(followup_answer_response.json()["score"], 85)
        self.assertIsNone(followup_answer_response.json()["next_question"])

        report_response = self.client.get(f"/interviews/{session_id}/report")
        self.assertEqual(report_response.status_code, 200)
        self.assertEqual(report_response.json()["status"], "completed")
        self.assertEqual(report_response.json()["report"]["total_score"], 85.0)

    def test_missing_session_returns_404(self) -> None:
        response = self.client.get("/interviews/missing/current-question")

        self.assertEqual(response.status_code, 404)

    def test_followup_question_before_main_answer_returns_409(self) -> None:
        create_response = self.client.post(
            "/interviews",
            json={
                "user_id": "test_user",
                "role": "frontend",
                "topics": ["React"],
                "difficulty": "medium",
                "num_questions": 1,
            },
        )
        session_id = create_response.json()["session_id"]

        response = self.client.get(f"/interviews/{session_id}/followup-question")

        self.assertEqual(response.status_code, 409)


if __name__ == "__main__":
    unittest.main()

