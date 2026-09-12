from fastapi import APIRouter

from api.schemas.learning_advice import LearningAdviceResponse
from api.services import learning_advice_service

# 这个router下所有接口 自动加上interviews 前缀
router = APIRouter(prefix="/interviews", tags=["learning-advice"])


@router.get("/{session_id}/learning-advice", response_model=LearningAdviceResponse)
def get_learning_advice(session_id: str) -> LearningAdviceResponse:
    return learning_advice_service.get_learning_advice(session_id)