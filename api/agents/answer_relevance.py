import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from api.agents.answer_relevance_schemas import (
    AnswerRelevanceContext,
    AnswerRelevanceResult,
    AnswerRelevanceState,
)
from api.agents.answer_relevance_tools import validate_answer_relevance_result
from api.infra.llm import build_llm
from langsmith import traceable

ANSWER_RELEVANCE_SYSTEM_PROMPT = """
你是 AI 技术面试系统中的回答相关性判断 Agent。

你的任务不是评分，也不是生成追问。
你的唯一任务是判断候选人提交的内容是否是对当前面试题的有效回答。

你必须只输出 JSON，不要输出 Markdown，不要输出额外解释。

分类规则：

1. category = "answer"
   用户正在认真回答当前题目，即使答案不完整或有错误，也属于 answer。
   对应 suggested_action 必须是 "continue_interview"。
   response_to_user 必须为空字符串。

2. category = "user_question"
   用户不是回答题目，而是在向系统提问。
   例如：“这题是什么意思？”、“能解释一下题目吗？”、“你能举个例子吗？”
   对应 suggested_action 通常是 "answer_clarification"。

3. category = "needs_clarification"
   用户表达自己不理解题目，或者需要澄清题意。
   例如：“没看懂问题”、“这个依赖数组指什么？”
   对应 suggested_action 通常是 "answer_clarification"。

4. category = "off_topic"
   用户回答内容明显和当前题目无关。
   对应 suggested_action 通常是 "ask_retry"。

5. category = "too_short"
   用户回答过短，不足以判断其理解。
   例如：“会”、“用过”、“是的”、“了解一点”。
   对应 suggested_action 通常是 "ask_retry"。

6. category = "dont_know"
   用户明确表示不会、不知道、没学过、没有经验。
   对应 suggested_action 通常是 "offer_hint" 或 "simplify_question"。

注意：
- 如果用户答案很差但确实在回答题目，仍然归类为 answer。
- 不要因为答案错误就归类为 off_topic。
- 不要评分。
- 不要生成追问。
- 不要修改题目。
- confidence 必须是 0 到 1 的数字。

输出 JSON 格式：

{
  "reasoning": "分类理由",
  "category": "answer | user_question | needs_clarification | off_topic | too_short | dont_know",
  "suggested_action": "continue_interview | answer_clarification | ask_retry | offer_hint | simplify_question",
  "response_to_user": "当不能继续面试时返回给用户的一句话；如果 continue_interview 则为空字符串",
  "confidence": 0.9
}
"""


ANSWER_RELEVANCE_USER_PROMPT = """
【当前题目】
{main_question}

【知识点】
{topic}

【难度】
{difficulty}

【参考答案】
{expected_answer}

【候选人提交内容】
{candidate_answer}

请判断候选人提交内容是否是当前题目的有效回答。
只输出 JSON。
"""


def classify_answer_relevance_node(
    state: AnswerRelevanceState,
    llm: Any | None = None,
) -> dict:
    context = state["context"]
    llm = llm or build_llm()

    llm_json = llm.bind(response_format={"type": "json_object"})

    raw_result = llm_json.invoke(
        [
            SystemMessage(content=ANSWER_RELEVANCE_SYSTEM_PROMPT),
            HumanMessage(
                content=ANSWER_RELEVANCE_USER_PROMPT.format(
                    main_question=context.main_question,
                    topic=context.topic,
                    difficulty=context.difficulty,
                    expected_answer=context.expected_answer or "无",
                    candidate_answer=context.candidate_answer,
                )
            ),
        ]
    )

    data = json.loads(raw_result.content)
    result = AnswerRelevanceResult.model_validate(data)
    validate_answer_relevance_result(result)

    return {
        "raw_response": data,
        "result": result,
    }


def build_answer_relevance_graph(llm: Any | None = None):
    def classify_node(state: AnswerRelevanceState) -> dict:
        return classify_answer_relevance_node(state, llm=llm)

    workflow = StateGraph(AnswerRelevanceState)
    workflow.add_node("classify_answer_relevance", classify_node)

    workflow.add_edge(START, "classify_answer_relevance")
    workflow.add_edge("classify_answer_relevance", END)

    return workflow.compile()

@traceable(name="AnswerRelevanceAgent", run_type="chain")
def run_answer_relevance_agent(
    context: AnswerRelevanceContext,
    llm: Any | None = None,
) -> AnswerRelevanceResult:
    if not context.candidate_answer.strip():
        return AnswerRelevanceResult(
            reasoning="候选人提交内容为空，不能作为有效回答。",
            category="too_short",
            suggested_action="ask_retry",
            response_to_user="你的回答为空，请补充你对这道题的理解。",
            confidence=1.0,
        )

    graph = build_answer_relevance_graph(llm=llm)
    final_state = graph.invoke(
        {
            "context": context,
            "result": None,
            "raw_response": None,
        }
    )

    result = final_state["result"]
    if result is None:
        raise ValueError("AnswerRelevanceAgent did not return a result")

    return result