import uuid
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from datetime import datetime
from dataclasses import asdict
from models import InterviewTurn, InterviewPlan, InterviewSession
from evaluator import generate_followup_question, evaluate_turn
from report import generate_interview_report
from evaluator import build_followup_materials, build_materials_from_turn

"""
InterviewEngine 状态机

init_interview_session 创建一次新的面试会话 
InterviewEngine.get_current_turn
InterviewEngine.get_current_question
submit_main_answer      提交主回答 生成追问 推进session状态
submit_followup_answer  提交追问答案 判断index状态 推进session状态
"""
def init_interview_session(user_id:str, interview_plan:InterviewPlan) -> InterviewSession:
    """ 
    根据面试计划创建一次新的面试会话，并把第一题状态设置为 waiting_main_answer

    Args:
        user_id interview_plan
    Returns:
        InterviewSession 类对象
    """
    
    turns = []
    for item in interview_plan.items:
        turn = InterviewTurn(
            index=item.index,
            question_id=item.question_id,
            topic=item.topic,
            main_question=item.question.question,
            status="not_started"
        )
        turns.append(turn)
    if turns:
        turns[0].status = "waiting_main_answer"
    # uuid是python标准库 用来生成通用唯一标识符
    # pythonuuid.uuid4() 会随机生成一个唯一id
    return InterviewSession(
        session_id=str(uuid.uuid4()),
        user_id=user_id,
        plan=interview_plan,
        current_index=0,
        turns=turns,
        created_time=datetime.now().isoformat(),
        updated_time=datetime.now().isoformat(),
        status="in_progress",
    )

class InterviewEngine:
    """ 
    封装面试状态机逻辑，负责获取当前题、提交主回答、生成追问、提交追问回答和推进题目状态。
    """
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")
    

    def get_current_turn(session:InterviewSession) -> InterviewTurn:
        """ 
        获取当前正在进行的那一道题
        Args:
            session
        Returns:
            InterviewTurn
        """
        if session.status != "in_progress":
            raise ValueError(f"当前面试状态不是 in_progress 而是 {session.status}")
        if session.current_index >= len(session.turns):
            raise IndexError( f"current_index 越界: {session.current_index}")
        return session.turns[session.current_index]
    
    def get_current_question(session: InterviewSession) -> str:
        """ 
        返回当前应该展示给用户的问题
        turn.status == waiting_main_answer 返回 turn.question
        turn.status == waiting_followup_answer 返回 turn.followup_question

        Args:
            session
        Returns:
            question(str)
        """
        if session.status == "completed":
            return None
        turn = InterviewEngine.get_current_turn(session)
        if turn.status == "waiting_main_answer":
            return turn.main_question
        if turn.status == "waiting_followup_answer":
            return turn.followup_question
        raise ValueError(f"当前 turn 状态不允许获取问题: {turn.status}")
    
    def submit_main_answer(session:InterviewSession, answer: str, llm:ChatOpenAI) -> InterviewSession:
        """  
        提交主问题回答，然后生成追问 , 推进状态变化 turn.status = waiting_followup_answer
        Args:
            session \ answer(用户输入) \ llm
        Returns:
            session
        """
        if not answer or not answer.strip():
            raise ValueError("追问回答不能为空")
        turn = InterviewEngine.get_current_turn(session)
        if turn.status != "waiting_main_answer":
            raise ValueError(f"当前 turn 状态不允许提交主回答: {turn.status}")
        turn.main_answer = answer
        # turn.followup_question = InterviewEngine.generate_followup(turn)
        materials = build_followup_materials(session, turn)
        turn.followup_question = generate_followup_question(turn, materials, llm=llm)
        turn.status = "waiting_followup_answer"
        session.updated_time = InterviewEngine._now()
        return session

    def submit_followup_answer(session:InterviewSession, answer: str, llm: ChatOpenAI | None = None) -> InterviewSession:
        """ 
        保存追问回答 调用evaluate_turn评分函数 生成单题评论
        Args:
            session \ answer(用户输入) \ llm
        Returns:
            session
        """
        if not answer or not answer.strip():
            raise ValueError("追问回答不能为空")
        turn = InterviewEngine.get_current_turn(session)
        if turn.status != "waiting_followup_answer":
            raise ValueError(f"当前 turn 状态不允许提交追问回答: {turn.status}")
        turn.followup_answer = answer
        # turn.evaluation = InterviewEngine.evaluate_turn(turn)
        materials = build_materials_from_turn(session, turn)
        turn.evaluation = evaluate_turn(turn, materials, llm=llm)
        turn.score = turn.evaluation.score
        turn.status = "completed"
        
        have_next = session.current_index + 1 < len(session.turns)
        if have_next:
            session.current_index += 1 
            next_turn = session.turns[session.current_index]
            next_turn.status = "waiting_main_answer"
        else:
            session.status = "completed"
            session.finished_time = InterviewEngine._now()
            # session.final_report = InterviewEngine.generate_report(session)  
            session.final_report = asdict(generate_interview_report(session, llm=llm))

        session.updated_time = InterviewEngine._now()
        return session
