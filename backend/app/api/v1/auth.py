from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.db.models import User, Workspace, LearnerProfile
from app.schemas.auth import (
    UserRegisterRequest, UserLoginRequest, TokenResponse, UserResponse,
    LearnerProfileResponse, UpdatePreferencesRequest
)
from app.services.auth_service import hash_password, verify_password, create_access_token
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new student account, workspace, and initial learner profile."""
    # Check duplicate email
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists"
        )

    # Atomic user + workspace + profile creation
    user = User(
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name
    )
    db.add(user)
    await db.flush()

    workspace = Workspace(user_id=user.id, name=f"{req.email}'s Workspace")
    db.add(workspace)

    profile = LearnerProfile(
        user_id=user.id,
        preferences={
            "learning_style": "practical",
            "explanation_depth": "detailed",
            "daily_minutes": 45,
            "analogies_preferred": True
        }
    )
    db.add(profile)
    await db.commit()
    await db.refresh(workspace)

    token = create_access_token(data={"sub": user.id, "email": user.email})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        workspace_id=workspace.id
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate student credentials and return access token."""
    res = await db.execute(
        select(User).options(selectinload(User.workspaces)).where(User.email == req.email)
    )
    user = res.scalar_one_or_none()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    workspace_id = user.workspaces[0].id if user.workspaces else ""
    token = create_access_token(data={"sub": user.id, "email": user.email})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        workspace_id=workspace_id
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """Retrieve authenticated student details and learner profile."""
    workspace_id = user.workspaces[0].id if user.workspaces else None
    profile_data = None
    if user.profile:
        profile_data = LearnerProfileResponse(
            id=user.profile.id,
            user_id=user.profile.user_id,
            preferences=user.profile.preferences or {},
            topic_mastery=user.profile.topic_mastery or {},
            weak_areas=user.profile.weak_areas or [],
            unresolved_doubts=user.profile.unresolved_doubts or [],
            completed_lessons=user.profile.completed_lessons or []
        )

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        workspace_id=workspace_id,
        profile=profile_data
    )


@router.put("/profile", response_model=LearnerProfileResponse)
async def update_profile_preferences(
    req: UpdatePreferencesRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update learner personalization preferences."""
    profile = user.profile
    if not profile:
        profile = LearnerProfile(user_id=user.id, preferences={})
        db.add(profile)

    prefs = dict(profile.preferences or {})
    if req.learning_style is not None:
        prefs["learning_style"] = req.learning_style
    if req.explanation_depth is not None:
        prefs["explanation_depth"] = req.explanation_depth
    if req.daily_minutes is not None:
        prefs["daily_minutes"] = req.daily_minutes
    if req.analogies_preferred is not None:
        prefs["analogies_preferred"] = req.analogies_preferred

    profile.preferences = prefs
    await db.commit()
    await db.refresh(profile)

    return LearnerProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        preferences=profile.preferences,
        topic_mastery=profile.topic_mastery or {},
        weak_areas=profile.weak_areas or [],
        unresolved_doubts=profile.unresolved_doubts or [],
        completed_lessons=profile.completed_lessons or []
    )


@router.delete("/account", status_code=status.HTTP_200_OK)
async def delete_account(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Permanently delete user account and all personal learning data."""
    await db.delete(user)
    await db.commit()
    return {"status": "success", "message": "Account and all associated personal data permanently removed."}
