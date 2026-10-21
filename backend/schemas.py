"""Pydantic request models used by the FastAPI routes."""
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class QuestionRequest(BaseModel):
    topic: str = Field(default="", max_length=2000)
    level: str = Field(default="Easy", min_length=1, max_length=30)
    # auto_topic lets the server pick from a curated pool, so clients no longer
    # need to send free-form instructions as the "topic".
    auto_topic: bool = False
    track: Literal["ml", "interview"] = "interview"
    revision_topics: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def _topic_required_unless_auto(self):
        if not self.auto_topic and not self.topic.strip():
            raise ValueError("topic is required unless auto_topic is true")
        return self


class EvaluateRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=2000)
    level: str = Field(default="Easy", min_length=1, max_length=30)
    question: str = Field(min_length=1, max_length=8000)
    answer: str = Field(min_length=1, max_length=20000)
    mode: str = Field(default="interview", max_length=30)
    display_topic: str = Field(default="", max_length=500)
    save_attempt: bool = False


class DSAProblemRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=100)
    difficulty: str = Field(default="Mixed", min_length=1, max_length=30)


class DSAEvaluateRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=100)
    difficulty: str = Field(default="Medium", min_length=1, max_length=30)
    problem: str = Field(min_length=1, max_length=30000)
    solution: str = Field(min_length=1, max_length=30000)
    mode: str = Field(default="Practice", max_length=30)
    save_attempt: bool = False


class DSAMockSetRequest(BaseModel):
    topic: str = Field(default="Arrays", min_length=1, max_length=100)
    difficulty: str = Field(default="Mixed", min_length=1, max_length=30)
    count: int = Field(default=10, ge=1, le=50)


class DSAPracticeQuestionRequest(BaseModel):
    topic: str = Field(default="Arrays", min_length=1, max_length=100)
    difficulty: str = Field(default="Mixed", min_length=1, max_length=30)


class AIPracticeQuestionRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=200)
    difficulty: str = Field(default="Medium", min_length=1, max_length=30)
    # Recent titles help reduce repeated AI-practice questions.
    recent_titles: list[str] = Field(default_factory=list, max_length=15)


class DSAOwnQuestionRequest(BaseModel):
    question_id: str = Field(default="", max_length=100)
    title: str = Field(min_length=1, max_length=200)
    topic: str = Field(default="Arrays", min_length=1, max_length=100)
    difficulty: str = Field(default="Medium", min_length=1, max_length=30)
    pattern: str = Field(default="General DSA", max_length=100)


# Legacy save payloads are kept for old frontend calls.
class SaveMLPracticeAttemptRequest(BaseModel):
    session_id: str = ""
    topic: str = Field(min_length=1, max_length=2000)
    level: str = Field(default="Easy", max_length=30)
    question: str = Field(min_length=1, max_length=8000)
    answer: str = Field(min_length=1, max_length=20000)
    score: float = 0
    verdict: str = "PARTIAL"
    feedback: str = ""
    missing_points: str = ""
    corrected_answer: str = ""
    improvement: str = ""


class SaveInterviewReportRequest(BaseModel):
    session_id: str = ""
    topic: str = Field(min_length=1, max_length=500)
    level: str = Field(default="Easy", max_length=30)
    rounds: int = Field(default=0, ge=0, le=20)
    average_score: float = 0
    strong_points: str = Field(default="", max_length=4000)
    weak_points: str = Field(default="", max_length=4000)
    recommendation: str = Field(default="", max_length=4000)
    evaluation_receipts: list[str] = Field(default_factory=list, max_length=20)


class SaveDSAAttemptRequest(BaseModel):
    session_id: str = ""
    mode: str = Field(default="Practice", max_length=30)
    topic: str = Field(min_length=1, max_length=100)
    difficulty: str = Field(default="Medium", max_length=30)
    problem_name: str = Field(default="DSA Problem", max_length=300)
    problem: str = Field(default="", max_length=30000)
    solution: str = Field(default="", max_length=30000)
    score: float = 0
    status: str = "Needs Improvement"
    feedback: str = ""


class SaveProjectAttemptRequest(BaseModel):
    session_id: str = ""
    challenge_id: str = Field(default="", max_length=255)
    domain: str = Field(default="Machine Learning", max_length=100)
    topic: str = Field(default="AI Selected Topic", max_length=500)
    difficulty: str = Field(default="Beginner", max_length=30)
    project_title: str = Field(default="Project Challenge", max_length=300)
    challenge: dict = Field(default_factory=dict)
    submission: str = Field(default="", max_length=50000)
    score: float = 0
    verdict: str = "PARTIAL"
    feedback: str = ""
    missing_points: str = ""
    improved_approach: str = ""
    next_steps: str = ""


class ProjectChallengeRequest(BaseModel):
    domain: str = Field(default="Machine Learning", max_length=100)
    topic: str = Field(default="AI Selected Topic", max_length=2000)
    difficulty: str = Field(default="Beginner", max_length=30)
    auto_topic: bool = False


class ProjectCodeFile(BaseModel):
    path: str = Field(min_length=1, max_length=1000)
    content: str = Field(default="", max_length=300000)


class ProjectSubmissionRequest(BaseModel):
    challenge_id: str = Field(min_length=1, max_length=255)
    # Kept for old text-only project submissions.
    submission: str = Field(default="", max_length=50000)
    files: list[ProjectCodeFile] = Field(default_factory=list, max_length=250)
    project_notes: str = Field(default="", max_length=10000)


class TranslateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
