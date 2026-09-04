import unittest

from api.domain.models import InterviewPlan, InterviewSession
from api.errors import SessionNotFoundError
from api.session_store import clear_sessions, get_session, save_session, update_session


def make_session(session_id: str = "session-1") -> InterviewSession:
    plan = InterviewPlan(
        plan_id="plan-1",
        role="frontend",
        topics=["React"],
        difficulty="medium",
        num_questions=0,
        items=[],
    )
    return InterviewSession(
        session_id=session_id,
        user_id="user-1",
        plan=plan,
        current_index=0,
        created_time="2026-08-03T00:00:00",
        updated_time="2026-08-03T00:00:00",
        status="in_progress",
    )


class SessionStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        clear_sessions()

    def tearDown(self) -> None:
        clear_sessions()

    def test_save_and_get_session(self) -> None:
        session = make_session()

        save_session(session)

        self.assertIs(get_session(session.session_id), session)

    def test_get_missing_session_raises(self) -> None:
        with self.assertRaises(SessionNotFoundError):
            get_session("missing")

    def test_update_existing_session(self) -> None:
        session = make_session()
        save_session(session)

        session.status = "completed"
        update_session(session)

        self.assertEqual(get_session(session.session_id).status, "completed")

    def test_update_missing_session_raises(self) -> None:
        with self.assertRaises(SessionNotFoundError):
            update_session(make_session("missing"))


if __name__ == "__main__":
    unittest.main()

