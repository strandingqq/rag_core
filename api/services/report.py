import json
from dataclasses import asdict
from typing import Any

from api.domain.models import InterviewReport, InterviewSession, TurnSummary
from api.infra.llm import build_llm
from api.infra.prompts import generate_interview_report_prompt


def ensure_session_completed(session: InterviewSession) -> None:
    if session.status != "completed":
        raise ValueError("interview is not completed")
    if not session.turns:
        raise ValueError("session has no turns")
    for turn in session.turns:
        if turn.status != "completed":
            raise ValueError(
                f"turn {turn.index + 1} is not completed: {turn.status}"
            )
        if turn.evaluation is None:
            raise ValueError(f"turn {turn.index + 1} has no evaluation")
        if turn.score is None:
            raise ValueError(f"turn {turn.index + 1} has no score")


def build_turn_summaries(session: InterviewSession) -> list[TurnSummary]:
    summaries: list[TurnSummary] = []
    for turn in session.turns:
        if turn.evaluation is None or turn.score is None:
            raise ValueError(f"turn {turn.index + 1} has not been evaluated")
        summaries.append(
            TurnSummary(
                index=turn.index,
                question_id=turn.question_id,
                topic=turn.topic,
                score=turn.score,
                main_question=turn.main_question,
                main_answer=turn.main_answer or "",
                followup_question=turn.followup_question or "",
                followup_answer=turn.followup_answer or "",
                reason=turn.evaluation.reason,
                hit_points=turn.evaluation.hit_points,
                missing_points=turn.evaluation.missing_points,
                mistakes=turn.evaluation.mistakes,
                suggestion=turn.evaluation.suggestion,
            )
        )
    return summaries


def calculate_total_score(turn_summaries: list[TurnSummary]) -> float:
    if not turn_summaries:
        return 0.0
    return round(sum(turn.score for turn in turn_summaries) / len(turn_summaries), 1)


def score_to_level(score: float) -> str:
    if score >= 90:
        return "优秀"
    if score >= 80:
        return "良好"
    if score >= 70:
        return "中等偏上"
    if score >= 60:
        return "及格但不稳定"
    return "需要系统补强"


def generate_report_summary(
    turn_summaries: list[TurnSummary],
    total_score: float,
    level: str,
    llm: Any | None = None,
) -> str:
    from langchain_core.prompts import ChatPromptTemplate

    llm = llm or build_llm()
    report_data = {
        "total_score": total_score,
        "level": level,
        "turn_summaries": [asdict(turn) for turn in turn_summaries],
    }
    prompt = ChatPromptTemplate.from_template(generate_interview_report_prompt)
    chain = prompt | llm
    response = chain.invoke(
        {"report_data": json.dumps(report_data, ensure_ascii=False, indent=2)}
    )
    return response.content.strip()


def generate_interview_report(
    session: InterviewSession,
    llm: Any | None = None,
) -> InterviewReport:
    ensure_session_completed(session)
    turn_summaries = build_turn_summaries(session)
    total_score = calculate_total_score(turn_summaries)
    level = score_to_level(total_score)
    summary = generate_report_summary(
        turn_summaries=turn_summaries,
        total_score=total_score,
        level=level,
        llm=llm,
    )
    return InterviewReport(
        session_id=session.session_id,
        user_id=session.user_id,
        total_score=total_score,
        level=level,
        summary=summary,
        turn_summaries=turn_summaries,
    )

