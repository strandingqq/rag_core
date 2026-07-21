from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from models import InterviewTurn, InterviewSession, valResult, valMaterials, FollowupMaterials
from llm import build_llm
from prompts import followup_prompt, evaluate_prompt
""" 

build_materials_from_turn  组织评分材料 valMatrial
build_followup_materials   组织追问材料 FollowupMaterial
generate_followup_question 根据 FollowupMaterial 组织追问
evaluate_turn              单题评分
"""
def build_materials_from_turn(session: InterviewSession, turn: InterviewTurn) -> valMaterials:
    """ 
    根据当前 index 在面试计划中找到原题，提取参考答案, 组织为评分材料 valMaterials

    Args:session turn
    Returns:valMaterials类对象 补充材料
    """
    question = session.plan.items[turn.index].question

    return valMaterials(
        expected_answer=question.expected_answer,
    )

def build_followup_materials(session: InterviewSession, turn: InterviewTurn) -> FollowupMaterials:
    """ 
    根据当前 index 在面试计划中找到原题，提取参考答案, 组织为追问材料 FollowupMaterials

    Args:session turn
    Returns:FollowupMaterials类对象 补充材料
    """
    question = session.plan.items[turn.index].question

    return FollowupMaterials(
        expected_answer=question.expected_answer,
        follow_up_angles=question.follow_up_angles,
        retrieved_context="无",
    )

def generate_followup_question(
    turn: InterviewTurn,
    materials: FollowupMaterials,
    llm: ChatOpenAI | None = None,
) -> str:
    """ 
    根据 主问题 用户主回答 参考答案 追问方向 调用LLM生成追问问题

    Args:
        turn 、 materials 用于提供参考答案 追问方向 、 llm
    Returns:
        content(str)
    """
    if not turn.main_answer or not turn.main_answer.strip():
        raise ValueError("主回答不能为空，不能生成追问")

    llm = llm or build_llm()

    prompt = ChatPromptTemplate.from_template(followup_prompt)
    chain = prompt | llm

    response = chain.invoke(
        {
            "main_question": turn.main_question,
            "main_answer": turn.main_answer,
            "expected_answer": materials.expected_answer or "无",
            "follow_up_angles": format_follow_up_angles(materials.follow_up_angles),
            "retrieved_context": materials.retrieved_context or "无",
        }
    )

    content = response.content.strip()

    if not content:
        raise ValueError("LLM 没有生成追问")

    return content

def _as_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value]
    return [str(value)]

def evaluate_turn(turn: InterviewTurn, materials: valMaterials, llm:ChatOpenAI | None=None) -> valResult:
    """ 
    根据主回答、追问回答和参考答案调用 LLM 评分，并解析成结构化评分结果

    Args:
        turn 单题记录 materiasls llm
    Returns:
        valResult 类对象
    """
    if not turn.main_answer or not turn.main_answer.strip():
        raise ValueError("主回答不能为空，不能进行评分")
    if not turn.followup_answer or not turn.followup_answer.strip():
        raise ValueError("追问回答不能为空，不能进行评分")
    
    materials = materials or valMaterials()
    llm = llm or build_llm()
    prompt = ChatPromptTemplate.from_template(evaluate_prompt)
    parser = JsonOutputParser()
    chain = prompt | llm | parser

    data = chain.invoke(
        {
            "main_question": turn.main_question,
            "main_answer": turn.main_answer,
            "followup_question": turn.followup_question or "无",
            "followup_answer": turn.followup_answer,
            "expected_answer": materials.expected_answer or "无",
        }
    )
    score = int(data.get("score", 0))
    return valResult(
        score=score,
        reason=str(data.get("reason", "")),
        hit_points=_as_list(data.get("hit_points")),
        missing_points=_as_list(data.get("missing_points")),
        mistakes=_as_list(data.get("mistakes")),
        suggestion=data.get("suggestion"),
    )

def format_follow_up_angles(angles: list[str]) -> str:
    if not angles:
        return "无"

    return "\n".join(
        f"{i}. {angle}"
        for i, angle in enumerate(angles, start=1)
    )
