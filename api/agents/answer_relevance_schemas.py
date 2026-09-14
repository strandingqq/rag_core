from typing import Literal, TypedDict

from pydantic import BaseModel, Field


AnswerCategory = Literal[
    "answer",             # 用户在回答 继续原流程
    "user_question",      # 用户在问系统问题
    "needs_clarification",# 用户表示需要解释题目
    "off_topic",          # 用户回答和 题目无关
    "too_short",          # 回答太短
    "dont_know",          # 用户表示不会
]

SuggestedAction = Literal[
    "continue_interview",
    "answer_clarification",
    "ask_retry",
    "offer_hint",
    "simplify_question",
]


class AnswerRelevanceContext(BaseModel):
    """ 
    题目 + 用户回答 
    组织的结果
    """
    session_id: str
    user_id: str
    turn_index: int
    question_id: str
    topic: str
    difficulty: str
    main_question: str
    candidate_answer: str
    expected_answer: str = ""


class AnswerRelevanceResult(BaseModel):
    """ 
    workflow 的状态 用于在节点之间传播
    """
    reasoning: str = Field(
        description="Reasoning for classifying the candidate answer."
    )
    category: AnswerCategory = Field(
        description=(
            "The candidate answer category. Must be one of: answer, "
            "user_question, needs_clarification, off_topic, too_short, dont_know."
        )
    )
    suggested_action: SuggestedAction = Field(
        description=(
            "The next suggested action. Must be one of: continue_interview, "
            "answer_clarification, ask_retry, offer_hint, simplify_question."
        )
    )
    response_to_user: str = Field(
        default="",
        description=(
            "A short response to return to the user when the answer is not a valid "
            "answer. Keep empty when suggested_action is continue_interview."
        ),
    )
    confidence: float = Field(
        ge=0,
        le=1,
        description="Confidence score between 0 and 1.",
    )


class AnswerRelevanceState(TypedDict):
    context: AnswerRelevanceContext
    result: AnswerRelevanceResult | None
    raw_response: dict | None