from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from database import Base


class MLPracticeAttempt(Base):
    __tablename__ = "ml_practice_attempts"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), index=True, nullable=False)

    topic = Column(String(255), nullable=False)
    level = Column(String(50), nullable=False)

    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)

    score = Column(Float, default=0)
    verdict = Column(String(50), default="PARTIAL")
    feedback = Column(Text, default="")
    missing_points = Column(Text, default="")
    corrected_answer = Column(Text, default="")
    improvement = Column(Text, default="")

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

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), index=True, nullable=False)

    mode = Column(String(100), default="Practice")
    topic = Column(String(255), nullable=False)
    difficulty = Column(String(50), nullable=False)

    problem_name = Column(String(255), default="DSA Problem")
    problem = Column(Text, default="")
    solution = Column(Text, default="")

    score = Column(Float, default=0)
    status = Column(String(100), default="Needs Improvement")
    feedback = Column(Text, default="")

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

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), index=True, nullable=False)

    domain = Column(String(255), default="Machine Learning")
    topic = Column(String(255), nullable=False)
    difficulty = Column(String(50), default="Beginner")

    project_title = Column(String(255), default="Project Challenge")
    challenge_json = Column(Text, default="")
    submission = Column(Text, default="")

    score = Column(Float, default=0)
    verdict = Column(String(50), default="PARTIAL")
    feedback = Column(Text, default="")
    missing_points = Column(Text, default="")
    improved_approach = Column(Text, default="")
    next_steps = Column(Text, default="")

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RevokedSession(Base):
    __tablename__ = "revoked_sessions"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(String(255), index=True, nullable=False)
    token_hash = Column(String(255), unique=True, index=True, nullable=False)

    reason = Column(String(255), default="User logout")

    revoked_at = Column(DateTime(timezone=True), server_default=func.now())