from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    verify_password, get_password_hash, create_access_token, create_refresh_token,
    decode_refresh_token, hash_token
)
from app.crud.crud import get_user_by_email, create_user, create_audit_log
from app.models.models import User, AuthToken, UserStatus, UserRole
from app.schemas.schemas import (
    Token, UserCreate, UserOut, ChangePasswordRequest, ForgotPasswordRequest,
    ResetPasswordRequest, RefreshTokenRequest
)
from app.api.deps import get_current_user
from app.utils.notifications import send_email

router = APIRouter()
_DUMMY_PASSWORD_HASH = get_password_hash(uuid.uuid4().hex)


def _persist_access_token(db: Session, user_id: int, access_token: str, expires_at: datetime) -> None:
    db.add(AuthToken(
        user_id=user_id,
        token=hash_token(access_token),
        token_type="access",
        expires_at=expires_at,
        is_revoked=False,
    ))

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a partner account. Administrators use the private bootstrap command."""
    if user_in.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator accounts are created by the server bootstrap only.",
        )
    db_user = get_user_by_email(db, email=user_in.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email is already registered."
        )
    return create_user(db, user_in)

@router.post("/login", response_model=Token)
def login(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """Authenticate via email and password, returning JWT access & refresh tokens."""
    user = get_user_by_email(db, email=form_data.username.strip().lower())
    password_hash = user.hashed_password if user else _DUMMY_PASSWORD_HASH
    password_matches = verify_password(form_data.password, password_hash)
    if not user or not password_matches:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Check if user status allows login
    if user.status == UserStatus.SUSPENDED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been suspended. Please contact administrators."
        )
    elif user.status == UserStatus.REJECTED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account verification request was rejected."
        )
    elif user.status == UserStatus.DEACTIVATED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is deactivated. Please register a new account or reactivate."
        )
        
    # Access and refresh tokens
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    
    # Store refresh token in db
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    db_token = AuthToken(
        user_id=user.id,
        token=hash_token(refresh_token),
        token_type="refresh",
        expires_at=expires_at,
        is_revoked=False
    )
    db.add(db_token)
    _persist_access_token(
        db,
        user.id,
        access_token,
        datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    db.commit()
    
    create_audit_log(
        db,
        actor_id=user.id,
        action="user_login",
        target_table="users",
        target_id=user.id
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    payload: Optional[RefreshTokenRequest] = Body(None),
    refresh_token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke a refresh token on user logout."""
    raw_token = payload.refresh_token if payload else refresh_token
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token is required")
    db_token = db.query(AuthToken).filter(
        AuthToken.token == hash_token(raw_token),
        AuthToken.user_id == current_user.id,
        AuthToken.token_type == "refresh",
    ).first()
    if db_token:
        db_token.is_revoked = True
    db.query(AuthToken).filter(
        AuthToken.user_id == current_user.id,
        AuthToken.token_type.in_(["access", "refresh", "reset"]),
        AuthToken.is_revoked == False,
    ).update({"is_revoked": True}, synchronize_session=False)
    db.commit()
        
    create_audit_log(
        db,
        actor_id=current_user.id,
        action="user_logout",
        target_table="users",
        target_id=current_user.id
    )
    return {"detail": "Successfully logged out."}

@router.post("/refresh", response_model=Token)
def refresh(
    payload: Optional[RefreshTokenRequest] = Body(None),
    refresh_token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Yield a new access token using a valid, unrevoked refresh token."""
    raw_token = payload.refresh_token if payload else refresh_token
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")
    try:
        token_payload = decode_refresh_token(raw_token)
        if token_payload.get("type") != "refresh":
            raise ValueError("invalid token type")
        user_id = int(token_payload.get("sub"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token."
        )
        
    # Check token DB presence
    db_token = db.query(AuthToken).filter(
        AuthToken.token == hash_token(raw_token),
        AuthToken.token_type == "refresh",
        AuthToken.is_revoked == False,
        AuthToken.expires_at > datetime.utcnow()
    ).with_for_update().first()
    user = db.query(User).filter(User.id == user_id).first()
    
    if not db_token or not user or user.status in {
        UserStatus.SUSPENDED,
        UserStatus.REJECTED,
        UserStatus.DEACTIVATED,
    }:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is expired or revoked."
        )
        
    # Generate new tokens
    access_token = create_access_token(subject=user_id)
    new_refresh_token = create_refresh_token(subject=user_id)
    
    # Revoke old token and save new one
    db_token.is_revoked = True
    
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    new_db_token = AuthToken(
        user_id=user_id,
        token=hash_token(new_refresh_token),
        token_type="refresh",
        expires_at=expires_at,
        is_revoked=False
    )
    db.add(new_db_token)
    _persist_access_token(
        db,
        user_id,
        access_token,
        datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

@router.post("/change-password", status_code=status.HTTP_200_OK)
def change_password(
    req: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Modify the password of an authenticated user."""
    if not verify_password(req.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password."
        )
    current_user.hashed_password = get_password_hash(req.new_password)
    db.query(AuthToken).filter(
        AuthToken.user_id == current_user.id,
        AuthToken.token_type.in_(["access", "refresh", "reset"]),
        AuthToken.is_revoked == False,
    ).update({"is_revoked": True}, synchronize_session=False)
    db.commit()
    
    create_audit_log(
        db,
        actor_id=current_user.id,
        action="user_change_password",
        target_table="users",
        target_id=current_user.id
    )
    return {"detail": "Password updated successfully."}

@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Request a password reset link by email."""
    user = get_user_by_email(db, email=req.email)
    if not user:
        # Avoid user enumeration attacks; return 200 OK anyway
        return {"detail": "If the email exists, a password reset link has been sent."}
        
    reset_token = uuid.uuid4().hex + uuid.uuid4().hex
    expires_at = datetime.utcnow() + timedelta(hours=1)
    
    db_token = AuthToken(
        user_id=user.id,
        token=hash_token(reset_token),
        token_type="reset",
        expires_at=expires_at,
        is_revoked=False
    )
    db.add(db_token)
    db.commit()
    
    reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={reset_token}"
    email_body = f"""
    <html>
        <body>
            <p>Hello,</p>
            <p>You requested a password reset. Click the link below to set a new password:</p>
            <p><a href="{reset_url}">{reset_url}</a></p>
            <p>This link is valid for 1 hour.</p>
        </body>
    </html>
    """
    send_email(user.email, "[FoodShare] Reset Password", email_body)
    
    create_audit_log(
        db,
        actor_id=user.id,
        action="user_forgot_password_request",
        target_table="users",
        target_id=user.id
    )
    return {"detail": "If the email exists, a password reset link has been sent."}

@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password using a valid reset token."""
    db_token = db.query(AuthToken).filter(
        AuthToken.token == hash_token(req.token),
        AuthToken.token_type == "reset",
        AuthToken.is_revoked == False,
        AuthToken.expires_at > datetime.utcnow()
    ).with_for_update().first()
    
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token."
        )
        
    user = db_token.user
    user.hashed_password = get_password_hash(req.new_password)
    db_token.is_revoked = True
    db.query(AuthToken).filter(
        AuthToken.user_id == user.id,
        AuthToken.token_type.in_(["access", "refresh", "reset"]),
        AuthToken.is_revoked == False,
    ).update({"is_revoked": True}, synchronize_session=False)
    db.commit()
    
    create_audit_log(
        db,
        actor_id=user.id,
        action="user_reset_password",
        target_table="users",
        target_id=user.id
    )
    return {"detail": "Password reset completed successfully."}

@router.get("/verify-email", status_code=status.HTTP_200_OK)
def verify_email(token: str, db: Session = Depends(get_db)):
    """Architectural email verification endpoint."""
    db_token = db.query(AuthToken).filter(
        AuthToken.token == token,
        AuthToken.token_type == "email_verification",
        AuthToken.is_revoked == False,
        AuthToken.expires_at > datetime.utcnow()
    ).first()
    
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token."
        )
        
    user = db_token.user
    # Email is verified
    db_token.is_revoked = True
    db.commit()
    
    create_audit_log(
        db,
        actor_id=user.id,
        action="user_verify_email",
        target_table="users",
        target_id=user.id
    )
    return {"detail": "Email address verified successfully!"}
