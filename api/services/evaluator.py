from typing import Any

from api.domain.models import (
    EvaluationMaterials,
    EvaluationResult,
    FollowupMaterials,
    InterviewSession,
    InterviewTurn,
)
from api.infra.llm import build_llm
from api.infra.prompts import evaluate_prompt, followup_prompt


def build_evaluation_materials(
    session: InterviewSession,
    turn: InterviewTurn,
) -> EvaluationMaterials:
    question = session.plan.items[turn.index].question
    return EvaluationMaterials(expected_answer=question.expected_answer)


def build_followup_materials(
    session: InterviewSession,
    turn: InterviewTurn,
) -> FollowupMaterials:
    question = session.plan.items[turn.index].question
    return FollowupMaterials(
        expected_answer=question.expected_answer,
        follow_up_angles=question.follow_up_angles,
        retrieved_context="无",
    )


def generate_followup_question(
    turn: InterviewTurn,
    materials: FollowupMaterials,
    llm: Any | None = None,
) -> str:
    if not turn.main_answer or not turn.main_answer.strip():
        raise ValueError("main answer cannot be empty")

    from langchain_core.prompts import ChatPromptTemplate

    llm = llm or build_llm()
    prompt = ChatPromptTemplate.from_template(followup_prompt)
    chain = prompt | llm
    response = chain.invoke(
        {
            "main_question": turn.main_question,
            "main_answer": turn.main_answer,
            "expected_answer": materials.expected_answer or "无",
            "follow_up_angles": format_follow_up_angles(materials.follow_up_angles),
            "retrieved_context": materials.retrieved_context or "无",
        }
    )

    content = response.content.strip()
    if not content:
        raise ValueError("LLM did not generate a followup question")
    return content


def evaluate_turn(
    turn: InterviewTurn,
    materials: EvaluationMaterials,
    llm: Any | None = None,
) -> EvaluationResult:
    if not turn.main_answer or not turn.main_answer.strip():
        raise ValueError("main answer cannot be empty")
    if not turn.followup_answer or not turn.followup_answer.strip():
        raise ValueError("followup answer cannot be empty")

    from langchain_core.output_parsers import JsonOutputParser
    from langchain_core.prompts import ChatPromptTemplate

    materials = materials or EvaluationMaterials()
    llm = llm or build_llm()
    prompt = ChatPromptTemplate.from_template(evaluate_prompt)
    parser = JsonOutputParser()
    chain = prompt | llm | parser

    data = chain.invoke(
        {
            "main_question": turn.main_question,
            "main_answer": turn.main_answer,
            "followup_question": turn.followup_question or "无",
            "followup_answer": turn.followup_answer,
            "expected_answer": materials.expected_answer or "无",
        }
    )

    score = max(0, min(100, int(data.get("score", 0))))
    return EvaluationResult(
        score=score,
        reason=str(data.get("reason", "")),
        hit_points=_as_list(data.get("hit_points")),
        missing_points=_as_list(data.get("missing_points")),
        mistakes=_as_list(data.get("mistakes")),
        suggestion=data.get("suggestion"),
    )


def format_follow_up_angles(angles: list[str]) -> str:
    if not angles:
        return "无"
    return "\n".join(f"{index}. {angle}" for index, angle in enumerate(angles, 1))


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]

