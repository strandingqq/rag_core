from dataclasses import dataclass, field
from typing import Any


@dataclass
class Question:
    question_id: str
    topic: str
    difficulty: str
    question: str
    role: str = ""
    expected_answer: str = ""
    follow_up_angles: list[str] = field(default_factory=list)


@dataclass
class EvaluationMaterials:
    expected_answer: str = ""
    reference_points: list[str] = field(default_factory=list)
    common_mistakes: list[str] = field(default_factory=list)
    rubric: dict[str, int] = field(default_factory=dict)
    retrieved_chunks: list[Any] = field(default_factory=list)


@dataclass
class FollowupMaterials:
    expected_answer: str = ""
    follow_up_angles: list[str] = field(default_factory=list)
    retrieved_context: str = "无"


@dataclass
class EvaluationResult:
    score: int
    reason: str
    hit_points: list[str] = field(default_factory=list)
    missing_points: list[str] = field(default_factory=list)
    mistakes: list[str] = field(default_factory=list)
    suggestion: str | None = None


@dataclass
class InterviewPlanItem:
    index: int
    question_id: str
    topic: str
    question: Question


@dataclass
class InterviewPlan:
    plan_id: str
    role: str
    topics: list[str]
    difficulty: str
    num_questions: int
    items: list[InterviewPlanItem]


@dataclass
class InterviewTurn:
    index: int
    question_id: str
    topic: str
    main_question: str
    main_answer: str | None = None
    followup_question: str | None = None
    followup_answer: str | None = None
    score: int | None = None
    evaluation: EvaluationResult | None = None
    status: str = "not_started"


@dataclass
class InterviewSession:
    session_id: str
    user_id: str
    plan: InterviewPlan
    current_index: int
    created_time: str
    updated_time: str
    finished_time: str | None = None
    final_report: dict[str, Any] = field(default_factory=dict)
    turns: list[InterviewTurn] = field(default_factory=list)
    status: str = "not_started"


@dataclass
class TurnSummary:
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
    session_id: str
    user_id: str
    total_score: float
    level: str
    summary: str
    turn_summaries: list[TurnSummary] = field(default_factory=list)

