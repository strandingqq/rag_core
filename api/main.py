from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.errors import InterviewStateError, QuestionSelectionError, SessionNotFoundError, ExternalServiceError
from api.routers.health import router as health_router
from api.routers.interviews import router as interviews_router

app = FastAPI(
    title="AI Interview Training API",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(interviews_router)


@app.exception_handler(SessionNotFoundError)
async def handle_session_not_found(
    request: Request,
    exc: SessionNotFoundError,
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(InterviewStateError)
async def handle_interview_state_error(
    request: Request,
    exc: InterviewStateError,
) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(QuestionSelectionError)
async def handle_question_selection_error(
    request: Request,
    exc: QuestionSelectionError,
) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(ExternalServiceError)# 装饰器 给app注册功能
async def handle_external_service_error(
    request: Request,
    exc: ExternalServiceError, # 之前创建的错误对象 ExternalServiceError类对象
) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={
            "detail": str(exc),
            "service": exc.service,
        },
    )