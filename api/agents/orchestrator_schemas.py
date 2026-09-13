from dataclasses import dataclass, field
from enum import Enum


class RequestEvent(str, Enum):
    """
    明确当前 API 事件 在什么 
    比如创建题单 获取题目 提交用户答案
    """

    CREATE_INTERVIEW = "create_interview"
    GET_CURRENT_QUESTION = "get_current_question"
    SUBMIT_MAIN_ANSWER = "submit_main_answer"
    GET_FOLLOWUP_QUESTION = "get_followup_question"
    SUBMIT_FOLLOWUP_ANSWER = "submit_followup_answer"
    GET_REPORT = "get_report"
    GET_LEARNING_ADVICE = "get_learning_advice"


class OrchestratorAction(str, Enum):
    """ 
    系统当前下一步应该做什么
    """
    CREATE_PLAN = "create_plan"
    RETURN_MAIN_QUESTION = "return_main_question"
    ACCEPT_MAIN_ANSWER = "accept_main_answer"
    RETURN_FOLLOWUP_QUESTION = "return_followup_question"
    ACCEPT_FOLLOWUP_ANSWER = "accept_followup_answer"
    RETURN_REPORT = "return_report"
    RETURN_LEARNING_ADVICE = "return_learning_advice"
    REQUEST_HUMAN_REVIEW = "request_human_review"
    REJECT_INVALID_REQUEST = "reject_invalid_request"


@dataclass(frozen=True)
class SessionSnapshot:
    """
    当前 session 的压缩状态摘要 不能给完整的
    """
    session_id: str
    user_id: str
    session_status: str
    current_index: int
    total_turns: int
    current_turn_status: str | None = None
    current_question_id: str | None = None
    current_topic: str | None = None
    has_main_answer: bool = False
    has_followup_question: bool = False
    has_followup_answer: bool = False
    has_evaluation: bool = False
    has_final_report: bool = False


@dataclass(frozen=True)
class PayloadSummary:
    """
    用户回答的摘要 
    只保留 有没有答案 答案长度 答案的前80各字符
    """
    has_answer: bool = False
    answer_length: int = 0
    answer_preview: str = ""


@dataclass(frozen=True)
class OrchestratorDecision:
    """
    最终当前状态机的 决策结果
    """
    action: OrchestratorAction
    allowed: bool
    reason: str
    target_turn_index: int | None = None
    required_tools: list[str] = field(default_factory=list)
    confidence: float = 1.0
    needs_human_review: bool = False
    error_code: str | None = None
    error_message: str | None = None