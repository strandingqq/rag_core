import random
import uuid
from typing import Any

from api.domain.models import InterviewPlan, InterviewPlanItem, Question
from api.errors import QuestionSelectionError
from api.infra.question_loader import parse_json_list


def build_interview_plan(
    db: Any,
    role: str,
    topics: list[str],
    num_questions: int,
    difficulty: str = "medium",
) -> InterviewPlan:
    """ 
    根据 知识点 和 难度 从 Chroma 中筛选题目，构建一次面试使用的题单计划。

    Args:
        db 、 topic 、 num_questions 、 difficulty
    Returns:
        InterviewPlan 对象
    """
    if not role or not role.strip():
        raise QuestionSelectionError("role cannot be empty")
    if not topics:
        raise QuestionSelectionError("topics cannot be empty")
    if num_questions < 1:
        raise QuestionSelectionError("num_questions must be greater than 0")

    all_candidate_ids: list[str] = []
    topic_to_ids: dict[str, list[str]] = {}

    for topic in topics:
        where = {
            "$and": [
                {"role": role},
                {"topic": topic},
                {"difficulty": difficulty},
            ]
        }
        result = db.get(where=where, include=["metadatas"])
        ids = result.get("ids", [])
        all_candidate_ids.extend(ids)
        topic_to_ids[topic] = ids

    all_candidate_ids = list(dict.fromkeys(all_candidate_ids))
    random.shuffle(all_candidate_ids)

    selected_ids: list[str] = []
    for topic in topics:
        for doc_id in topic_to_ids.get(topic, []):
            if len(selected_ids) >= num_questions:
                break
            if doc_id not in selected_ids:
                selected_ids.append(doc_id)
                break

    for doc_id in all_candidate_ids:
        if len(selected_ids) >= num_questions:
            break
        if doc_id not in selected_ids:
            selected_ids.append(doc_id)

    if len(selected_ids) < num_questions:
        raise QuestionSelectionError(
            f"Not enough questions for role={role}, topics={topics}, "
            f"difficulty={difficulty}. Required {num_questions}, got {len(selected_ids)}."
        )

    selected_result = db.get(ids=selected_ids, include=["documents", "metadatas"])
    ids = selected_result.get("ids", [])
    documents = selected_result.get("documents", [])
    metadatas = selected_result.get("metadatas", [])

    # 构造 InterviewPlanItem
    items: list[InterviewPlanItem] = []
    for index, (doc_id, document, metadata) in enumerate(
        zip(ids, documents, metadatas)
    ):
        # 注意哦 这里的metedata是可以get的 它是 dict类型
        # 但是document不是 它是完全的文字 组织过了的 无法进行数据获取
        metadata = metadata or {}
        question_id = metadata.get("question_id", doc_id)
        question_text = metadata.get("question") or document or ""
        topic = metadata.get("topic", "")
        question_role = metadata.get("role", role)
        question_difficulty = metadata.get("difficulty", difficulty)
        expected_answer = (
            metadata.get("expected_answer")
            or metadata.get("expect_answer")
            or ""
        )
        follow_up_angles = parse_json_list(metadata.get("follow_up_angles", "[]"))

        question = Question(
            question_id=question_id,
            role=question_role,
            topic=topic,
            difficulty=question_difficulty,
            question=question_text,
            expected_answer=expected_answer,
            follow_up_angles=follow_up_angles,
        )
        items.append(
            InterviewPlanItem(
                index=index,
                question_id=question_id,
                topic=topic,
                question=question,
            )
        )

    return InterviewPlan(
        plan_id=str(uuid.uuid4()),
        role=role,
        topics=topics,
        difficulty=difficulty,
        num_questions=num_questions,
        items=items,
    )

