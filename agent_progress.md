# Agent 重构进度计划

## 当前目标

第一阶段先不要大改原来的面试主流程。

现在保留原本的流程：

```text
生成题单 -> 出主问题 -> 提交主回答 -> 生成追问 -> 提交追问回答 -> 评分 -> 下一题 -> 最终报告
```

这一阶段只新增一个 **面试反馈 / 学习建议 Agent**。

它的作用是：在一次面试完成后，读取已有的面试记录、分数、命中点、缺失点和错误点，然后生成更具体的学习建议。

## 为什么先做这个 Agent

这个 Agent 风险最低，因为它只读取已经完成的 session，不修改题目、不修改分数、不推进面试状态。

也就是说，即使这个 Agent 输出不理想，也不会破坏原来的面试流程。

通过这个 Agent，可以先练习这些能力：

- 如何设计 Agent 的职责边界。
- 如何设计函数工具。
- 如何把 Agent 接到 FastAPI service。
- 如何让 Agent 输出结构化结果。
- 如何在 `/docs` 中测试 Agent 接口。
- 后续如何继续扩展 memory、HITL 和 agent eval。

## Learning Advisor Agent 的作用

这个 Agent 是一个“面试后的学习教练”。

它不负责重新评分，而是基于已有评分做二次分析。

它需要回答的问题是：

- 这次面试整体表现怎么样？
- 候选人强项是什么？
- 候选人短板是什么？
- 哪些知识点最薄弱？
- 每个薄弱知识点应该怎么补？
- 下一次模拟面试应该重点练什么？

## 设计边界

第一版必须保持简单。

这个 Agent 应该做：

- 读取一个已经完成的 `InterviewSession`。
- 统计每个 topic 的表现。
- 找出低分 topic。
- 汇总 missing points、mistakes、suggestions。
- 生成学习建议。
- 返回固定 schema 的结构化结果。

这个 Agent 暂时不做：

- 不重新计算分数。
- 不修改原来的评分。
- 不修改 session 状态。
- 不自动生成下一套题。
- 不做长期 memory。
- 不做人工审核 HITL。
- 不做复杂多 Agent 协作。

## 推荐文件结构

```text
api/
  schemas/
    learning_advice.py

  agents/
    learning_tools.py
    learning_advisor.py

  services/
    learning_advice_service.py

  routers/
    learning_advice.py
```

## 计划清单

### 1. 完善输出 Schema

文件：

```text
api/schemas/learning_advice.py
```

需要定义：

- `StudyPlanItem`
- `LearningAdvice`
- `LearningAdviceResponse`

`LearningAdviceResponse` 是 API 返回给前端的外层结构，建议长这样：

```text
session_id
status
advice
```

`LearningAdvice` 是真正的学习建议内容，建议包含：

```text
session_id
user_id
overall_diagnosis
strengths
weaknesses
weak_topics
study_plan
next_interview_suggestion
```

### 2. 实现函数工具

文件：

```text
api/agents/learning_tools.py
```

第一版先写普通 Python 函数，不急着写 `@tool`，也不急着 `.bind_tools()`。

推荐工具：

- `build_session_snapshot(session)`
- `calculate_topic_performance(session)`
- `identify_weak_topics(topic_performance, threshold=70)`
- `build_rule_based_actions(weak_topics)`

这些工具只做确定性的事情，比如统计分数、收集缺失点、整理错误点。

不要让工具生成大段自然语言。自然语言总结交给 Agent。

### 3. 补完整 Agent Workflow

文件：

```text
api/agents/learning_advisor.py
```

第一版使用简单 LangGraph workflow：

```text
START -> collect_context -> generate_advice -> END
```

其中：

- `collect_context` 调用工具函数，整理 session 信息。
- `generate_advice` 调用 LLM，生成最终学习建议。

第一版可以不用 `InMemorySaver`。

第一版也可以不用 `.bind_tools()`。

原因是：这个 Agent 的流程非常固定，没必要让模型自由决定调用哪个工具。先把固定 workflow 跑通，更容易调试。

### 4. 给 Agent 暴露一个入口函数

文件：

```text
api/agents/learning_advisor.py
```

建议提供一个统一入口：

```text
run_learning_advisor(session, llm=None) -> LearningAdvice
```

这样 service 层只需要调用这个函数，不需要知道 LangGraph 内部怎么跑。

### 5. 新建 Service

文件：

```text
api/services/learning_advice_service.py
```

service 做这几件事：

- 根据 `session_id` 读取 session。
- 检查 session 是否已经完成。
- 获取 LLM。
- 调用 `run_learning_advisor(session, llm)`。
- 包装成 `LearningAdviceResponse` 返回。

如果面试还没完成，应该抛出 `InterviewStateError`。

### 6. 新建 Router

文件：

```text
api/routers/learning_advice.py
```

新增接口：

```text
GET /interviews/{session_id}/learning-advice
```

这个接口只调用 service：

```text
learning_advice_service.get_learning_advice(session_id)
```

### 7. 在 main.py 注册 Router

文件：

```text
api/main.py
```

把新 router 加进 FastAPI app。

完成后，`/docs` 里应该能看到新的接口。

### 8. 在 `/docs` 中手动测试

先跑服务：

```text
python -m uvicorn api.main:app --reload
```

然后打开：

```text
http://127.0.0.1:8000/docs
```

测试顺序：

```text
POST /interviews
GET /interviews/{session_id}/current-question
POST /interviews/{session_id}/main-answer
GET /interviews/{session_id}/followup-question
POST /interviews/{session_id}/followup-answer
GET /interviews/{session_id}/report
GET /interviews/{session_id}/learning-advice
```

### 9. 补测试

文件：

```text
api/tests/test_learning_advice_api.py
```

建议先测三种情况：

- 面试未完成时调用 `/learning-advice`，返回 409。
- 面试完成后调用 `/learning-advice`，返回学习建议。
- fake LLM 返回异常格式时，服务能给出清楚错误。

测试里继续使用 fake LLM，不要真实调用模型。

## 第一版完成标准

第一版做到下面几点就可以算完成：

- 原来的面试流程没有被破坏。
- `/report` 还能正常使用。
- 新增 `/learning-advice` 接口。
- 只有面试完成后才能生成学习建议。
- Agent 返回结构化的 `LearningAdvice`。
- 工具函数可以单独测试。
- API 单测通过。

## 后续扩展方向

第一版完成后，再考虑这些能力：

- 把普通函数工具升级成 LangChain tools。
- 使用 `.bind_tools()` 让模型自主选择工具。
- 加入 `InMemorySaver` 练习 checkpoint。
- 增加长期 memory，记录用户历史薄弱点。
- 增加 HITL，在低置信度建议或评分异常时请求人工确认。
- 增加 agent eval，用固定样例评估学习建议质量。
- 让下一轮题单根据历史表现自适应调整。
