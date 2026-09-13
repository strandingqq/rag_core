# AI 面试系统 Agent Workflow 计划

## 当前决策

当前阶段暂时不做 `EvaluatorAgent`。

评分逻辑先保留现有实现：

```text
api/services/evaluator.py
```

也就是说：

- 追问生成可以逐步替换为 `InterviewerAgent`。
- 学习建议继续使用已有 `LearningAdviceAgent`。
- 评分暂时继续使用原来的 `evaluate_turn()`。
- 题单生成暂时继续硬采样。
- 动态难度先用规则模块实现，不急着做成 Agent。

## 总体原则

```text
状态机保证流程安全
Orchestrator 负责流程判断
AnswerRelevanceAgent 负责判断主回答是否有效
InterviewerAgent 负责生成追问
现有 evaluator 负责评分
PerformanceAnalyzer 负责统计表现
DifficultyAdapter 负责调整下一题策略
LearningAdviceAgent 负责面试后学习建议
```

Agent 不能直接修改 session。

session 状态推进、保存回答、保存追问、保存评分、推进下一题仍由 service 层执行。

## 完整流程图

```text
POST /interviews
  |
  v
题单生成
  - 当前版本：硬采样 build_interview_plan()
  - 后续可选：QuestionPlannerAgent
  |
  v
Session created
  |
  v
GET /interviews/{session_id}/current-question
  |
  v
返回当前主问题
  |
  v
候选人提交主回答
POST /interviews/{session_id}/main-answer
  |
  v
OrchestratorAgent
  - 判断 session 是否 in_progress
  - 判断当前 turn 是否 waiting_main_answer
  - 判断 answer 是否非空
  |
  v
AnswerRelevanceAgent
  - 判断用户输入是否是有效回答
  |
  +--> category = answer
  |       |
  |       v
  |     保存 main_answer
  |       |
  |       v
  |     InterviewerAgent 生成追问
  |       |
  |       v
  |     保存 followup_question
  |       |
  |       v
  |     turn.status = waiting_followup_answer
  |       |
  |       v
  |     返回 followup_question
  |
  +--> category = user_question / needs_clarification
  |       |
  |       v
  |     返回题目解释或澄清
  |       |
  |       v
  |     不保存 main_answer
  |       |
  |       v
  |     turn.status 保持 waiting_main_answer
  |
  +--> category = off_topic / too_short
  |       |
  |       v
  |     返回 ask_retry
  |       |
  |       v
  |     不推进状态
  |
  +--> category = dont_know
          |
          v
        返回 hint 或 simplify 建议
          |
          v
        不推进状态，后续可记录 weak signal

候选人提交追问回答
POST /interviews/{session_id}/followup-answer
  |
  v
OrchestratorAgent
  - 判断 session 是否 in_progress
  - 判断当前 turn 是否 waiting_followup_answer
  - 判断 answer 是否非空
  |
  v
保存 followup_answer
  |
  v
现有 evaluate_turn() 评分
  - 暂时不做 EvaluatorAgent
  |
  v
保存 evaluation / score
  |
  v
PerformanceAnalyzer
  - 统计 last_score
  - 统计 average_score
  - 统计 weak_topics
  - 统计 consecutive_low_scores
  |
  v
DifficultyAdapter
  |
  +--> 分数正常或较好
  |       |
  |       v
  |     使用原题单下一题
  |
  +--> 分数较低
  |       |
  |       v
  |     降低下一题难度 / 标记下一题应更基础
  |       |
  |       v
  |     第一版可以只记录建议，不一定立刻替换题目
  |
  v
是否还有下一题
  |
  +--> 有
  |       |
  |       v
  |     current_index += 1
  |       |
  |       v
  |     next_turn.status = waiting_main_answer
  |       |
  |       v
  |     返回 next_question
  |
  +--> 无
          |
          v
        session.status = completed
          |
          v
        生成 final_report
          |
          v
        GET /interviews/{session_id}/learning-advice
          |
          v
        LearningAdviceAgent 生成学习建议
```

## 当前已有内容

### 已有主流程

```text
POST /interviews
GET /current-question
POST /main-answer
GET /followup-question
POST /followup-answer
GET /report
```

### 已有核心业务模块

```text
api/services/interview_service.py
api/services/planner.py
api/services/evaluator.py
api/services/report.py
```

### 已有 Agent 相关基础

```text
api/agents/orchestrator_schemas.py
api/agents/orchestrator_tools.py
api/agents/orchestrator.py
api/tests/test_orchestrator.py
```

### 已有学习建议 Agent

```text
api/agents/learning_advisor.py
api/agents/learning_tools.py
api/services/learning_advice_service.py
api/routers/learning_advice.py
```

## 当前还缺哪些内容

### 1. AnswerRelevanceAgent

用途：

判断用户主回答属于哪种类型。

建议输出分类：

```text
answer
user_question
needs_clarification
off_topic
too_short
dont_know
```

建议输出动作：

```text
continue_interview
answer_clarification
ask_retry
offer_hint
simplify_question
```

缺口：

```text
api/agents/answer_relevance_schemas.py
api/agents/answer_relevance.py
api/services/answer_relevance_service.py
api/tests/test_answer_relevance.py
```

第一版可以只做 schema + fake/rule test，不急着真实接 LLM。

### 2. InterviewerAgent 接入主流程

用途：

替换当前 `generate_followup_question()`。

当前缺口：

```text
将 InterviewerAgent 接入 _submit_main_answer()
保存 followup_question
保持原状态流转不变
增加测试
```

第一版不要修改 `InterviewTurn` 结构，只保存追问问题文本。

后续再考虑保存：

```text
target_gap
followup_type
reason
confidence
```

### 3. PerformanceAnalyzer

用途：

评分完成后统计表现。

建议输出：

```text
last_score
average_score
consecutive_low_scores
weak_topics
current_topic_score
recommended_difficulty
```

缺口：

```text
api/services/performance_service.py
或
api/agents/performance_tools.py
```

第一版建议做规则工具，不做 Agent。

### 4. DifficultyAdapter

用途：

根据表现决定下一题策略。

第一版规则：

```text
last_score >= 85:
  keep or increase difficulty

60 <= last_score < 85:
  keep difficulty

last_score < 60:
  lower difficulty

consecutive_low_scores >= 2:
  lower difficulty and mark remedial
```

缺口：

```text
api/services/difficulty_adapter.py
或
api/agents/difficulty_tools.py
```

第一版可以只返回策略，不立刻替换题目。

### 5. 动态题目替换

用途：

当 DifficultyAdapter 建议降低难度时，替换下一题或插入基础题。

当前暂时不做。

原因：

- 需要修改 plan/turns。
- 会影响 current_index 和题单稳定性。
- 需要更复杂测试。

第一版先只记录策略。

### 6. Trace / Eval

用途：

记录 Agent 决策和后续评估。

缺口：

```text
AgentTrace schema
save_agent_trace()
eval dataset
```

当前可以先不做，等 AnswerRelevanceAgent 和 InterviewerAgent 接入后再做。

## 暂时不做的内容

### 1. EvaluatorAgent

暂时保留原来的 `evaluate_turn()`。

原因：

- 现有评分已经能工作。
- 现在优先练习追问 Agent 和流程分支。
- 等主流程稳定后，再决定是否升级评分为 Agent。

### 2. QuestionPlannerAgent

暂时保留题单硬采样。

原因：

- 题单生成牵涉 Chroma 查询、plan 修改、题目数量约束。
- 当前优先保持创建面试流程稳定。

### 3. 完整 HITL

暂时不做人工复核状态机。

原因：

- 需要新增 review 状态和审批接口。
- 等评分或 AnswerRelevance 需要人工复核时再加。

## 开发计划

### Phase 0: 稳定现有 Orchestrator

目标：

- `test_orchestrator.py` 通过。
- `submit_main_answer` 已经旁路接入 Orchestrator。
- 全量 API 测试通过。

完成标准：

```text
python -m unittest api.tests.test_orchestrator
python -m unittest discover api/tests
```

### Phase 1: 接入 InterviewerAgent

目标：

- 用 `InterviewerAgent` 替换原来的追问生成。
- 先不保存 target_gap、followup_type 等扩展字段。
- 原 API response 不变。

步骤：

```text
1. 确认 InterviewerAgent schema。
2. 确认 interviewer service。
3. 修改 _submit_main_answer() 中的追问生成逻辑。
4. 增加 fake LLM 测试。
5. 全量 API 测试。
```

完成标准：

```text
POST /main-answer 后仍返回 followup_question
原来的完整一题面试 API 测试通过
```

### Phase 2: 增加 AnswerRelevanceAgent

目标：

- 在生成追问前判断主回答是否是有效回答。
- 非有效回答时不推进状态。

步骤：

```text
1. 设计 AnswerRelevance schema。
2. 实现 AnswerRelevanceAgent。
3. 包装 answer_relevance_service。
4. 在 submit_main_answer 中接入。
5. 增加分类测试。
```

完成标准：

```text
正常回答 -> 继续生成追问
用户提问 -> 返回澄清，不推进状态
偏题回答 -> ask_retry，不推进状态
太短回答 -> ask_retry，不推进状态
```

### Phase 3: 增加 PerformanceAnalyzer

目标：

- 评分后生成表现摘要。

步骤：

```text
1. 定义 PerformanceSnapshot。
2. 实现 build_performance_snapshot(session)。
3. 在 submit_followup_answer 后调用。
4. 暂时只记录或返回内部策略，不改变题单。
```

完成标准：

```text
可以计算 last_score / average_score / weak_topics / consecutive_low_scores
```

### Phase 4: 增加 DifficultyAdapter

目标：

- 根据 PerformanceSnapshot 输出下一题难度建议。

步骤：

```text
1. 定义 DifficultyDecision。
2. 实现规则版 decide_next_difficulty(performance)。
3. 在 submit_followup_answer 后调用。
4. 第一版只记录建议，不替换题。
```

完成标准：

```text
低分时输出 lower difficulty
正常分时输出 keep difficulty
高分时输出 keep_or_raise difficulty
```

### Phase 5: 可选动态换题

目标：

- 根据 DifficultyDecision 替换下一题或插入基础题。

注意：

这一步会修改 plan/turns，风险较高，放到最后。

完成标准：

```text
低分后下一题可以替换为更低难度题
替换题必须来自 Chroma
current_index 和 turns 状态保持正确
```

### Phase 6: Trace / Eval

目标：

- 记录每次 Agent 决策。
- 准备小型 eval dataset。

建议先评估：

```text
AnswerRelevance 分类准确率
InterviewerAgent 追问是否只问一个问题
Orchestrator action 是否正确
```

## 当前最推荐的下一步

当前最推荐先做：

```text
Phase 1: 接入 InterviewerAgent
```

原因：

- 追问生成是最自然的 Agent 任务。
- 不需要改题单和评分。
- 对主流程影响小。
- 用户能在 `/docs` 里明显看到效果。

接下来不要急着做 AnswerRelevanceAgent。

先让 `InterviewerAgent` 稳定替换原追问生成，再做输入分类分支。
