from typing import Literal

from pydantic import BaseModel, Field


class StudyPlanItem(BaseModel):
    topic: str  # 这条计划针对哪个知识点
    priority: Literal["high", "medium", "low"]  # 当前知识点的重要程度
    reason: str # 解释为什么
    actions: list[str] = Field(default_factory=list)  # 具体的行动推荐 应该怎么做 也就是plan的实际
    resources: list[str] = Field(default_factory=list) # 推荐素材 先空 后续接rag学习资料检索


class LearningAdvice(BaseModel):
    session_id: str # 面试记录id
    user_id: str # 标记属于哪个用户
    overall_diagnosis: str # 展示整体水平
    strengths: list[str] = Field(default_factory=list) # 优势能力
    weaknesses: list[str] = Field(default_factory=list) # 缺陷能力
    weak_topics: list[str] = Field(default_factory=list) # 薄弱知识点
    study_plan: list[StudyPlanItem] = Field(default_factory=list) # 可执行的学习计划
    next_interview_suggestion: str # 推荐下一步怎么做


class LearningAdviceResponse(BaseModel):
    session_id: str
    status: str
    advice: LearningAdvice