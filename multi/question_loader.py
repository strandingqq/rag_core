from langchain_core.documents import Document
import json
from pathlib import Path

""" 
负责将 文件 - document & ids 准备好入库所需内容

load_jsonl 将jsonl文件读入内存中
json_to_question_document 将json文件每一行组织为document
load_documents_and_ids_from_jsonl 将指定路径的所有json文件 组织为document  返回一个list[dict] 包括id和document
"""
def load_jsonl(path) -> list[dict]:
    rows  = []
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows

def json_to_question_document(obj: dict, source_file: str) -> Document:
    """
    把 _questions.jsonl 的一行转换成题目 Document。
    用于 interview_questions collection。
    """
    question_id = obj.get("question_id", "")
    role = obj.get("role", "")
    topic = obj.get("topic", "")
    topic_id = obj.get("topic_id", "")
    question_type = obj.get("question_type", "")
    difficulty = obj.get("difficulty", "")
    question = obj.get("question", "")
    expected_answer = obj.get("expected_answer", "")
    reference_points = obj.get("reference_points", [])
    follow_up_angles = obj.get("follow_up_angles", [])
    common_mistakes = obj.get("common_mistakes", [])
    tags = obj.get("tags", [])
    assesses_topic_ids = obj.get("assesses_topic_ids", [])

    page_content = (
        f"[文档类型]: interview_question\n"
        f"[题目ID]: {question_id}\n"
        f"[岗位]: {role}\n"
        f"[知识点]: {topic}\n"
        f"[主题ID]: {topic_id}\n"
        f"[题型]: {question_type}\n"
        f"[难度]: {difficulty}\n"
        f"[题目]: {question}\n"
        f"[参考答案]: {expected_answer}\n"
        # f"[评分要点]: {_join_list(reference_points)}\n"
        # f"[追问方向]: {_join_list(follow_up_angles)}\n"
        # f"[常见错误]: {_join_list(common_mistakes)}\n"
        # f"[考察主题]: {_join_list(assesses_topic_ids)}\n"
        # f"[标签]: {_join_list(tags)}\n"
    )

    metadata = {
        "doc_type": "interview_question",
        "source": source_file,
        "question_id": question_id,
        "question": question, 
        "role": role,
        "topic": topic,
        "topic_id": topic_id,
        "question_type": question_type,
        "difficulty": difficulty,
        "source_file": obj.get("source_file", source_file),
        "source_line": int(obj.get("source_line", 0) or 0),
        "expect_answer": expected_answer,
        "follow_up_angles": json.dumps(follow_up_angles, ensure_ascii=False),
    }

    return Document(page_content=page_content, metadata=metadata)

def load_documents_and_ids_from_jsonl(file_path:Path) -> list[dict]:
    """
    打开文件地址，读取文件内容，并把每一行的 JSON 字符串转换成 Document 对象，最后返回一个 Document 对象的列表。
    """
    documents = []
    ids = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            doc = json_to_question_document(obj,source_file=file_path.name)
            documents.append(doc)
            doc_id = f"{file_path.stem}_{len(documents)}"
            ids.append(doc_id)
            
    return documents,ids


def parse_json_list(value) -> list[str]:
    """ 
    把 None、list、JSON 字符串或普通字符串统一转换成字符串列表。
    """
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value]
    if isinstance(value, str):
        if not value.strip():
            return []
        try:
            data = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        if isinstance(data, list):
            return [str(x) for x in data]
        return [str(data)]
    return [str(value)]