""" 
组织了所有prompt 加入llm后生成内容
使用方式为
from prompts import ..._prompt 

evaluate_prompt 单道题评分prompt
followup_prompt 追问生成prompt 
generate_interview_report_promp 生成单场面试总结报告prompt
"""


evaluate_prompt: str = """ 
    你是一个严格但公平的技术面试官。请基于当前题目、候选人主回答、追问回答、参考答案、评分要点、常见错误和 RAG 检索上下文，给出单题综合评分。

    评分要求：
    1. 分数必须是 0-100 的整数。
    2. 重点评价：技术正确性、关键点覆盖度、工程经验深度、表达清晰度。
    3. 如果候选人回答存在概念错误、编造、答非所问，必须写入 mistakes。
    4. 不要机械照抄参考答案评分；如果候选人回答技术上合理，可以认可。
    5. 只输出 JSON，不要输出 Markdown，不要输出额外解释。

    输出 JSON 格式如下：
    {{
    "score": 75,
    "reason": "一句到三句话说明评分理由",
    "hit_points": ["候选人命中的要点"],
    "missing_points": ["候选人缺失的要点"],
    "mistakes": ["候选人的明显错误，没有则为空列表"],
    "suggestion": "给候选人的改进建议"
    }}
    【当前题目】
    {main_question}

    【候选人主回答】
    {main_answer}

    【追问】
    {followup_question}

    【候选人追问回答】
    {followup_answer}

    【参考答案】
    {expected_answer}
    """
followup_prompt: str = """
    你是一个严格但公平的技术面试官。请基于当前题目、候选人的主回答、参考答案和追问方向，生成一个追问问题。

    要求：
    1. 只输出一个问题。
    2. 不要给答案。
    3. 不要解释为什么这样问。
    4. 追问必须围绕当前题、用户回答中的薄弱点，或给定追问方向。
    5. 如果用户回答过于笼统，优先追问具体工程细节、边界条件、异常处理、性能瓶颈或方案取舍。
    6. 不要问多个问题。

    【当前题目】
    {main_question}

    【候选人主回答】
    {main_answer}

    【参考答案】
    {expected_answer}

    【可选追问方向】
    {follow_up_angles}

    【RAG 检索上下文】
    {retrieved_context}
    """
generate_interview_report_prompt: str = """
    你是一个严格但公平的技术面试官。请基于完整题单评分结果，为候选人生成一段自然语言总结。

    要求：
    1. 不要重新计算分数。
    2. 不要改变已有分数和等级。
    3. 总结需要包含整体表现、主要优势、主要短板、下一步建议。
    4. 语气专业、直接、有指导价值。
    5. 输出一段中文文本，不要输出 JSON。

    【完整题单评分数据】
    {report_data}
    """