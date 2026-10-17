import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.db.models import User, Workspace, LearnerProfile
from app.schemas.auth import (
    UserRegisterRequest, UserLoginRequest, TokenResponse, UserResponse,
    LearnerProfileResponse, UpdatePreferencesRequest
)
from app.services.auth_service import hash_password, verify_password, create_access_token, burn_password_check
from app.api.deps import get_current_user

logger = logging.getLogger("learnweave.api.auth")
INVALID_CREDENTIALS = "Invalid email or password"

from app.api.rate_limit import limit_by_ip, limit_by_user, check_login_allowed, record_login_failure, clear_login_failures

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(limit_by_ip('register', 10, 3600))])
async def register(req: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new student account, workspace, and initial learner profile."""
    duplicate_detail = "An account with this email already exists"

    # Emails are normalized to lowercase; the lower() comparison also catches legacy mixed-case rows.
    existing = await db.execute(select(User.id).where(func.lower(User.email) == req.email))
    if existing.first() is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=duplicate_detail)

    # Atomic user + workspace + profile creation
    user = User(
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError:
        # Lost a race with a concurrent registration for the same email.
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=duplicate_detail)

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
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=duplicate_detail)
    await db.refresh(workspace)

    token = create_access_token(data={"sub": user.id, "email": user.email})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        workspace_id=workspace.id
    )


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(limit_by_ip('login', 30, 60))])
async def login(req: UserLoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Authenticate student credentials and return access token."""
    check_login_allowed(req.email, request)
    res = await db.execute(
        select(User).options(selectinload(User.workspaces)).where(func.lower(User.email) == req.email)
    )
    user = res.scalar_one_or_none()
    if user is None:
        burn_password_check(req.password)
        password_ok = False
    else:
        password_ok = verify_password(req.password, user.hashed_password)

    # Same response for unknown email, wrong password and deactivated account.
    if user is None or not password_ok or not user.is_active:
        record_login_failure(req.email, request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS,
            headers={"WWW-Authenticate": "Bearer"},
        )

    clear_login_failures(req.email, request)
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
