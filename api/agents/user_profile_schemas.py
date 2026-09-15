from typing import Literal, TypedDict

from pydantic import BaseModel, Field


LearningStage = Literal[
    "beginner",
    "intermediate",
    "advanced",
    "unknown",
]


class TopicScore(BaseModel):
    topic: str
    score: float


class UserProfileTurnSummary(BaseModel):
    """ 
    把每道题 turn 压缩成 画像agent需要的信息
    """
    index: int
    question_id: str
    topic: str
    score: int
    reason: str = ""
    hit_points: list[str] = Field(default_factory=list)
    missing_points: list[str] = Field(default_factory=list)
    mistakes: list[str] = Field(default_factory=list)
    suggestion: str | None = None


class UserProfileContext(BaseModel):
    """ 
    agent 输入的信息
    记录session 以及多轮Turn压缩得到的 UserProfileTurnSummary
    """
    user_id: str
    session_id: str
    role: str = ""
    topics: list[str] = Field(default_factory=list)
    total_score: float
    level: str
    turn_summaries: list[UserProfileTurnSummary] = Field(default_factory=list)
    learning_advice_summary: str = ""


class UserProfilePatch(BaseModel):
    """ 
    agent 输出 这是本次面试对用户画像的增量更新 而不是完整画像 需要考虑合并
    """
    weak_topics: list[str] = Field(default_factory=list)
    strong_topics: list[str] = Field(default_factory=list)
    common_mistakes: list[str] = Field(default_factory=list)
    latest_scores: dict[str, float] = Field(default_factory=dict)
    recommended_focus: list[str] = Field(default_factory=list)
    learning_stage: LearningStage = "unknown"
    summary: str
    confidence: float = Field(ge=0, le=1)


class UserProfileState(TypedDict):
    """ 
    包含了agent的输入 输出结构
    还有原本信息
    """
    context: UserProfileContext
    result: UserProfilePatch | None
    raw_response: dict | None