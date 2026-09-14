from typing import Any, Optional

from pydantic import BaseModel, Field


class CreateInterviewRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1)
    topics: list[str] = Field(..., min_length=1)
    difficulty: str = "medium"
    num_questions: int = Field(..., ge=1)


class CreateInterviewResponse(BaseModel):
    session_id: str
    status: str
    current_index: int
    total_questions: int
    current_question: Optional[str]


class CurrentQuestionResponse(BaseModel):
    session_id: str
    status: str
    current_index: int
    question_type: str
    question: Optional[str]


class AnswerRequest(BaseModel):
    answer: str = Field(..., min_length=1)


# class MainAnswerResponse(BaseModel):
#     session_id: str
#     status: str
#     current_index: int
#     turn_status: str
#     followup_question: Optional[str]
class MainAnswerResponse(BaseModel):
    session_id: str
    status: str
    current_index: int
    turn_status: str
    followup_question: Optional[str]
    answer_category: Optional[str] = None
    suggested_action: Optional[str] = None
    response_to_user: Optional[str] = None
    answer_relevance_confidence: Optional[float] = None

class FollowupQuestionResponse(BaseModel):
    session_id: str
    current_index: int
    question_type: str
    question: str


class FollowupAnswerResponse(BaseModel):
    session_id: str
    status: str
    completed_turn_index: int
    score: int
    current_index: int
    next_question: Optional[str]


class ReportResponse(BaseModel):
    session_id: str
    status: str
    report: dict[str, Any]
