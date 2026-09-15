from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


MemoryType = Literal[
    "weak_topic",
    "strong_topic",
    "common_mistake",
    "recommended_focus",
    "profile_summary",
    "session_summary",
]


class UserProfile(BaseModel):
    user_id: str
    role: str | None = None

    weak_topics: list[str] = Field(default_factory=list)
    strong_topics: list[str] = Field(default_factory=list)
    common_mistakes: list[str] = Field(default_factory=list)
    recommended_focus: list[str] = Field(default_factory=list)

    topic_scores: dict[str, list[float]] = Field(default_factory=dict)
    latest_scores: dict[str, float] = Field(default_factory=dict)

    learning_stage: str = "unknown"
    summary: str = ""

    session_count: int = 0
    last_session_id: str | None = None
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class TrainingRecord(BaseModel):
    record_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    session_id: str
    total_score: float
    level: str
    weak_topics: list[str] = Field(default_factory=list)
    strong_topics: list[str] = Field(default_factory=list)
    recommended_focus: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class MemoryRecord(BaseModel):
    memory_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    memory_type: MemoryType
    content: str
    topic: str | None = None
    source_session_id: str | None = None
    confidence: float = 1.0
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())