from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import json
from dataclasses import asdict
from models import InterviewSession, TurnSummary, InterviewReport
from llm import build_llm
from prompts import generate_interview_report_prompt

""" 
完整面试报告生成 可以和单题合并

ensure_session_completed   确定当前面试题目已全部回答结束
build_turn_summaries       把当前session每道题的 valResult 组织到新的 TurnSummary 中
generate_report_summary    把组织的TurnSummary和score交给llm 生成报告
generate_interview_report  完整流程
"""

def ensure_session_completed(session:InterviewSession) -> None:
    """ 
    通过条件判断能够当前以及完成了所有题目的面试
    """
    if session.status != "completed":
        raise ValueError(f"面试还没有完成")
    if not session.turns:
        raise ValueError("session.turns 为空，无法生成报告")
    for turn in session.turns:
        if turn.status != "completed":
            raise ValueError(
                f"第 {turn.index + 1} 题尚未完成，当前状态是: {turn.status}"
            )
        if turn.evaluation is None:
            raise ValueError(f"第 {turn.index + 1} 题没有 evaluation")
        if turn.score is None:
            raise ValueError(f"第 {turn.index + 1} 题没有 score")
        

def build_turn_summaries(session: InterviewSession) -> list[TurnSummary]:
    """ 
    把每个turn中保存的每道题的 valResult 组织到新的 TurnSummary 结构体当中

    Args:
        session
    Returns:
        list[TurnSummary]
    """
    summaries = []
    for turn in session.turns:
        summary = TurnSummary(
            index = turn.index,
            question_id = turn.question_id,
            topic = turn.topic,
            score =  turn.score, 
            main_question=turn.main_question,
            main_answer=turn.main_answer or "",
            followup_question=turn.followup_question or "",
            followup_answer=turn.followup_answer or "",
            reason = turn.evaluation.reason,
            hit_points=turn.evaluation.hit_points,
            missing_points=turn.evaluation.missing_points,
            mistakes=turn.evaluation.mistakes,
            suggestion=turn.evaluation.suggestion,
        )
        summaries.append(summary)
    return summaries

def calculate_total_score(turn_summaries: list[TurnSummary]) -> float:
    """ 
    简单平均每道题的score
    """
    if not turn_summaries:
        return 0.0

    total = sum(turn.score for turn in turn_summaries)
    return round(total / len(turn_summaries), 1)

def score_to_level(score: float) -> str:
    if score >= 90:
        return "优秀"
    if score >= 80:
        return "良好"
    if score >= 70:
        return "中等偏上"
    if score >= 60:
        return "及格但不稳定"
    return "需要系统补强"

def generate_report_summary(
        turn_summaries: list[TurnSummary],
        total_score: float,
        level: str,
        llm: ChatOpenAI | None = None) -> str:
    """ 
    把 turn_summary 的摘要内容交给llm 生成str的最终报告

    Args:
        list[TurnSummary] \ total_score \ level \ llm
    Returns:
        文字总结 str
    """
    llm = llm or build_llm()
    report_data = {
        "total_score":total_score,
        "level":level,
        "turn_summaries":[asdict(turn) for turn in turn_summaries],
    }
    prompt = ChatPromptTemplate.from_template(generate_interview_report_prompt)
    chain = prompt | llm 
    response = chain.invoke({
        "report_data": json.dumps(report_data, ensure_ascii=False, indent=2)
    })
    return response.content.strip()

def generate_interview_report(session: InterviewSession,
                              llm: ChatOpenAI | None = None) -> InterviewReport:
    """ 
    检验面试已经完成(ensure_session_completed) 汇总结果(build_turn_summaries) 计算总分 生成最终面试报告
    Args:
        session \ llm
    Returns:
        InterviewReport 最终报告
    """
    ensure_session_completed(session)
    turn_summaries = build_turn_summaries(session)
    total_score = calculate_total_score(turn_summaries)
    level = score_to_level(total_score)

    summary = generate_report_summary(turn_summaries=turn_summaries, 
                                      total_score = total_score,
                                      level = level,
                                      llm = llm)
    return InterviewReport(
        session_id = session.session_id,
        user_id = session.user_id,
        total_score = total_score,
        level = level,
        summary = summary,
        turn_summaries = turn_summaries
    )
