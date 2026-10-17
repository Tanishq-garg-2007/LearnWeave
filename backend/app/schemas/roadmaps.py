from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class GoalCreateRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=255, description="Subject or skill to learn, e.g. Operating Systems")
    target_level: Literal["beginner", "intermediate", "advanced", "mastery"] = Field("intermediate", description="beginner, intermediate, advanced, mastery")
    current_level: Literal["none", "beginner", "intermediate", "advanced"] = Field("beginner", description="none, beginner, intermediate, advanced")
    total_duration_weeks: int = Field(4, ge=1, le=24, description="Target course duration in weeks")
    hours_per_week: float = Field(6.0, ge=1.0, le=40.0, description="Available study hours per week")
    preferred_style: str = Field("hands-on practical examples", max_length=100, description="Teaching style preference")
    specific_objectives: List[str] = Field(default_factory=list, max_length=10, description="Target outcomes/projects")


class GoalResponse(BaseModel):
    id: str
    user_id: str
    subject: str
    target_level: str
    current_level: str
    total_duration_weeks: int
    hours_per_week: float
    preferred_style: str
    specific_objectives: List[str]
    created_at: Any


# Structured Pydantic models for LLM output & validation
class PlannedLesson(BaseModel):
    title: str = Field(..., min_length=3)
    learning_objectives: List[str] = Field(..., min_length=1)
    duration_minutes: int = Field(45, ge=1, le=600)
    prerequisite_titles: List[str] = Field(default_factory=list)
    is_revision: bool = False


class PlannedModule(BaseModel):
    title: str = Field(..., min_length=3)
    description: str
    target_week: int = Field(..., ge=1)
    is_planned_later: bool = False
    estimated_hours: float = Field(..., ge=0.5)
    lessons: List[PlannedLesson] = Field(default_factory=list)


class RoadmapGenerationOutput(BaseModel):
    title: str = "Personalized Learning Roadmap"
    subject: str = "Curriculum"
    overview: str = "Personalized active sprint curriculum."
    modules: List[PlannedModule] = Field(default_factory=list)
    total_estimated_weeks: int = 4


# API response schemas
class LessonResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    module_id: str
    title: str
    learning_objectives: List[str]
    order_index: int
    status: str
    duration_minutes: int


class ModuleResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    roadmap_id: str
    title: str
    description: Optional[str] = None
    order_index: int
    is_planned_later: bool
    target_week: int
    estimated_hours: float
    lessons: List[LessonResponse] = Field(default_factory=list)


class RoadmapDetailResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    goal_id: str
    user_id: str
    title: str
    version: int
    is_active: bool
    total_modules: int
    total_lessons: int
    created_at: Any
    updated_at: Any
    modules: List[ModuleResponse] = Field(default_factory=list)


class RescheduleLessonRequest(BaseModel):
    new_status: Optional[str] = None # pending, completed, skipped
