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

---

# 主流程 Agent 化开发顺序

## 新阶段目标

Learning Advisor Agent 完成后，下一阶段开始把原来的主流程逐步替换成 Agent workflow。

但是外部 API 先保持不变，仍然保留原来的接口：

```text
POST /interviews
GET /interviews/{session_id}/current-question
POST /interviews/{session_id}/main-answer
GET /interviews/{session_id}/followup-question
POST /interviews/{session_id}/followup-answer
GET /interviews/{session_id}/report
GET /interviews/{session_id}/learning-advice
```

这一阶段的核心原则：

- Agent 负责判断、生成、解释。
- Service 负责状态校验、调用工具、写入 session。
- 状态推进必须由确定性代码执行，不让 LLM 直接修改 `InterviewSession`。
- 每次替换只替换一个环节，保证可以定位问题。

## 推荐开发顺序

### 0. 固化现有 Learning Advisor Agent

目标：

- 确认 `/learning-advice` 能在 `/docs` 跑通。
- 确认原来的面试主流程没有被破坏。
- 补齐基础测试。

这一步完成后，再开始动主流程。

### 1. 新增 `InterviewOrchestratorAgent`

这是主流程 Agent 化的第一步。

第一版不要让它执行任何业务动作，只让它根据当前请求和 session 状态输出“下一步应该做什么”。

它的定位是：

```text
状态理解器 + 动作选择器 + 路由决策器
```

例如：

- 当前 turn 是 `waiting_main_answer`，用户提交了主回答，则应该进入 `accept_main_answer`。
- 当前 turn 是 `waiting_followup_answer`，用户请求当前问题，则应该返回追问。
- 当前 session 已经 `completed`，用户继续提交回答，则应该拒绝。
- 当前 session 已完成且用户请求报告，则允许返回报告。

第一版 Orchestrator 只做决策，不真正生成追问、不评分、不生成报告。

### 2. 替换追问生成：`InterviewerAgent`

目标：

- 用 Agent 替代当前 `generate_followup_question`。
- 输出追问问题，同时输出追问意图、目标薄弱点和置信度。

建议输出：

```text
followup_question
target_gap
followup_type
reason
confidence
```

### 3. 替换评分：`EvaluatorAgent`

目标：

- 用 Agent 替代当前 `evaluate_turn`。
- 输出结构化评分。
- 增加 `confidence` 和 `needs_human_review`。

这一步开始引入轻量 HITL。

### 4. 替换题单生成：`QuestionPlannerAgent`

目标：

- Agent 负责制定选题策略。
- Chroma 查询和题目筛选仍由确定性工具执行。
- 不能让 Agent 直接编造不存在的题。

### 5. 增加 `Guardrails` 和 `HITL`

目标：

- 追问必须只有一个问题。
- 评分必须在 0-100。
- 低置信度评分进入人工复核。
- Agent 建议修改题单时需要人工确认。

### 6. 增加 `Tracing` 和 `Agent Eval`

目标：

- 每次 Agent run 都记录输入、输出、工具调用和错误。
- 为 Orchestrator、Interviewer、Evaluator 分别准备小型 eval dataset。
- 每次改 prompt 或 agent 逻辑后能跑回归测试。

---

# Step 1: InterviewOrchestratorAgent 设计

## 设计目标

`InterviewOrchestratorAgent` 是主流程的总控 Agent。

第一版只解决一个问题：

```text
在当前 session 状态和当前 API 请求下，系统下一步应该执行什么动作？
```

它不直接：

- 生成题单。
- 生成追问。
- 评分。
- 修改 `session.current_index`。
- 修改 `turn.status`。
- 写入 session。

它只输出结构化决策。

## 为什么第一步先做 Orchestrator

原因：

- 它能训练 Agent 的核心能力：状态理解、动作选择、工具规划。
- 它不会立刻破坏原来的主流程。
- 它可以作为后面所有 Agent 的入口。
- 它能为 tracing、eval、HITL 打基础。

## 输入设计

Orchestrator 的输入应该由三部分组成。

### 1. 当前请求事件

建议定义为 `request_event`：

```text
create_interview
get_current_question
submit_main_answer
get_followup_question
submit_followup_answer
get_report
get_learning_advice
```

第一版可以先覆盖已有接口，不新增接口。

### 2. Session 快照

不要把整个 dataclass 原样丢给 LLM。

应该先整理成简洁快照：

```text
session_id
user_id
session_status
current_index
total_turns
current_turn_status
current_question_id
current_topic
has_main_answer
has_followup_question
has_followup_answer
has_evaluation
has_final_report
```

如果 session 不存在，例如 `POST /interviews`，则 `session_snapshot` 可以是 `None`。

### 3. 请求 payload 摘要

例如：

```text
has_answer
answer_length
answer_preview
```

不要把用户完整长回答无限制塞给 Orchestrator。第一版只需要判断是否为空、当前请求类型和状态是否匹配。

## 输出设计

建议定义内部 schema：`OrchestratorDecision`。

字段：

```text
action
allowed
reason
target_turn_index
required_tools
confidence
needs_human_review
error_code
error_message
```

其中 `action` 建议先定义这些枚举：

```text
create_plan
return_main_question
accept_main_answer
generate_followup
return_followup_question
accept_followup_answer
evaluate_turn
advance_to_next_question
generate_report
return_report
return_learning_advice
reject_invalid_request
```

第一版可以让一个请求对应一个主 action。

例如：

```json
{
  "action": "accept_main_answer",
  "allowed": true,
  "reason": "Current turn is waiting for a main answer and the request contains a non-empty answer.",
  "target_turn_index": 0,
  "required_tools": ["get_current_turn", "save_main_answer", "generate_followup"],
  "confidence": 0.95,
  "needs_human_review": false,
  "error_code": null,
  "error_message": null
}
```

如果请求不合法：

```json
{
  "action": "reject_invalid_request",
  "allowed": false,
  "reason": "The current turn is waiting for a followup answer, so submitting another main answer is invalid.",
  "target_turn_index": 0,
  "required_tools": [],
  "confidence": 0.98,
  "needs_human_review": false,
  "error_code": "INVALID_TURN_STATUS",
  "error_message": "current turn does not allow submitting main answer"
}
```

## 第一版文件结构

建议新增：

```text
api/
  agents/
    orchestrator.py
    orchestrator_schemas.py
    orchestrator_tools.py
```

职责：

```text
orchestrator_schemas.py
  定义 RequestEvent、OrchestratorAction、SessionSnapshot、OrchestratorDecision

orchestrator_tools.py
  build_session_snapshot(session)
  build_payload_summary(answer=None)

orchestrator.py
  run_orchestrator(request_event, session=None, payload=None, llm=None)
```

第一版可以先不用真正 tool calling。

可以先用固定 Python 工具整理上下文，然后让 Agent 输出结构化决策。

## 第一版执行方式

建议采用“旁路接入”。

也就是：先让 service 调用 Orchestrator，但不完全依赖它推进流程。

示例：

```text
submit_main_answer
  -> load session
  -> run_orchestrator("submit_main_answer", session, payload)
  -> 如果 decision.allowed == false，抛 InterviewStateError
  -> 如果 decision.action != "accept_main_answer"，抛 InterviewStateError
  -> 继续执行原来的 _submit_main_answer
```

这样既接入了 Agent，又不会把状态机完全交给 Agent。

## Orchestrator 的第一批规则

这些规则应该写进 instructions，也应该写进测试。

```text
1. session.status == completed 时，不允许提交 main answer 或 followup answer。
2. turn.status == waiting_main_answer 时，可以读取 main question，可以提交 main answer。
3. turn.status == waiting_main_answer 时，不允许读取 followup question。
4. turn.status == waiting_followup_answer 时，可以读取 followup question，可以提交 followup answer。
5. turn.status == waiting_followup_answer 时，不允许再次提交 main answer。
6. 只有 session.status == completed 且 final_report 存在时，才能 return_report。
7. 只有 session.status == completed 时，才能 return_learning_advice。
8. 空 answer 必须 reject_invalid_request。
```

## 第一版测试计划

建议新增：

```text
api/tests/test_orchestrator.py
```

先不测真实 LLM，使用 fake orchestrator 或规则版 fallback。

至少覆盖：

- `waiting_main_answer + get_current_question -> return_main_question`
- `waiting_main_answer + submit_main_answer -> accept_main_answer`
- `waiting_main_answer + get_followup_question -> reject_invalid_request`
- `waiting_followup_answer + get_followup_question -> return_followup_question`
- `waiting_followup_answer + submit_followup_answer -> accept_followup_answer`
- `completed + get_report -> return_report`
- `completed + submit_main_answer -> reject_invalid_request`
- `empty answer + submit_main_answer -> reject_invalid_request`

## 第一版完成标准

做到下面几点即可：

- 新增 OrchestratorAgent 内部入口。
- 能生成结构化 `OrchestratorDecision`。
- 接入至少一个 service 方法，建议先接 `submit_main_answer`。
- 原有 API 行为不变。
- 非法状态能被 Orchestrator 拒绝。
- 单测通过。

## 后续如何升级

第一版稳定后，再逐步升级：

- 把 Orchestrator 从一个 service 接入扩展到所有 interview service 方法。
- 增加 tracing，记录每次 decision。
- 给 Orchestrator 做 eval dataset。
- 让 Orchestrator 支持 handoff 到 `InterviewerAgent`、`EvaluatorAgent`、`LearningAdvisorAgent`。
- 增加 HITL action，例如 `request_human_review`。
