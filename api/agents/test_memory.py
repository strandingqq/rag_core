import uuid
from api.agents.user_profile_memory import build_user_profile_memory_agent
graph, store = build_user_profile_memory_agent()

session_id = str(uuid.uuid4())
user_id = "user_001"

thread_config = {
    "configurable": {
        "thread_id": session_id,
    }
}

result = graph.invoke(
    {
        "user_id": user_id,
        "session_id": session_id,
        "interview_summary": {
            "topic": "React Hooks",
            "score": 62,
            "mistakes": [
                "useEffect 依赖数组解释不完整",
                "副作用清理函数说明不足",
            ],
        },
        "old_profile": None,
        "profile_patch": None,
        "saved_profile": None,
    },
    config=thread_config,
)
print(result["saved_profile"])
item = store.get(("user_001", "profile"), "user_profile")
print(item.value)