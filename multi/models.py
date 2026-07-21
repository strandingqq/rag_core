from dataclasses import dataclass , field, asdict
from typing import Any
# dataclass注意 没有默认值的字段，不能放在有默认值字段的后面。
# non-default argument 'question' follows default argument
""" 
所有数据结构体都在这里定义

Question -- InterviewPlanItem -- InterviewPlan                   ---|       
                                                                    |--InterviewSession
valResult  -- InterviewTurn  -- TurnSummary  -- InterviewReport  ---|

valMaterials 
FollowupMaterials
"""



""" 
@dataclass 会自动生成一个init方法 大致等价于 
    self.session_id = session_id 
    ....
创建的时候就可以 session = InterviewSession(
    session_id="xxx",
    user_id="u001",
    status="in_progress",
    current_index=0,
)
注意 不可以 session = InterviewSession() 这被称为空参构造 没有默认值的字段都是必填参数
"""
""" 
list是可变对象 如果多个实例共享一个默认列表 一个对象修改列表时 其他对象可能被一起影响到
class EvaluationResult:
    hit_points = []
a = EvaluationResult()
b = EvaluationResult()
当我修改a.hit_points.append("答对了 KV Cache")
b也会被修改

所以dataclass会阻止这样定义 
hit_points: list[str] = field(default_factory=list)
这样都会单独调用一次 list() 生成一个全新的空列表
"""
@dataclass
class Question:
    """ 
    题库中的一道面试题 保存面试题所必须的内容
    
    Args:
        question_id , topic , difficulty , question , expected_answer , follow_up_angle
    """
    question_id: str
    topic: str
    difficulty: str 
    question: str
    expected_answer: str = ""
    follow_up_angles: list[str] = field(default_factory=list)

@dataclass
class valMaterials:
    """ 
    为评分函数提供 参考答案、评分点、常见错误和检索 补充材料。

    Args:expected_answer、reference_points、common_mistakes、rubric、retrieved_chunks
    """
    expected_answer: str = ""
    reference_points: list[str] = field(default_factory=list)
    common_mistakes: list[str] = field(default_factory=list)
    rubric: dict[str, int] = field(default_factory=dict)
    retrieved_chunks: list[Any] = field(default_factory=list)

@dataclass   
class FollowupMaterials:
    """ 
    为生成追问提供 参考答案、追问方向和外部检索 上下文。

    Args: expected_answer、follow_up_angles、retrieved_context
    """
    expected_answer: str = ""
    follow_up_angles: list[str] = field(default_factory=list)
    retrieved_context: str = "无"


@dataclass
class valResult:
    """ 
    一道题的评分、理由、命中点、缺失点、错误点和改进建议

    Args: core、reason、hit_points、missing_points、mistakes、suggestion
    """
    score: int
    reason: str
    hit_points: list[str] = field(default_factory=list)
    missing_points: list[str] = field(default_factory=list)
    mistakes: list[str] = field(default_factory=list)
    suggestion: str | None = None


""" 
完整的题单的数据结构 plan - plan中的一道题目 - 题目
"""
@dataclass
class InterviewPlanItem:
    """ 
    表示面试计划中的一道题 记录题目序号、题目 ID、知识点和完整题目对象。

    Args:index、question_id、topic、question
    """
    index: int
    question_id: str
    topic: str
    question: Question
    
@dataclass
class InterviewPlan:
    """ 
    一次面试的题单配置

    Args:plan_id、topics、num_questions、items
    """
    plan_id: str
    topics: list[str]
    num_questions: int
    items: list[InterviewPlanItem]

@dataclass
class InterviewTurn:
    """ 
    一道题的完整记录 以及状态变更
    plan 记录了完整的面试题单 
    turns 记录了每道题目的完整记录/问答情况 包括评分结果

    Args:index、question_id、topic、main_question、main_answer、followup_question、followup_answer、score、evaluation、status
    """
    index: int
    question_id: str
    topic: str
 
    main_question: str
    main_answer: str | None = None
    followup_question: str | None = None
    followup_answer: str | None = None

    score: int | None = None
    evaluation: valResult | None = None
    status: str = "not_started" # waiting_main_answer / waiting_followup_answer / completed


@dataclass
class InterviewSession:
    """ 
    记录一次完整面试的运行状态
    session.plan.items[session.current_index] 就是当前题目

    Args:session_id、user_id、plan、current_index、created_time、updated_time、finished_time、final_report、turns、status
    """
    session_id: str
    user_id: str
    plan : InterviewPlan

    current_index: int
    created_time: str
    updated_time: str
    finished_time: str | None = None
    final_report: dict = field(default_factory=dict)
    turns: list[InterviewTurn] = field(default_factory=list)
    
    status: str = "not_started" # in_progress / completed


@dataclass 
class TurnSummary:
    """ 
    单题报告

    Args:index、question_id、topic、score、main_question、main_answer、followup_question、followup_answer、reason、hit_points、missing_points、mistakes、suggestion
    """
    index: int
    question_id: str
    topic: str
    score: int
    
    main_question: str
    main_answer: str
    followup_question: str
    followup_answer: str
    reason: str
    hit_points: list[str] = field(default_factory=list)
    missing_points: list[str] = field(default_factory=list)
    mistakes: list[str] = field(default_factory=list)
    suggestion: str | None = None

@dataclass
class InterviewReport:
    """ 
    题单完整报告

    Args:session_id、user_id、total_score、level、summary、turn_summaries
    """
    session_id: str
    user_id: str
    total_score: float
    level: str
    summary: str
    turn_summaries: list[TurnSummary] = field(default_factory=list)