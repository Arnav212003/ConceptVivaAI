from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
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


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    google_sub = Column(String(255), unique=True, index=True, nullable=False)
    email = Column(String(320), default="")
    name = Column(String(255), default="")
    picture_url = Column(String(1000), default="")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login_at = Column(DateTime(timezone=True), server_default=func.now())

    @property
    def owner_id(self) -> str:
        """History rows are keyed by this id once the user signs in."""
        return f"usr_{self.id}"


class AuthSession(Base):
    """Cookie-backed login session. Only a SHA-256 hash of the token is stored."""

    __tablename__ = "auth_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)


class GuestHistoryMigration(Base):
    """One row per guest session merged into an account; makes migration idempotent."""

    __tablename__ = "guest_history_migrations"

    id = Column(Integer, primary_key=True, index=True)
    guest_session_id = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    rows_moved = Column(Integer, default=0)
    migrated_at = Column(DateTime(timezone=True), server_default=func.now())


class AnalyticsDaily(Base):
    """Privacy-conscious product analytics: daily aggregate counters only.

    No user id, session id, IP address or user agent is stored, and `dimension`
    only ever holds values from a server-side allowlist.
    """

    __tablename__ = "analytics_daily"
    __table_args__ = (Index("ux_analytics_day_event_dim", "day", "event", "dimension", unique=True),)

    id = Column(Integer, primary_key=True)
    day = Column(String(10), nullable=False)  # YYYY-MM-DD (UTC)
    event = Column(String(50), nullable=False)
    dimension = Column(String(80), nullable=False, default="")
    count = Column(Integer, nullable=False, default=0)
