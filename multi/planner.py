import random
import uuid
from question_loader import parse_json_list
from models import Question, InterviewPlanItem, InterviewPlan


""" 
题单的生成

build_interview_plan 根据知识点和难度 构建题单
"""
def build_interview_plan(db, topics: list[str], num_questions, difficulty: str="medium") -> InterviewPlan:
    """ 
    根据 知识点 和 难度 从 Chroma 中筛选题目，构建一次面试使用的题单计划。

    Args:
        db 、 topic 、 num_questions 、 difficulty
    Returns:
        InterviewPlan 对象
    """
    random_seed = 1
    rng = random.Random(random_seed)
    all_candidate_ids: list[str] = []
    topic_to_ids: dict[str, list[str]] = {}
    for topic in topics:
        where = {
            "$and":[
                {"topic":topic},
                {"difficulty":difficulty}
            ]
        }
        result = db.get(where = where,
                        include = ["metadatas"])
        ids = result.get("ids",[])
        all_candidate_ids.extend(ids)
        topic_to_ids[topic] = ids
    all_candidate_ids = list(dict.fromkeys(all_candidate_ids))
    random.shuffle(all_candidate_ids)
    selected_ids: list[str] = []
    for topic in topics:
        ids = topic_to_ids.get(topic, [])
        for doc_id in ids:
            if len(selected_ids) >= num_questions:
                break
            if doc_id not in selected_ids:
                selected_ids.append(doc_id)
                break
    # 如果未满数量
    for doc_id in all_candidate_ids:
        if len(selected_ids) >= num_questions:
            break
        if doc_id not in selected_ids:
            selected_ids.append(doc_id)
    if len(selected_ids) < num_questions:
        print("剩余题目数量不足")

    selected_result = db.get(
        ids = selected_ids,
        include = ["documents", "metadatas"]
    )
    ids = selected_result.get("ids",[])
    documents = selected_result.get("documents", [])
    metadatas = selected_result.get("metadatas", [])

    # 构造 InterviewPlanItem
    items = []
    for index, (doc_id, document, metadata) in enumerate(
        zip(ids, documents, metadatas)
    ):
        # 注意哦 这里的metedata是可以get的 它是 dict类型
        # 但是document不是 它是完全的文字 组织过了的 无法进行数据获取
        metadata = metadata or {}
        question_id = metadata.get("question_id",doc_id)
        question_text = metadata.get("question", None)
        topic = metadata.get("topic", "")
        difficult = metadata.get("difficulty", "")
        expected_answer = metadata.get("expect_answer", "")
        follow_up_angles = parse_json_list(metadata.get("follow_up_angles", "[]"))
        question = Question(
            question_id = question_id,
            topic = topic,
            difficulty = difficult,
            question = question_text,
            expected_answer=expected_answer,
            follow_up_angles=follow_up_angles,
        )
        item = InterviewPlanItem(
            index = index, # 1-5 题目序号索引
            question_id = question_id,
            topic = topic,
            question = question
        )
        items.append(item)
    return InterviewPlan(
        plan_id = str(uuid.uuid4()),
        topics = topics,
        num_questions = num_questions,
        items = items
    )