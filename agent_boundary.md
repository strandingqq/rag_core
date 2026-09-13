# Agent 边界设计文档

## 目标

这个项目原本是一个确定性的面试流程：

```text
生成题单 -> 出主问题 -> 提交主回答 -> 生成追问 -> 提交追问回答 -> 评分 -> 下一题 -> 最终报告 -> 学习建议
```

Agent 化不是要把所有逻辑都交给 LLM，而是把系统拆成：

```text
硬编码状态机 + Agent 决策 + Tool 执行 + Guardrail 校验 + Service 落库
```

核心原则：

```text
Agent decides.
Tools execute.
Service validates.
Store persists.
Tests verify.
```

## 为什么需要边界

如果没有边界，Agent 很容易变成一个“什么都做”的大函数：

- 既判断流程，又生成内容。
- 既改状态，又写入数据。
- 既评分，又决定是否进入下一题。
- 出错后很难判断问题来自 prompt、状态机、工具还是数据。

所以必须先规定：

- 哪些事情由规则做。
- 哪些事情由 Agent 做。
- 哪些事情由 Tool 做。
- 哪些事情必须由 Service 最终确认。

这样既能保留工程稳定性，也能逐步训练 Agent 设计能力。

## 总体分工

### 1. API Layer

负责：

- 接收 HTTP 请求。
- 做 Pydantic 参数校验。
- 调用 service。
- 返回 response。

不负责：

- 不判断复杂状态。
- 不调用 Agent。
- 不写业务流程。

### 2. Service Layer

负责：

- 加载 session。
- 调用 OrchestratorAgent 获取决策。
- 校验 decision 是否允许执行。
- 调用工具或 specialist agent。
- 更新 session。
- 保存 session。
- 抛出业务错误。

Service 是最终控制层。即使 Agent 说可以，Service 也必须再次校验。

### 3. OrchestratorAgent

负责：

- 理解当前请求事件。
- 理解当前 session 快照。
- 判断请求是否合法。
- 选择下一步 action。
- 指定需要调用的 tool 或 specialist agent。
- 给出决策原因。
- 判断是否可能需要 human review。

不负责：

- 不直接修改 session。
- 不推进 `current_index`。
- 不保存回答。
- 不生成追问正文。
- 不评分。
- 不生成报告。
- 不直接访问数据库。

一句话：

```text
OrchestratorAgent 只输出下一步决策，不执行下一步动作。
```

### 4. Tools

负责确定性动作，例如：

- 构造 session 快照。
- 查询题库。
- 读取当前 turn。
- 保存回答。
- 计算 topic 分数。
- 整理弱项。
- 保存 trace。
- 创建 human review request。

Tool 应该是窄函数、可测试、少副作用。

不建议让 Tool 做：

- 自由生成长文本。
- 自己决定流程是否继续。
- 自己推进多个业务状态。
- 绕过 service 直接修改核心状态。

### 5. Specialist Agents

负责开放式任务：

- `InterviewerAgent`：生成追问。
- `EvaluatorAgent`：评分和解释。
- `LearningAdviceAgent`：学习建议。
- `QuestionPlannerAgent`：题单策略。
- `MemoryAgent`：用户长期画像。
- `HITLReviewAgent`：复核建议。

这些 Agent 只负责自己的专业输出，不直接改 session。

### 6. Guardrails

负责校验 Agent 输出：

- action 是否在允许枚举内。
- score 是否在 0-100。
- 追问是否只有一个问题。
- 评分是否有 reason。
- 题目是否来自题库。
- 是否需要 human review。

Guardrails 是防止 Agent 输出越界的安全层。

## OrchestratorAgent 的边界

### 它是什么

`OrchestratorAgent` 是面试 workflow 的调度器。

它读取：

```text
request_event
session_snapshot
payload_summary
```

然后输出：

```text
orchestrator_decision
```

### 它不是什么

它不是面试官，不负责生成追问。

它不是评分器，不负责给分。

它不是数据库层，不负责写 session。

它不是状态机本身，不负责真正推进状态。

它只是回答：

```text
在当前状态下，这个请求应该执行什么动作？
```

## Orchestrator 需要支持的任务

### 1. 创建面试

事件：

```text
create_interview
```

Orchestrator 判断：

- 是否需要创建题单。
- 是否需要调用 `QuestionPlannerAgent`。

第一版建议：

- 先不接入创建面试。
- 保留当前硬编码题单生成。
- 后续再引入 `QuestionPlannerAgent`。

需要 schema：

- `CreateInterviewContext`
- `OrchestratorDecision`

需要 tools：

- `search_questions`
- `build_interview_plan`

为什么需要：

- 后续支持自适应题单时，Orchestrator 可以决定是否使用普通题单、弱项题单或复习题单。

### 2. 获取当前问题

事件：

```text
get_current_question
```

Orchestrator 判断：

- 当前 session 是否还在进行。
- 当前 turn 是主问题阶段还是追问阶段。
- 应该返回主问题还是追问。

需要 schema：

- `SessionSnapshot`
- `OrchestratorDecision`

需要 tools：

- `build_session_snapshot`
- `get_current_turn_snapshot`

推荐 action：

```text
return_main_question
return_followup_question
reject_invalid_request
```

为什么需要：

- 这是最基础的状态路由。
- 后续如果加入暂停、人工复核、跳题，都需要统一由 Orchestrator 判断当前应该返回什么。

### 3. 提交主回答

事件：

```text
submit_main_answer
```

Orchestrator 判断：

- session 是否 `in_progress`。
- 当前 turn 是否 `waiting_main_answer`。
- answer 是否非空。
- 下一步是否应该保存主回答并生成追问。

需要 schema：

- `SessionSnapshot`
- `PayloadSummary`
- `OrchestratorDecision`

需要 tools：

- `build_payload_summary`
- `get_current_turn_snapshot`
- `save_main_answer`

后续需要 specialist agent：

- `InterviewerAgent`

推荐 action：

```text
accept_main_answer
reject_invalid_request
```

推荐 required_tools：

```text
save_main_answer
generate_followup
```

为什么需要：

- 这是第一个适合接入 Orchestrator 的入口。
- 它既有明确规则，又会连接后续的追问 Agent。
- 可以先旁路接入，不破坏原逻辑。

### 4. 获取追问

事件：

```text
get_followup_question
```

Orchestrator 判断：

- 当前 turn 是否 `waiting_followup_answer`。
- 是否已经存在 `followup_question`。

需要 schema：

- `SessionSnapshot`
- `OrchestratorDecision`

需要 tools：

- `get_current_turn_snapshot`

推荐 action：

```text
return_followup_question
reject_invalid_request
```

为什么需要：

- 可以防止用户在还没提交主回答时读取追问。
- 后续如果追问生成失败，可以路由到重试或人工处理。

### 5. 提交追问回答

事件：

```text
submit_followup_answer
```

Orchestrator 判断：

- session 是否 `in_progress`。
- 当前 turn 是否 `waiting_followup_answer`。
- answer 是否非空。
- 下一步是否应该评分。

需要 schema：

- `SessionSnapshot`
- `PayloadSummary`
- `OrchestratorDecision`

需要 tools：

- `build_payload_summary`
- `save_followup_answer`

后续需要 specialist agent：

- `EvaluatorAgent`

推荐 action：

```text
accept_followup_answer
reject_invalid_request
```

推荐 required_tools：

```text
save_followup_answer
evaluate_turn
advance_or_complete_session
```

为什么需要：

- 这是评分流程入口。
- 后续可以根据评分置信度决定是否进入 HITL。

### 6. 获取报告

事件：

```text
get_report
```

Orchestrator 判断：

- session 是否 `completed`。
- 是否已有 `final_report`。

需要 schema：

- `SessionSnapshot`
- `OrchestratorDecision`

需要 tools：

- `get_report_snapshot`

推荐 action：

```text
return_report
reject_invalid_request
```

为什么需要：

- 报告只能在面试完成后读取。
- 后续可以支持“报告缺失时重新生成报告”的恢复逻辑。

### 7. 获取学习建议

事件：

```text
get_learning_advice
```

Orchestrator 判断：

- session 是否 `completed`。
- 是否允许调用 `LearningAdviceAgent`。

需要 schema：

- `SessionSnapshot`
- `OrchestratorDecision`

需要 tools：

- `build_session_snapshot`
- `calculate_topic_performance`
- `identify_weak_topics`

需要 specialist agent：

- `LearningAdviceAgent`

推荐 action：

```text
return_learning_advice
reject_invalid_request
```

为什么需要：

- 学习建议是面试完成后的后处理能力。
- 未来可以根据 memory 决定是否合并历史弱点。

## 核心 Schema 设计

### 1. RequestEvent

作用：

表示当前 API 请求类型。

需要它的原因：

- 不让 Agent 猜用户在调用哪个接口。
- 保证输入稳定。

字段：

```text
create_interview
get_current_question
submit_main_answer
get_followup_question
submit_followup_answer
get_report
get_learning_advice
```

### 2. SessionSnapshot

作用：

给 Agent 一个简洁、安全、稳定的 session 摘要。

需要它的原因：

- 避免把完整 dataclass 丢给 LLM。
- 减少 token。
- 方便测试。
- 防止泄露不必要字段。

字段：

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

### 3. PayloadSummary

作用：

描述当前请求 payload。

需要它的原因：

- Orchestrator 只需要判断是否有回答，不需要完整长文本。
- 可以避免长回答污染流程判断。

字段：

```text
has_answer
answer_length
answer_preview
```

### 4. OrchestratorAction

作用：

统一规定 Orchestrator 能输出哪些动作。

需要它的原因：

- 避免 Agent 自创 action。
- 方便 service 分支处理。
- 方便 eval。

建议枚举：

```text
create_plan
return_main_question
accept_main_answer
return_followup_question
accept_followup_answer
generate_report
return_report
return_learning_advice
request_human_review
reject_invalid_request
```

### 5. OrchestratorDecision

作用：

Orchestrator 的唯一输出。

需要它的原因：

- 让 Agent 输出可解析、可校验、可测试。
- 为 tracing 和 eval 提供标准数据。

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

### 6. AgentTrace

作用：

记录每次 Agent 决策。

需要它的原因：

- 调试。
- 复盘。
- eval。
- 面试展示工程完整性。

字段：

```text
trace_id
session_id
agent_name
request_event
input_snapshot
decision
tool_calls
latency_ms
error
created_time
```

第一版可以先不实现落库，只预留结构。

### 7. HumanReviewRequest

作用：

HITL 人工复核任务。

需要它的原因：

- 当评分低置信度或 Agent 输出异常时暂停流程。
- 后续训练 human-in-the-loop 能力。

字段：

```text
review_id
session_id
turn_index
review_type
reason
agent_output
status
created_time
resolved_time
reviewer_comment
```

第一版可以先不实现，只预留设计。

## 核心 Tool 设计

### Orchestrator Tools

这些工具服务于流程判断。

```text
build_session_snapshot(session) -> SessionSnapshot
build_payload_summary(answer) -> PayloadSummary
validate_decision(decision, snapshot, payload_summary) -> None
```

为什么需要：

- 把输入整理和输出校验从 Agent 中拆出来。
- 保持 Orchestrator 简洁。

### Session Tools

这些工具服务于 session 操作。

```text
get_current_turn_snapshot(session) -> dict
save_main_answer(session, answer) -> session
save_followup_answer(session, answer) -> session
advance_or_complete_session(session) -> session
```

为什么需要：

- 后续如果 Agent 通过 tool calling 触发动作，可以复用这些确定性能力。
- 但第一版仍建议由 service 直接调用，不让 Agent 自由执行。

### Question Tools

这些工具服务于题单和题库。

```text
search_questions(role, topics, difficulty) -> list[Question]
build_plan_from_candidates(candidates, num_questions) -> InterviewPlan
```

为什么需要：

- 防止 Agent 编造题目。
- 保证题目来自真实题库。

### Evaluation Tools

这些工具服务于评分前后处理。

```text
build_evaluation_materials(session, turn)
clamp_score(score) -> int
validate_evaluation_result(result) -> None
```

为什么需要：

- 评分可以由 Agent 生成，但分数边界和结构必须由代码校验。

### Learning Tools

这些工具服务于学习建议。

```text
calculate_topic_performance(session)
identify_weak_topics(topic_performance)
build_session_learning_context(session)
```

为什么需要：

- 统计类工作应该由工具做。
- Agent 只负责生成自然语言建议。

### Trace Tools

这些工具服务于观测和 eval。

```text
save_agent_trace(trace)
list_agent_traces(session_id)
```

为什么需要：

- 后续调试 Agent 时必须知道它为什么做了某个 decision。

## 第一版最小实现边界

第一版只做这些：

```text
1. RequestEvent
2. SessionSnapshot
3. PayloadSummary
4. OrchestratorAction
5. OrchestratorDecision
6. build_session_snapshot
7. build_payload_summary
8. 规则版 run_orchestrator
9. test_orchestrator.py
```

第一版暂时不做：

```text
1. LLM Orchestrator
2. tool calling
3. handoff
4. HITL 落库
5. trace 落库
6. memory
```

原因：

- 先把边界和 schema 固化。
- 先保证状态决策正确。
- 后续再把规则实现替换成 Agent 实现。

## 最小接入方式

建议先旁路接入 `submit_main_answer`：

```text
submit_main_answer
  -> load session
  -> build snapshot
  -> run_orchestrator("submit_main_answer", session, payload)
  -> 如果 decision.allowed == false，抛 InterviewStateError
  -> 如果 decision.action != "accept_main_answer"，抛 InterviewStateError
  -> 继续执行原来的 _submit_main_answer
```

为什么只先接一个：

- 风险低。
- 容易测试。
- 可以验证抽象是否合理。
- 不会一次性影响所有接口。

## 后续扩展顺序

建议顺序：

```text
1. 规则版 Orchestrator
2. 接入 submit_main_answer
3. 接入 get_followup_question
4. 接入 submit_followup_answer
5. 接入 get_report 和 get_learning_advice
6. 增加 tracing
7. 增加 eval dataset
8. 替换追问为 InterviewerAgent
9. 替换评分为 EvaluatorAgent
10. 增加 HITL
11. 增加 QuestionPlannerAgent
12. 增加 MemoryAgent
```

## 判断是否应该用 Agent 的标准

应该用 Agent：

- 需要理解自然语言。
- 需要根据上下文选择策略。
- 需要生成解释。
- 需要在多个工具或子 Agent 间路由。
- 需要处理动态流程。

应该用规则：

- 状态机流转。
- 权限判断。
- 参数校验。
- 数据库写入。
- 分数边界。
- API 错误码。
- 幂等性。

## 一句话总结

这个项目的 Agent 边界是：

```text
硬规则保证系统不会错；
Agent 让系统更聪明；
Tool 让 Agent 能使用真实能力；
Service 保证所有动作被正确执行；
Guardrails 防止 Agent 越界。
```
