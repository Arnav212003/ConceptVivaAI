from sqlalchemy import Column, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.sql import func

from database import Base


class MLPracticeAttempt(Base):
    __tablename__ = "ml_practice_attempts"
    __table_args__ = (Index("ix_ml_practice_attempts_session_status", "session_id", "evaluation_status"),)

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), index=True, nullable=False)

    topic = Column(String(255), nullable=False)
    level = Column(String(50), nullable=False)

    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)

    score = Column(Float, nullable=True)
    verdict = Column(String(50), default="PARTIAL")
    feedback = Column(Text, default="")
    missing_points = Column(Text, default="")
    corrected_answer = Column(Text, default="")
    improvement = Column(Text, default="")

    # "completed" or "unavailable". Unavailable attempts have score NULL and are
    # excluded from every average.
    evaluation_status = Column(String(20), nullable=False, default="completed", server_default="completed")
    prompt_version = Column(String(60), default="")
    model_name = Column(String(100), default="")
    integrity_flags = Column(Text, default="[]")

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class InterviewReport(Base):
    __tablename__ = "interview_reports"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), index=True, nullable=False)

    topic = Column(String(255), nullable=False)
    level = Column(String(50), nullable=False)

    rounds = Column(Integer, default=0)
    average_score = Column(Float, default=0)

    strong_points = Column(Text, default="")
    weak_points = Column(Text, default="")
    recommendation = Column(Text, default="")

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DSAAttempt(Base):
    __tablename__ = "dsa_attempts"
    __table_args__ = (Index("ix_dsa_attempts_session_status", "session_id", "evaluation_status"),)

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), index=True, nullable=False)

    mode = Column(String(100), default="Practice")
    topic = Column(String(255), nullable=False)
    difficulty = Column(String(50), nullable=False)

    problem_name = Column(String(255), default="DSA Problem")
    problem = Column(Text, default="")
    solution = Column(Text, default="")

    score = Column(Float, nullable=True)
    status = Column(String(100), default="Needs Improvement")
    feedback = Column(Text, default="")
    # Keeps hidden-test attempts separate from AI-reviewed attempts.
    tier = Column(String(30), default="ai_generated")

    # "completed" or "unavailable". Unavailable attempts have score NULL and are
    # excluded from every average.
    evaluation_status = Column(String(20), nullable=False, default="completed", server_default="completed")
    prompt_version = Column(String(60), default="")
    model_name = Column(String(100), default="")
    integrity_flags = Column(Text, default="[]")
    scoring_method = Column(String(30), default="ai_rubric")
    judge_verdict = Column(String(40), default="")
    judge_submission_id = Column(String(64), default="")
    tests_passed = Column(Integer, default=0)
    tests_total = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ProjectChallenge(Base):
    __tablename__ = "project_challenges"

    id = Column(Integer, primary_key=True, index=True)
    challenge_id = Column(String(255), unique=True, index=True, nullable=False)
    session_id = Column(String(255), index=True, nullable=False)

    domain = Column(String(255), default="Machine Learning")
    topic = Column(String(255), nullable=False)
    difficulty = Column(String(50), default="Beginner")

    project_title = Column(String(255), default="Project Challenge")
    challenge_json = Column(Text, default="")

    status = Column(String(50), default="ACTIVE")

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ProjectAttempt(Base):
    __tablename__ = "project_attempts"
    __table_args__ = (Index("ix_project_attempts_session_status", "session_id", "evaluation_status"),)

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), index=True, nullable=False)

    challenge_id = Column(String(255), index=True, default="")

    domain = Column(String(255), default="Machine Learning")
    topic = Column(String(255), nullable=False)
    difficulty = Column(String(50), default="Beginner")

    project_title = Column(String(255), default="Project Challenge")
    challenge_json = Column(Text, default="")
    submission = Column(Text, default="")

    score = Column(Float, nullable=True)
    verdict = Column(String(50), default="PARTIAL")
    feedback = Column(Text, default="")
    missing_points = Column(Text, default="")
    improved_approach = Column(Text, default="")

    # "completed" or "unavailable". Unavailable attempts have score NULL and are
    # excluded from every average.
    evaluation_status = Column(String(20), nullable=False, default="completed", server_default="completed")
    prompt_version = Column(String(60), default="")
    model_name = Column(String(100), default="")
    integrity_flags = Column(Text, default="[]")
    next_steps = Column(Text, default="")

    # Extra review details are stored as JSON text.
    architecture_review = Column(Text, default="")
    file_findings = Column(Text, default="[]")
    bugs = Column(Text, default="[]")
    security_issues = Column(Text, default="[]")
    missing_requirements = Column(Text, default="[]")
    files_reviewed = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RevokedSession(Base):
    __tablename__ = "revoked_sessions"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(String(255), index=True, nullable=False)
    token_hash = Column(String(255), unique=True, index=True, nullable=False)

    reason = Column(String(255), default="User logout")

    revoked_at = Column(DateTime(timezone=True), server_default=func.now())
