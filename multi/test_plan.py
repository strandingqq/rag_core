from pathlib import Path
import os
from chroma_store import init_chroma_db
from planner import build_interview_plan

persist_dir = Path(os.environ.get("CHROMA_PERSIST_DIR", "chroma_all_v2")).resolve()
collection_name = "question"
db = init_chroma_db(
    persist_dir=persist_dir,
    collection_name=collection_name,
)
topics = ["C++11","C++14"]
difficulty = "medium"
plan = build_interview_plan(db, topics, 3, difficulty=difficulty)
print(type(plan))
print(plan.plan_id)
print(plan.topics)
print(plan.items[0])
print(plan.items[1])
print(plan.items[2])