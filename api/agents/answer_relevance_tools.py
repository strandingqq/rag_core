from api.agents.answer_relevance_schemas import (
    AnswerRelevanceContext,
    AnswerRelevanceResult,
)
from api.domain.models import InterviewSession, InterviewTurn


def build_answer_relevance_context(
    session: InterviewSession,
    turn: InterviewTurn,
    answer: str,
) -> AnswerRelevanceContext:
    question = session.plan.items[turn.index].question

    return AnswerRelevanceContext(
        session_id=session.session_id,
        user_id=session.user_id,
        turn_index=turn.index,
        question_id=turn.question_id,
        topic=turn.topic,
        difficulty=question.difficulty,
        main_question=turn.main_question,
        candidate_answer=answer.strip(),
        expected_answer=question.expected_answer or "",
    )


def validate_answer_relevance_result(result: AnswerRelevanceResult) -> None:
    if result.confidence < 0 or result.confidence > 1:
        raise ValueError("confidence must be between 0 and 1")

    if result.category == "answer":
        if result.suggested_action != "continue_interview":
            raise ValueError(
                "category=answer must use suggested_action=continue_interview"
            )
        return

    if result.suggested_action == "continue_interview":
        raise ValueError(
            "Only category=answer can use suggested_action=continue_interview"
        )

    if not result.response_to_user.strip():
        raise ValueError(
            "response_to_user is required when the answer should not continue"
        )