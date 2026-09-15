from typing import Any

from langgraph.graph import StateGraph, START, END
from langgraph.store.base import BaseStore
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

from api.agents.user_profile_memory_schemas import UserProfileMemoryState
from api.agents.user_profile import run_user_profile_agent
from api.agents.user_profile_schemas import UserProfileContext, UserProfileTurnSummary
from api.agents.user_profile_memory_tools import get_user_profile_from_store, merge_user_profile, save_user_profile_to_store


def build_user_profile_context_from_memory_state(
    state: UserProfileMemoryState,
) -> UserProfileContext:
    """
    将 memory agent 的简化面试总结转换成画像 agent 当前需要的输入结构。
    """
    interview_summary = state["interview_summary"]
    turn_summaries_data = interview_summary.get("turn_summaries")

    if turn_summaries_data:
        turn_summaries = [
            UserProfileTurnSummary(
                index=int(item.get("index", index)),
                question_id=str(item.get("question_id", f"q{index + 1}")),
                topic=str(item.get("topic", interview_summary.get("topic", ""))),
                score=int(item.get("score", interview_summary.get("score", 0))),
                reason=str(item.get("reason", "")),
                hit_points=[str(x) for x in item.get("hit_points", [])],
                missing_points=[str(x) for x in item.get("missing_points", [])],
                mistakes=[str(x) for x in item.get("mistakes", [])],
                suggestion=item.get("suggestion"),
            )
            for index, item in enumerate(turn_summaries_data)
        ]
    else:
        turn_summaries = [
            UserProfileTurnSummary(
                index=0,
                question_id=str(interview_summary.get("question_id", "q1")),
                topic=str(interview_summary.get("topic", "")),
                score=int(interview_summary.get("score", 0)),
                reason=str(interview_summary.get("reason", "")),
                hit_points=[str(x) for x in interview_summary.get("hit_points", [])],
                missing_points=[str(x) for x in interview_summary.get("missing_points", [])],
                mistakes=[str(x) for x in interview_summary.get("mistakes", [])],
                suggestion=interview_summary.get("suggestion"),
            )
        ]

    topics = interview_summary.get("topics")
    if not topics and interview_summary.get("topic"):
        topics = [interview_summary["topic"]]

    return UserProfileContext(
        user_id=state["user_id"],
        session_id=state["session_id"],
        role=str(interview_summary.get("role", "")),
        topics=[str(topic) for topic in (topics or [])],
        total_score=float(interview_summary.get("total_score", interview_summary.get("score", 0))),
        level=str(interview_summary.get("level", "")),
        turn_summaries=turn_summaries,
        learning_advice_summary=str(interview_summary.get("learning_advice_summary", "")),
    )


def load_old_profile_node(state: UserProfileMemoryState, store: BaseStore):
    """ 
    读取旧的用户画像
    """
    old_profile = get_user_profile_from_store(store=store, user_id=state["user_id"])
    return {"old_profile": old_profile}

def generate_profile_patch_node(
    state: UserProfileMemoryState,
    llm: Any | None = None,
):
    """ 
    调用UserProfileAgent 生成新增量patch
    """
    context = build_user_profile_context_from_memory_state(state)
    profile_patch = run_user_profile_agent(context, llm=llm)

    return {
        "profile_patch": profile_patch,
    }

def save_profile_node(
    state: UserProfileMemoryState,
    store: BaseStore,
):
    """ 
    合并 并 保存
    """
    saved_profile = merge_user_profile(
        old_profile=state["old_profile"],
        profile_patch=state["profile_patch"],
    )

    save_user_profile_to_store(
        store=store,
        user_id=state["user_id"],
        profile=saved_profile,
    )

    return {
        "saved_profile": saved_profile,
    }


def build_user_profile_memory_agent(llm: Any | None = None):
    def profile_patch_node(state: UserProfileMemoryState) -> dict:
        return generate_profile_patch_node(state, llm=llm)

    workflow = StateGraph(UserProfileMemoryState)

    workflow.add_node("load_old_profile", load_old_profile_node)
    workflow.add_node("generate_profile_patch", profile_patch_node)
    workflow.add_node("save_profile", save_profile_node)

    workflow.add_edge(START, "load_old_profile")
    workflow.add_edge("load_old_profile", "generate_profile_patch")
    workflow.add_edge("generate_profile_patch", "save_profile")
    workflow.add_edge("save_profile", END)

    checkpointer = MemorySaver()
    store = InMemoryStore()

    """ 
    把你定义的 Graph 工作流编译成一个可以被执行的 Runnable/CompiledGraph
    传入 checkpointer 和 store 就是再告诉这个agent 运行过程中，状态和长期记忆应该有谁负责保存
    """
    graph = workflow.compile(
        checkpointer = checkpointer,
        store = store,
    )
    return graph, store
