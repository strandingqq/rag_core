from fastapi import APIRouter

from api.schemas.interviews import (
    AnswerRequest,
    CreateInterviewRequest,
    CreateInterviewResponse,
    CurrentQuestionResponse,
    FollowupAnswerResponse,
    FollowupQuestionResponse,
    MainAnswerResponse,
    ReportResponse,
)
from api.services import interview_service


router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.post("", response_model=CreateInterviewResponse, status_code=201)
def create_interview(request: CreateInterviewRequest) -> CreateInterviewResponse:
    return interview_service.create_interview(request)


@router.get("/{session_id}/current-question", response_model=CurrentQuestionResponse)
def get_current_question(session_id: str) -> CurrentQuestionResponse:
    return interview_service.get_current_question(session_id)


@router.post("/{session_id}/main-answer", response_model=MainAnswerResponse)
def submit_main_answer(
    session_id: str,
    request: AnswerRequest,
) -> MainAnswerResponse:
    return interview_service.submit_main_answer(session_id, request)


@router.get("/{session_id}/followup-question", response_model=FollowupQuestionResponse)
def get_followup_question(session_id: str) -> FollowupQuestionResponse:
    return interview_service.get_followup_question(session_id)


@router.post("/{session_id}/followup-answer", response_model=FollowupAnswerResponse)
def submit_followup_answer(
    session_id: str,
    request: AnswerRequest,
) -> FollowupAnswerResponse:
    return interview_service.submit_followup_answer(session_id, request)


@router.get("/{session_id}/report", response_model=ReportResponse)
def get_report(session_id: str) -> ReportResponse:
    return interview_service.get_report(session_id)
