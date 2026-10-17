from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, EmailStr, Field, field_validator

BCRYPT_MAX_PASSWORD_BYTES = 72


def _normalize_email(value: str) -> str:
    return value.strip().lower()


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password at least 6 characters, at most 72 bytes")
    full_name: Optional[str] = Field(None, max_length=255)

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _normalize_email(value)

    @field_validator("password", mode="after")
    @classmethod
    def check_password_bytes(cls, value: str) -> str:
        # bcrypt raises on input over 72 bytes, so reject it up front with a clear 422.
        if len(value.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
            raise ValueError(f"Password must be at most {BCRYPT_MAX_PASSWORD_BYTES} bytes (UTF-8 encoded)")
        return value


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=256)

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _normalize_email(value)


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
    learning_style: Optional[str] = Field(None, max_length=100)
    explanation_depth: Optional[Literal["brief", "standard", "detailed", "beginner", "intermediate", "advanced"]] = None
    daily_minutes: Optional[int] = Field(None, ge=10, le=480)
    analogies_preferred: Optional[bool] = None
