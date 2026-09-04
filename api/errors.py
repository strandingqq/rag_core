""" 
errors.py 是用来定义 业务错误类型的 也就是raise之后抛出的错误
raise InterviewStateError("followup answer cannot be empty")
这是一个InterviewStateError
在main.py中会有一个异步函数 / exception_handler 如果捕获到了error 就会输出一个包含错误码的JsonResponse


用户请求 API
-> router 调 service
-> service 发现状态不对
-> raise InterviewStateError("...")
-> 异常一路向上传到 FastAPI
-> FastAPI 查找有没有对应 exception_handler
-> 找到 @app.exception_handler(InterviewStateError)
-> 执行 handler
-> 返回 JSONResponse(status_code=409, content={"detail": "..."})
-> 用户在 docs 里看到 Code 409 和 detail
"""


class SessionNotFoundError(Exception):
    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(f"Session not found: {session_id}")


class InterviewStateError(Exception):
    pass


class QuestionSelectionError(Exception):
    """ 
    不带信息的错误返回
    """
    pass

class ExternalServiceError(Exception):
    """ 
    带信息的错误返回
    """
    def __init__(self, service:str, message:str):
        self.service = service
        self.message = message
        super().__init__(f"{service} failed: {message}")