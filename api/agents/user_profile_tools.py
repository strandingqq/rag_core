from dataclasses import asdict
from typing import Any

from api.agents.user_profile_schemas import (
    UserProfileContext,
    UserProfilePatch,
    UserProfileTurnSummary,
)
from api.domain.models import InterviewReport, InterviewSession, TurnSummary


def build_user_profile_context_from_report(
    report: InterviewReport,
    session: InterviewSession,
    learning_advice_summary: str = "",
) -> UserProfileContext:
    """ 
    从 report/session 构造 UserProfileContext
    """
    role = getattr(session.plan, "role", "")
    topics = list(session.plan.topics)

    return UserProfileContext(
        user_id=session.user_id,
        session_id=session.session_id,
        role=role,
        topics=topics,
        total_score=report.total_score,
        level=report.level,
        turn_summaries=[
            build_turn_summary_for_profile(turn)
            for turn in report.turn_summaries
        ],
        learning_advice_summary=learning_advice_summary,
    )


def build_user_profile_context_from_dict(
    report_data: dict[str, Any],
    session: InterviewSession,
    learning_advice_summary: str = "",
) -> UserProfileContext:
    """ 
    兼容 report 是 dataclass 或 dict 的情况
    """
    role = getattr(session.plan, "role", "")
    topics = list(session.plan.topics)

    turn_summaries = []
    for item in report_data.get("turn_summaries", []):
        turn_summaries.append(
            UserProfileTurnSummary(
                index=int(item.get("index", 0)),
                question_id=str(item.get("question_id", "")),
                topic=str(item.get("topic", "")),
                score=int(item.get("score", 0)),
                reason=str(item.get("reason", "")),
                hit_points=[str(x) for x in item.get("hit_points", [])],
                missing_points=[str(x) for x in item.get("missing_points", [])],
                mistakes=[str(x) for x in item.get("mistakes", [])],
                suggestion=item.get("suggestion"),
            )
        )

    return UserProfileContext(
        user_id=session.user_id,
        session_id=session.session_id,
        role=role,
        topics=topics,
        total_score=float(report_data.get("total_score", 0)),
        level=str(report_data.get("level", "")),
        turn_summaries=turn_summaries,
        learning_advice_summary=learning_advice_summary,
    )


def build_turn_summary_for_profile(
    turn: TurnSummary,
) -> UserProfileTurnSummary:
    """
    把一道题Turn记录 压缩成 UserProfileTurnSummary
    多个TurnSummary 组织成UserProfileContext 也就是agent输入
    """
    data = asdict(turn)

    return UserProfileTurnSummary(
        index=int(data.get("index", 0)),
        question_id=str(data.get("question_id", "")),
        topic=str(data.get("topic", "")),
        score=int(data.get("score", 0)),
        reason=str(data.get("reason", "")),
        hit_points=[str(x) for x in data.get("hit_points", [])],
        missing_points=[str(x) for x in data.get("missing_points", [])],
        mistakes=[str(x) for x in data.get("mistakes", [])],
        suggestion=data.get("suggestion"),
    )


def validate_user_profile_patch(patch: UserProfilePatch) -> None:
    """ 
    校验 UserProfilePatch 是否合理
    """
    if patch.confidence < 0 or patch.confidence > 1:
        raise ValueError("confidence must be between 0 and 1")

    if not patch.summary.strip():
        raise ValueError("summary cannot be empty")

    for topic in patch.weak_topics + patch.strong_topics:
        if not topic.strip():
            raise ValueError("topic cannot be empty")

    for topic, score in patch.latest_scores.items():
        if not topic.strip():
            raise ValueError("latest_scores topic cannot be empty")
        if score < 0 or score > 100:
            raise ValueError("latest_scores score must be between 0 and 100")