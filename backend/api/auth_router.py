from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from infrastructure.database import get_db
from infrastructure.models import MdmUser
from core.security import (
    get_current_user, TokenData, verify_password,
    get_password_hash, create_access_token
)
from core.enums import UserRole
from sqlalchemy import select

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    allowed_entities: list = []


class UserCreateRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str = "viewer"
    allowed_entities: list = []


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user and return JWT token."""
    result = await db.execute(
        select(MdmUser).where(MdmUser.username == form_data.username)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role,
            "allowed_entities": user.allowed_entities or []
        }
    )
    
    return TokenResponse(
        access_token=access_token,
        role=user.role,
        allowed_entities=user.allowed_entities or []
    )


@router.get("/me")
async def get_me(current_user: TokenData = Depends(get_current_user)):
    """Get current user info."""
    return {
        "user_id": current_user.user_id,
        "role": current_user.role,
        "allowed_entities": current_user.allowed_entities
    }


@router.post("/users")
async def create_user(
    request: UserCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(lambda: check_role([UserRole.ADMIN]))
):
    """Create new user (admin only)."""
    from core.security import check_role
    
    result = await db.execute(
        select(MdmUser).where(MdmUser.username == request.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")
    
    user = MdmUser(
        username=request.username,
        email=request.email,
        password_hash=get_password_hash(request.password),
        role=request.role,
        allowed_entities=request.allowed_entities
    )
    db.add(user)
    await db.flush()
    
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "role": user.role
    }


def check_role(required_roles: list):
    async def checker(current_user: TokenData = Depends(get_current_user)):
        if current_user.role not in required_roles and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return checker
