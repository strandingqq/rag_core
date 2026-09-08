from langgraph.graph import StateGraph, START, END
from api.domain.models import InterviewSession
from typing import Any
import json
from typing import Any, TypedDict
from api.domain.models import InterviewSession
from api.infra.llm import build_llm
from api.schemas.learning_advice import LearningAdvice
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from api.agents.learning_tools import (
    build_rule_based_actions,
    build_session_snapshot,
    calculate_topic_performance,
    identify_weak_topics,
)

class LearningAdvisorState(TypedDict, total=False):
    session: InterviewSession
    llm: Any
    session_snapshot: dict[str, Any]
    topic_performance: list[dict[str, Any]]
    weak_topics: list[dict[str, Any]]
    rule_based_actions: list[dict[str, Any]]
    advice: LearningAdvice

learning_advisor_prompt = """
你是一个技术面试后的学习建议 Agent。

你的任务：
1. 基于候选人的面试记录、单题评分、命中点、缺失点和错误点，生成学习建议。
2. 不要重新评分。
3. 不要质疑已有分数。
4. 不要编造面试记录中不存在的问题。
5. 建议必须具体、可执行，不能只写“加强基础”“多练习”这种空话。
6. 只输出 JSON，不要输出 Markdown，不要输出额外解释。

输出 JSON 格式必须是：

{{
  "session_id": "string",
  "user_id": "string",
  "overall_diagnosis": "string",
  "strengths": ["string"],
  "weaknesses": ["string"],
  "weak_topics": ["string"],
  "study_plan": [
    {{
      "topic": "string",
      "priority": "high",
      "reason": "string",
      "actions": ["string"],
      "resources": ["string"]
    }}
  ],
  "next_interview_suggestion": "string"
}}

注意：
- priority 只能是 high、medium、low。
- study_plan 必须围绕 weak_topics 和 rule_based_actions。
- 如果没有明显薄弱 topic，也要给出巩固建议。
- resources 第一版可以返回空列表。

【面试快照】
{session_snapshot}

【Topic 表现统计】
{topic_performance}

【薄弱 Topic】
{weak_topics}

【规则生成的学习动作】
{rule_based_actions}
"""

def collect_context(state: LearningAdvisorState) -> dict[str, Any]:
    session = state["session"]

    session_snapshot = build_session_snapshot(session)
    topic_performance = calculate_topic_performance(session)
    weak_topics = identify_weak_topics(topic_performance)
    rule_based_actions = build_rule_based_actions(weak_topics)

    return {
        "session_snapshot": session_snapshot,
        "topic_performance": topic_performance,
        "weak_topics": weak_topics,
        "rule_based_actions": rule_based_actions,
    }


def generate_advice(state: LearningAdvisorState) -> dict[str, Any]:
    llm = state.get("llm") or build_llm()

    prompt = ChatPromptTemplate.from_template(learning_advisor_prompt)
    parser = JsonOutputParser()
    chain = prompt | llm | parser

    data = chain.invoke(
        {
            "session_snapshot": json.dumps(
                state["session_snapshot"],
                ensure_ascii=False,
                indent=2,
            ),
            "topic_performance": json.dumps(
                state["topic_performance"],
                ensure_ascii=False,
                indent=2,
            ),
            "weak_topics": json.dumps(
                state["weak_topics"],
                ensure_ascii=False,
                indent=2,
            ),
            "rule_based_actions": json.dumps(
                state["rule_based_actions"],
                ensure_ascii=False,
                indent=2,
            ),
        }
    )

    advice = _validate_learning_advice(data)
    return {"advice": advice}


def run_learning_advisor(
    session: InterviewSession,
    llm: Any | None = None,
) -> LearningAdvice:
    """ 
    把agent包装成函数
    """
    result = learning_advisor_graph.invoke(
        {
            "session": session,
            "llm": llm,
        }
    )

    return result["advice"]


def _validate_learning_advice(data: dict[str, Any]) -> LearningAdvice:
    if hasattr(LearningAdvice, "model_validate"):
        return LearningAdvice.model_validate(data)

    return LearningAdvice.parse_obj(data)


workflow = StateGraph(LearningAdvisorState)

workflow.add_node("collect_context", collect_context)
workflow.add_node("generate_advice", generate_advice)

workflow.add_edge(START, "collect_context")
workflow.add_edge("collect_context", "generate_advice")
workflow.add_edge("generate_advice", END)

learning_advisor_graph = workflow.compile()