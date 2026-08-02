# API Layer

这个目录用于重新组织 AI 模拟面试训练系统的 HTTP API 层。`api/` 是一个独立 FastAPI 包，不导入 `multi/` 下的代码。

后续从项目根目录启动：

```powershell
cd E:\2026\byte_heart_only_one\rag_core
python -m uvicorn api.main:app --reload
```

## 目录职责

```text
api/
  __init__.py
  main.py
  dependencies.py
  session_store.py
  errors.py
  routers/
    __init__.py
    health.py
    interviews.py
  schemas/
    __init__.py
    health.py
    interviews.py
  domain/
    __init__.py
    models.py
  infra/
    __init__.py
    config.py
    chroma_store.py
    llm.py
    question_loader.py
    prompts.py
  services/
    __init__.py
    planner.py
    evaluator.py
    report.py
    interview_service.py
```

## 分层职责

- `routers/`: HTTP 路由层，只调用 service。
- `schemas/`: API 请求和响应模型。
- `domain/`: 内部业务数据结构。
- `services/`: 面试题单、追问、评分、报告和状态流转。
- `infra/`: Chroma、LLM、配置和题库数据工具。
- `session_store.py`: MVP 阶段的内存会话存储，后续可替换为数据库。
