# app/api/endpoints/auth.py
#
# Authentication endpoints:
# POST /auth/register  — create account
# POST /auth/login     — get access + refresh tokens
# POST /auth/refresh   — exchange refresh token for new access token
# POST /auth/logout    — invalidate refresh token

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.user import User
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token
)
from app.core.dependencies import get_current_user
from app.schemas.schemas import UserRegister, UserLogin, TokenResponse, RefreshTokenRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user.
    Checks for duplicate email, hashes password, stores user.
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT token pair.
    
    We use the same error message for "user not found" and "wrong password"
    intentionally — this prevents user enumeration attacks where an attacker
    could figure out which emails are registered.
    """
    user = db.query(User).filter(User.email == payload.email).first()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account is inactive")

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    # Store refresh token in DB so we can invalidate it on logout
    user.refresh_token = refresh_token
    db.commit()

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Exchange a valid refresh token for a new access + refresh token pair.
    Rotates the refresh token (old one is invalidated) — better security.
    """
    token_data = decode_token(payload.refresh_token)

    if not token_data or token_data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.query(User).filter(
        User.id == token_data["sub"],
        User.refresh_token == payload.refresh_token  # must match stored token
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")

    # Rotate tokens
    new_access = create_access_token({"sub": str(user.id)})
    new_refresh = create_refresh_token({"sub": str(user.id)})
    user.refresh_token = new_refresh
    db.commit()

    return TokenResponse(access_token=new_access, refresh_token=new_refresh)


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Logout by invalidating the stored refresh token.
    The access token will still work until it expires (30 min),
    which is acceptable for stateless JWT auth.
    """
    current_user.refresh_token = None
    db.commit()
    return {"message": "Logged out successfully"}
