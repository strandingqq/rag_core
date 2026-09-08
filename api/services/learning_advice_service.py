from api.agents.learning_advisor import run_learning_advisor
from api.dependencies import get_llm
from api.errors import ExternalServiceError, InterviewStateError
from api.schemas.learning_advice import LearningAdviceResponse
from api.session_store import get_session as load_session


def get_learning_advice(session_id: str) -> LearningAdviceResponse:
    """ 
    genju session_id 获取学习建议
    """
    session = load_session(session_id)

    # 如果面试没有完成
    if session.status != "completed":
        raise InterviewStateError("interview is not completed")

    try:
        advice = run_learning_advisor(session=session, llm=get_llm())
    except Exception as exc:
        raise ExternalServiceError(
            service="LearningAdvisorAgent",
            message="failed to generate learning advice",
        ) from exc

    return LearningAdviceResponse(
        session_id=session.session_id,
        status=session.status,
        advice=advice,
    )