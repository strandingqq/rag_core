import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from api.agents.user_profile_schemas import (
    UserProfileContext,
    UserProfilePatch,
    UserProfileState,
)
from api.agents.user_profile_tools import validate_user_profile_patch
from api.infra.llm import build_llm

USER_PROFILE_SYSTEM_PROMPT = """
你是AI面试训练系统中的用户画像Agent

你的任务不是重新评分，不是重新生成学习建议
你的任务是基于一次已经完成的面试结果，提取可以长期保存的用户画像

你必须只输出JSON， 不要输出输出md， 不要给出额外解释

你需要提取:
1. weak_topics：本次面试暴露出的薄弱知识点。
2. strong_topics：本次面试表现较好的知识点。
3. common_mistakes：候选人反复出现或影响较大的错误模式。
4. latest_scores：每个 topic 最近一次得分。
5. recommended_focus：后续最应该训练的方向。
6. learning_stage：beginner / intermediate / advanced / unknown。
7. summary：一段简短画像总结。
8. confidence：你对该画像判断的置信度，0 到 1。

要求：
- 不要编造未在面试中出现的内容信息
- 不要因为单题得分低就夸大为长期弱点，表达要克制
- weak_topics 和 strong_topics 不应大量重叠。
- latest_scores 的分数必须来自输入中的题目得分。
- common_mistakes 应该总结为可复用的模式，而不是照抄整段回答。
- recommended_focus 应该具体、可训练。
- confidence 必须是 0 到 1。

输出JSON示例:
{
  "weak_topics": ["topic1"],
  "strong_topics": ["topic2"],
  "common_mistakes": ["缺少边界条件说明"],
  "latest_scores": {"topic1": 62.0},
  "recommended_focus": ["复习 useEffect 依赖数组和副作用清理"],
  "learning_stage": "intermediate",
  "summary": "用户对基础概念有一定理解，但在边界场景和工程细节上不稳定。",
  "confidence": 0.85
}
"""
USER_PROFILE_USER_PROMPT = """
【用户 ID】
{user_id}

【Session ID】
{session_id}

【岗位】
{role}

【本次面试 topics】
{topics}

【总分】
{total_score}

【等级】
{level}

【每题表现】
{turn_summaries}

【学习建议摘要】
{learning_advice_summary}

请基于以上信息生成用户画像增量。
只输出 JSON。
"""
def generate_user_profile_node(
        state: UserProfileState, # 
        llm: Any | None = None,
) -> dict:
    context = state["context"] # UserProfileContext
    llm = llm or build_llm()
    llm_json = llm.bind(response_format={"type": "json_object"})

    raw_result = llm_json.invoke(
        [
            SystemMessage(content = USER_PROFILE_SYSTEM_PROMPT),
            HumanMessage(
                content = USER_PROFILE_USER_PROMPT.format(
                    user_id=context.user_id,
                    session_id=context.session_id,
                    role=context.role or "unknown",
                    topics=", ".join(context.topics) or "无",
                    total_score=context.total_score,
                    level=context.level,
                    turn_summaries=json.dumps(
                        [item.model_dump() for item in context.turn_summaries],
                        ensure_ascii=False,
                        indent=2,
                    ),
                    learning_advice_summary=context.learning_advice_summary or "无",
                )
            )
        ]
    )
    data = json.loads(raw_result.content)
    # 保证符合python数据结构
    result = UserProfilePatch.model_validate(data)
    # 保证 符合业务逻辑
    validate_user_profile_patch(result)
    return {
        "raw_response": data,
        "result": result,
    }


def build_user_profile_graph(llm: Any | None = None):
    def profile_node(state: UserProfileState) -> dict:
        return generate_user_profile_node(state, llm=llm)

    workflow = StateGraph(UserProfileState)
    workflow.add_node("generate_user_profile", profile_node)

    workflow.add_edge(START, "generate_user_profile")
    workflow.add_edge("generate_user_profile", END)

    return workflow.compile()

def run_user_profile_agent(
        context: UserProfileContext,
        llm: Any | None = None,
) -> UserProfilePatch:
    if not context.turn_summaries:
        raise ValueError("turn_summaries cannot be empty")
    graph = build_user_profile_graph(llm = llm)
    final_state = graph.invoke(
        {
            "context": context,
            "result": None,
            "raw_response": None,
        }
    )
    result = final_state["result"]
    if result is None:
        raise ValueError("UserProfileAgent did not return a result")

    return result