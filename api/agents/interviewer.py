from typing import Any

from api.agents.interviewer_schemas import (
    FollowupType,
    InterviewerContext,
    InterviewerOutput,
)
from api.agents.interviewer_tools import (
    format_follow_up_angles,
    validate_interviewer_output,
)
from api.infra.llm import build_llm
from langsmith import traceable

INTERVIEWER_PROMPT = """
你是一个严格但公平的技术面试官，负责基于候选人的主回答生成一个追问问题。

你的任务：
1. 阅读当前题目、候选人主回答、参考答案和可选追问方向。
2. 找出候选人回答中最值得追问的薄弱点。
3. 只生成一个追问问题。
4. 不要给答案。
5. 不要同时问多个问题。
6. 不要重复主问题。
7. 输出必须是 JSON，不要输出 Markdown 或额外解释。

追问应该优先围绕：
- 候选人回答中模糊或缺失的关键点
- 工程细节
- 边界条件
- 性能问题
- 方案取舍
- 实际项目经验
- 调试排查过程

followup_type 必须是下面之一：
concept_check
engineering_detail
edge_case
performance
tradeoff
debugging
project_experience
clarification

输出 JSON 格式：
{{
  "followup_question": "一个追问问题",
  "target_gap": "这个追问针对的薄弱点",
  "followup_type": "engineering_detail",
  "reason": "为什么选择这个追问",
  "confidence": 0.85,
  "needs_human_review": false
}}

【当前题目】
{main_question}

【候选人主回答】
{main_answer}

【参考答案】
{expected_answer}

【可选追问方向】
{follow_up_angles}

【历史表现摘要】
{previous_turn_summary}
"""

@traceable(name="InterviewerAgent", run_type="chain")
def run_interviewer_agent(
    context: InterviewerContext,
    llm: Any | None = None,
) -> InterviewerOutput:
    if not context.main_answer.strip():
        raise ValueError("main_answer cannot be empty")

    from langchain_core.output_parsers import JsonOutputParser
    from langchain_core.prompts import ChatPromptTemplate

    llm = llm or build_llm()
    prompt = ChatPromptTemplate.from_template(INTERVIEWER_PROMPT)
    parser = JsonOutputParser()
    chain = prompt | llm | parser

    data = chain.invoke(
        {
            "main_question": context.main_question,
            "main_answer": context.main_answer,
            "expected_answer": context.expected_answer or "无",
            "follow_up_angles": format_follow_up_angles(context.follow_up_angles),
            "previous_turn_summary": context.previous_turn_summary or "无",
        }
    )

    output = InterviewerOutput(
        followup_question=str(data.get("followup_question", "")).strip(),
        target_gap=str(data.get("target_gap", "")).strip(),
        followup_type=_parse_followup_type(data.get("followup_type")),
        reason=str(data.get("reason", "")).strip(),
        confidence=_parse_confidence(data.get("confidence")),
        needs_human_review=bool(data.get("needs_human_review", False)),
    )

    validate_interviewer_output(output)
    return output


def _parse_followup_type(value: Any) -> FollowupType:
    if value is None:
        return FollowupType.CLARIFICATION

    try:
        return FollowupType(str(value))
    except ValueError:
        return FollowupType.CLARIFICATION


def _parse_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.5

    return max(0.0, min(1.0, confidence))