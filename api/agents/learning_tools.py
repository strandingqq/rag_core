from api.domain.models import InterviewSession
from typing import Any


def _unique_strings(values: list[Any]) -> list[str]:
    result = []
    seen = set()

    for value in values:
        text = str(value).strip()
        if not text:
            continue
        if text in seen:
            continue

        seen.add(text)
        result.append(text)

    return result

def _build_action_reason(weak_topic: dict[str, Any]) -> str:
    topic = weak_topic["topic"]
    average_score = weak_topic.get("average_score")
    severity = weak_topic.get("severity")
    evidence = weak_topic.get("evidence", {})

    missing_count = len(evidence.get("missing_points", []))
    mistake_count = len(evidence.get("mistakes", []))

    if severity == "high":
        return (
            f"{topic} 平均分为 {average_score}，低于及格稳定线，"
            f"并暴露出 {missing_count} 个缺失点、{mistake_count} 个错误点。"
        )

    if severity == "medium":
        return (
            f"{topic} 平均分为 {average_score}，还不够稳定，"
            f"需要优先补齐 {missing_count} 个缺失点。"
        )

    return (
        f"{topic} 分数不算最低，但仍出现了可改进点，"
        f"建议通过针对性练习巩固。"
    )

def build_session_snapshot(session: InterviewSession) -> dict:
    """ 
    把完整的InterviewSession 精简成为一个dict
    得到完整的session快照
    """
    turns = []
    for turn in session.turns:
        evaluation = turn.evaluation

        turns.append(
            {
                "index": turn.index,
                "question_id": turn.question_id,
                "topic": turn.topic,
                "status": turn.status,
                "main_question": turn.main_question,
                "main_answer": turn.main_answer or "",
                "followup_question": turn.followup_question or "",
                "followup_answer": turn.followup_answer or "",
                "score": turn.score,
                "reason": evaluation.reason if evaluation else "",
                "hit_points": evaluation.hit_points if evaluation else [],
                "missing_points": evaluation.missing_points if evaluation else [],
                "mistakes": evaluation.mistakes if evaluation else [],
                "suggestion": evaluation.suggestion if evaluation else None,
            }
        )

    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "status": session.status,
        "role": session.plan.role,
        "topics": session.plan.topics,
        "difficulty": session.plan.difficulty,
        "current_index": session.current_index,
        "total_questions": len(session.turns),
        "turns": turns,
    }

def calculate_topic_performance(session: InterviewSession) -> list[dict]:
    """ 
    按照topic 聚合分数和表现
    让agent知道 哪个知识点整体弱 而不是单题
    """
    topic_map : dict[str, dict[str, Any]] = {} 
    # 这是收集所有 topic 对应题目的记录 用于最终结果result的汇总计算
    for turn in session.turns:
        if turn.score is None:
            continue
        topic = turn.topic or "unknown"
        if topic not in topic_map:
            topic_map[topic] = {
                "topic": topic,
                "scores": [],
                "question_ids": [],
                "missing_points": [],
                "mistakes": [],
                "suggestions": [],
            }

        item = topic_map[topic]
        item["scores"].append(turn.score)
        item["question_ids"].append(turn.question_id)

        if turn.evaluation:
            item["missing_points"].extend(turn.evaluation.missing_points)
            item["mistakes"].extend(turn.evaluation.mistakes)
            if turn.evaluation.suggestion:
                item["suggestions"].append(turn.evaluation.suggestion)

    results = []
    for item in topic_map.values():
        scores = item["scores"]
        average_score = round(sum(scores) / len(scores), 1) if scores else 0.0

        results.append(
        {
            "topic": item["topic"],
            "average_score": average_score,
            "min_score": min(scores) if scores else None,
            "max_score": max(scores) if scores else None,
            "question_count": len(scores),
            "question_ids": item["question_ids"],
            "missing_points": _unique_strings(item["missing_points"]),
            "mistakes": _unique_strings(item["mistakes"]),
            "suggestions": _unique_strings(item["suggestions"]),
        }
    )
    return sorted(results, key=lambda x: x["average_score"])




def identify_weak_topics(topic_performance: list[dict], threshold: int = 70) -> list[dict]:
    """ 
    从topic中找出薄弱知识点
    整理成为新的数据结构
    """
    weak_topics = []

    for item in topic_performance:
        average_score = item.get("average_score", 0)
        mistakes = item.get("mistakes", [])
        missing_points = item.get("missing_points", [])

        is_low_score = average_score < threshold
        has_clear_mistakes = len(mistakes) > 0
        has_missing_points = len(missing_points) > 0

        if not (is_low_score or has_clear_mistakes or has_missing_points):
            continue

        if average_score < 60:
            severity = "high"
        elif average_score < threshold:
            severity = "medium"
        else:
            severity = "low"

        weak_topics.append(
            {
                "topic": item["topic"],
                "severity": severity,
                "average_score": average_score,
                "question_count": item.get("question_count", 0),
                "evidence": {
                    "question_ids": item.get("question_ids", []),
                    "missing_points": missing_points,
                    "mistakes": mistakes,
                    "suggestions": item.get("suggestions", []),
                },
            }
        )

    return weak_topics


def build_rule_based_actions(weak_topics: list[dict]) -> list[dict]:
    """ 
    根据薄弱topic 先生成一版 学习建议 先用规则型
    """
    actions = []
    for weak_topic in weak_topics:
        topic = weak_topic["topic"]
        severity = weak_topic["severity"]
        evidence = weak_topic.get("evidence", {})
        missing_points = evidence.get("missing_points", [])
        mistakes = evidence.get("mistakes", [])
        suggestions = evidence.get("suggestions", [])

        topic_actions = []

        if missing_points:
            topic_actions.append(
                "复习并补齐这些缺失点："
                + "；".join(missing_points[:3])
            )

        if mistakes:
            topic_actions.append(
                "重点纠正这些错误理解："
                + "；".join(mistakes[:3])
            )

        if suggestions:
            topic_actions.append(
                "根据面试反馈练习："
                + "；".join(suggestions[:2])
            )

        if not topic_actions:
            topic_actions.append(f"重新梳理 {topic} 的核心概念、典型场景和常见边界问题。")

        actions.append(
            {
                "topic": topic,
                "priority": severity,
                "reason": _build_action_reason(weak_topic),
                "actions": topic_actions,
                "resources": [],
            }
        )

    return actions