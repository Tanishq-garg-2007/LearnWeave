from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password at least 6 characters")
    full_name: Optional[str] = None


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    workspace_id: str


class LearnerProfileResponse(BaseModel):
    id: str
    user_id: str
    preferences: Dict[str, Any]
    topic_mastery: Dict[str, Any]
    weak_areas: List[str]
    unresolved_doubts: List[Dict[str, Any]]
    completed_lessons: List[str]


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    workspace_id: Optional[str] = None
    profile: Optional[LearnerProfileResponse] = None


class UpdatePreferencesRequest(BaseModel):
    learning_style: Optional[str] = None
    explanation_depth: Optional[str] = None
    daily_minutes: Optional[int] = None
    analogies_preferred: Optional[bool] = None
