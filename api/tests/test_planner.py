import unittest

from api.errors import QuestionSelectionError
from api.services.planner import build_interview_plan


class FakeQuestionDb:
    def __init__(self) -> None:
        self.where_calls = []
        self.metadata_by_id = {
            "react-1": {
                "question_id": "q-react-1",
                "role": "frontend",
                "topic": "React",
                "difficulty": "medium",
                "question": "请解释 useEffect 的依赖数组。",
                "expected_answer": "依赖数组用于控制副作用重新执行时机。",
                "follow_up_angles": '["空数组和不传数组的区别"]',
            },
            "js-1": {
                "question_id": "q-js-1",
                "role": "frontend",
                "topic": "JavaScript",
                "difficulty": "medium",
                "question": "请解释闭包。",
                "expected_answer": "闭包可以访问外层函数作用域。",
                "follow_up_angles": "[]",
            },
        }

    def get(self, where=None, include=None, ids=None):
        if where is not None:
            self.where_calls.append(where)
            filters = {}
            for item in where.get("$and", []):
                filters.update(item)

            matched_ids = [
                doc_id
                for doc_id, metadata in self.metadata_by_id.items()
                if metadata["role"] == filters.get("role")
                and metadata["topic"] == filters.get("topic")
                and metadata["difficulty"] == filters.get("difficulty")
            ]
            return {"ids": matched_ids}

        if ids is not None:
            metadatas = [self.metadata_by_id[doc_id] for doc_id in ids]
            documents = [metadata["question"] for metadata in metadatas]
            return {
                "ids": ids,
                "documents": documents,
                "metadatas": metadatas,
            }

        return {"ids": []}


class PlannerTest(unittest.TestCase):
    def test_build_plan_filters_by_role_topic_and_difficulty(self) -> None:
        db = FakeQuestionDb()

        plan = build_interview_plan(
            db=db,
            role="frontend",
            topics=["React", "JavaScript"],
            num_questions=2,
            difficulty="medium",
        )

        self.assertEqual(plan.role, "frontend")
        self.assertEqual(plan.difficulty, "medium")
        self.assertEqual(len(plan.items), 2)
        self.assertEqual(plan.items[0].question.question_id, "q-react-1")
        self.assertEqual(plan.items[1].question.question_id, "q-js-1")
        self.assertIn({"role": "frontend"}, db.where_calls[0]["$and"])
        self.assertIn({"topic": "React"}, db.where_calls[0]["$and"])
        self.assertIn({"difficulty": "medium"}, db.where_calls[0]["$and"])

    def test_build_plan_raises_when_questions_are_not_enough(self) -> None:
        db = FakeQuestionDb()

        with self.assertRaises(QuestionSelectionError):
            build_interview_plan(
                db=db,
                role="backend",
                topics=["React"],
                num_questions=1,
                difficulty="medium",
            )


if __name__ == "__main__":
    unittest.main()

