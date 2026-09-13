from dataclasses import dataclass, field
from enum import Enum


class FollowupType(str, Enum):
    """ 
    追问的类型 防止模型随便乱写分类
    """
    CONCEPT_CHECK = "concept_check"
    ENGINEERING_DETAIL = "engineering_detail"
    EDGE_CASE = "edge_case"
    PERFORMANCE = "performance"
    TRADEOFF = "tradeoff"
    DEBUGGING = "debugging"
    PROJECT_EXPERIENCE = "project_experience"
    CLARIFICATION = "clarification"


@dataclass(frozen=True)
class InterviewerContext:
    """ 
    给 InterviewerAgent 的输入上下文 
    也就是session中的信息
    """
    session_id: str
    user_id: str
    turn_index: int
    question_id: str
    topic: str
    difficulty: str
    main_question: str
    main_answer: str
    expected_answer: str = ""
    follow_up_angles: list[str] = field(default_factory=list)
    previous_turn_summary: str = "无"


@dataclass(frozen=True)
class InterviewerOutput:
    """ 
    InterviewerAgent 的结构化输出
    """
    followup_question: str
    target_gap: str
    followup_type: FollowupType
    reason: str
    confidence: float = 1.0
    needs_human_review: bool = False