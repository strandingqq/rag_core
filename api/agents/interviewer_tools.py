from api.agents.interviewer_schemas import InterviewerContext, InterviewerOutput
from api.domain.models import InterviewSession, InterviewTurn


def build_interviewer_context(
    session: InterviewSession,
    turn: InterviewTurn,
) -> InterviewerContext:
    """ 
    从 session 取数据 构建InterviewContext
    """
    question = session.plan.items[turn.index].question

    return InterviewerContext(
        session_id=session.session_id,
        user_id=session.user_id,
        turn_index=turn.index,
        question_id=turn.question_id,
        topic=turn.topic,
        difficulty=question.difficulty,
        main_question=turn.main_question,
        main_answer=turn.main_answer or "",
        expected_answer=question.expected_answer or "",
        follow_up_angles=question.follow_up_angles,
        previous_turn_summary=build_previous_turn_summary(session, turn.index),
    )


def build_previous_turn_summary(
    session: InterviewSession,
    current_index: int,
) -> str:
    """ 
    整理 previous turns
    """
    completed_turns = [
        turn
        for turn in session.turns[:current_index]
        if turn.status == "completed"
    ]

    if not completed_turns:
        return "无"

    lines = []
    for turn in completed_turns[-3:]:
        score = turn.score if turn.score is not None else "无"
        reason = turn.evaluation.reason if turn.evaluation else "无"
        lines.append(
            f"第 {turn.index + 1} 题，topic={turn.topic}，score={score}，reason={reason}"
        )

    return "\n".join(lines)


def format_follow_up_angles(angles: list[str]) -> str:
    """ 
    格式化追问方向
    """
    if not angles:
        return "无"

    return "\n".join(
        f"{index}. {angle}"
        for index, angle in enumerate(angles, start=1)
    )


def validate_interviewer_output(output: InterviewerOutput) -> None:
    """ 
    校验 agent 输出
    """
    question = output.followup_question.strip()

    if not question:
        raise ValueError("followup_question cannot be empty")

    question_mark_count = question.count("?") + question.count("？")
    if question_mark_count > 1:
        raise ValueError("followup_question should contain only one question")

    if not output.target_gap.strip():
        raise ValueError("target_gap cannot be empty")

    if not output.reason.strip():
        raise ValueError("reason cannot be empty")

    if output.confidence < 0 or output.confidence > 1:
        raise ValueError("confidence must be between 0 and 1")