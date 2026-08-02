import json
from pathlib import Path
from typing import Any


def load_jsonl(path: Path | str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def json_to_question_document(obj: dict[str, Any], source_file: str) -> Any:
    from langchain_core.documents import Document

    question_id = obj.get("question_id", "")
    role = obj.get("role", "")
    topic = obj.get("topic", "")
    topic_id = obj.get("topic_id", "")
    question_type = obj.get("question_type", "")
    difficulty = obj.get("difficulty", "")
    question = obj.get("question", "")
    expected_answer = obj.get("expected_answer", "")
    follow_up_angles = obj.get("follow_up_angles", [])

    page_content = (
        "[文档类型]: interview_question\n"
        f"[题目ID]: {question_id}\n"
        f"[岗位]: {role}\n"
        f"[知识点]: {topic}\n"
        f"[主题ID]: {topic_id}\n"
        f"[题型]: {question_type}\n"
        f"[难度]: {difficulty}\n"
        f"[题目]: {question}\n"
        f"[参考答案]: {expected_answer}\n"
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
        "expected_answer": expected_answer,
        "expect_answer": expected_answer,
        "follow_up_angles": json.dumps(follow_up_angles, ensure_ascii=False),
    }

    return Document(page_content=page_content, metadata=metadata)


def load_documents_and_ids_from_jsonl(file_path: Path) -> tuple[list[Any], list[str]]:
    documents = []
    ids = []
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            doc = json_to_question_document(obj, source_file=file_path.name)
            documents.append(doc)
            ids.append(f"{file_path.stem}_{len(documents)}")
    return documents, ids


def parse_json_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        if not value.strip():
            return []
        try:
            data = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        if isinstance(data, list):
            return [str(item) for item in data]
        return [str(data)]
    return [str(value)]

