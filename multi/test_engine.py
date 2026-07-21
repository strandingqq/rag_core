from pathlib import Path
import os
from engine import init_interview_session, InterviewEngine
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
plan = build_interview_plan(db, topics, 1, difficulty=difficulty)

session = init_interview_session(
    user_id="test_user",
    interview_plan=plan,
)

print(session.status)
print(session.current_index)
print(session.turns[0].status)
print(session.status)
print(InterviewEngine.get_current_question(session))



from llm import build_llm

llm = build_llm()

session = InterviewEngine.submit_main_answer(
    session,
    answer="useEffect 会在组件渲染后执行，依赖数组用于控制副作用重新执行的时机。",
    llm=llm,
)
print(session.turns[0].status)
print(session.turns[0].main_answer)
print(session.turns[0].followup_question)



session = InterviewEngine.submit_followup_answer(
    session,
    answer="基于线程池实现异步任务调度并优化并发性能",
    llm=llm,
)

print(session.turns[0].status)
print(session.turns[0].score)
print(session.turns[0].evaluation)
print(session.current_index)
print(session.status)
print(session.final_report)