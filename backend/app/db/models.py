import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.db.session import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workspaces = relationship("Workspace", back_populates="user", cascade="all, delete-orphan")
    profile = relationship("LearnerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    goals = relationship("LearningGoal", back_populates="user", cascade="all, delete-orphan")


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    name = Column(String(255), default="Personal Workspace")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="workspaces")
    notes = relationship("Note", back_populates="workspace", cascade="all, delete-orphan")


class LearnerProfile(Base):
    __tablename__ = "learner_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    preferences = Column(JSONB, default=lambda: {
        "learning_style": "practical",
        "explanation_depth": "detailed",
        "daily_minutes": 45,
        "analogies_preferred": True
    })
    topic_mastery = Column(JSONB, default=dict)  # {"topic_name": float_score_0_to_1}
    weak_areas = Column(JSONB, default=list)      # ["pointers", "concurrency"]
    unresolved_doubts = Column(JSONB, default=list) # [{"topic": "...", "doubt": "..."}]
    completed_lessons = Column(JSONB, default=list) # ["lesson_id_1", ...]
    missed_sessions = Column(JSONB, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")


class LearningGoal(Base):
    __tablename__ = "learning_goals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subject = Column(String(255), nullable=False, index=True)
    target_level = Column(String(50), default="intermediate") # beginner, intermediate, advanced, mastery
    current_level = Column(String(50), default="beginner")
    total_duration_weeks = Column(Integer, default=4)
    hours_per_week = Column(Float, default=6.0)
    preferred_style = Column(String(100), default="hands-on practical examples")
    specific_objectives = Column(JSONB, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="goals")
    roadmaps = relationship("Roadmap", back_populates="goal", cascade="all, delete-orphan")


class Roadmap(Base):
    __tablename__ = "roadmaps"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    goal_id = Column(String(36), ForeignKey("learning_goals.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    total_modules = Column(Integer, default=0)
    total_lessons = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    goal = relationship("LearningGoal", back_populates="roadmaps")
    modules = relationship("Module", back_populates="roadmap", cascade="all, delete-orphan", order_by="Module.order_index")
    versions = relationship("RoadmapVersion", back_populates="roadmap", cascade="all, delete-orphan")


class RoadmapVersion(Base):
    __tablename__ = "roadmap_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    roadmap_id = Column(String(36), ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    change_reason = Column(String(500), nullable=True)
    snapshot_data = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    roadmap = relationship("Roadmap", back_populates="versions")


class Module(Base):
    __tablename__ = "modules"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    roadmap_id = Column(String(36), ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    order_index = Column(Integer, nullable=False)
    is_planned_later = Column(Boolean, default=False)  # True for future weeks beyond 2-week active window
    target_week = Column(Integer, nullable=False)
    estimated_hours = Column(Float, default=3.0)

    roadmap = relationship("Roadmap", back_populates="modules")
    lessons = relationship("Lesson", back_populates="module", cascade="all, delete-orphan", order_by="Lesson.order_index")


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    module_id = Column(String(36), ForeignKey("modules.id", ondelete="CASCADE"), nullable=False, index=True)
    roadmap_id = Column(String(36), ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    learning_objectives = Column(JSONB, default=list)
    order_index = Column(Integer, nullable=False)
    status = Column(String(50), default="pending")  # pending, in_progress, completed, skipped
    duration_minutes = Column(Integer, default=45)
    lesson_content = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    module = relationship("Module", back_populates="lessons")
    prerequisites = relationship("LessonPrerequisite", foreign_keys="LessonPrerequisite.lesson_id", back_populates="lesson", cascade="all, delete-orphan")


class LessonPrerequisite(Base):
    __tablename__ = "lesson_prerequisites"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    lesson_id = Column(String(36), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    prerequisite_lesson_id = Column(String(36), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)

    lesson = relationship("Lesson", foreign_keys=[lesson_id], back_populates="prerequisites")


class Note(Base):
    __tablename__ = "notes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False, index=True)
    tags = Column(JSONB, default=list)
    raw_content = Column(Text, nullable=False)
    file_type = Column(String(50), default="text/markdown")  # pdf, markdown, txt
    file_size = Column(Integer, default=0)
    visibility = Column(String(20), default="private", index=True)  # private, public
    processing_status = Column(String(50), default="pending")  # pending, processed, failed
    is_imported = Column(Boolean, default=False)
    source_note_id = Column(String(36), nullable=True)
    source_version = Column(Integer, default=1)
    wilson_score = Column(Float, default=0.0, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="notes")
    chunks = relationship("NoteChunk", back_populates="note", cascade="all, delete-orphan")
    votes = relationship("NoteVote", back_populates="note", cascade="all, delete-orphan")


class NoteChunk(Base):
    __tablename__ = "note_chunks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    note_id = Column(String(36), ForeignKey("notes.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    text_content = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    embedding = Column(Vector(384), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    note = relationship("Note", back_populates="chunks")


class NoteVote(Base):
    __tablename__ = "note_votes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    note_id = Column(String(36), ForeignKey("notes.id", ondelete="CASCADE"), nullable=False, index=True)
    vote_value = Column(Integer, nullable=False)  # +1 or -1
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "note_id", name="uq_user_note_vote"),
    )

    note = relationship("Note", back_populates="votes")


class NoteReport(Base):
    __tablename__ = "note_reports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    reporter_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    note_id = Column(String(36), ForeignKey("notes.id", ondelete="CASCADE"), nullable=False, index=True)
    reason = Column(String(500), nullable=False)
    status = Column(String(50), default="pending")  # pending, reviewed, dismissed, removed
    created_at = Column(DateTime, default=datetime.utcnow)


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    lesson_id = Column(String(36), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    assessment_type = Column(String(50), default="quiz")  # quiz, homework, diagnostic
    questions = Column(JSONB, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


class AssessmentAttempt(Base):
    __tablename__ = "assessment_attempts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Float, nullable=False)
    passed = Column(Boolean, default=False)
    answers = Column(JSONB, default=list)
    topic_mastery_impact = Column(JSONB, default=dict)
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CycleRun(Base):
    __tablename__ = "cycle_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    lesson_id = Column(String(36), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    current_step = Column(String(50), default="pending") # pending, lesson_gen, doubt, quiz_gen, eval, adaptive, completed, failed
    status = Column(String(50), default="pending")  # pending, running, succeeded, failed, skipped
    step_inputs = Column(JSONB, default=dict)
    step_outputs = Column(JSONB, default=dict)
    error_message = Column(Text, nullable=True)
    idempotency_key = Column(String(100), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StudySchedule(Base):
    __tablename__ = "study_schedules"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    lesson_id = Column(String(36), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    scheduled_date = Column(DateTime, nullable=False)
    status = Column(String(50), default="scheduled")  # scheduled, completed, missed, rescheduled
    created_at = Column(DateTime, default=datetime.utcnow)

    lesson = relationship("Lesson")
