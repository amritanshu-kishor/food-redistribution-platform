from datetime import datetime, timedelta, timezone
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    verify_password, get_password_hash, create_access_token, create_refresh_token,
    decode_refresh_token, decode_access_token
)
from app.crud.crud import get_user_by_email, create_user, create_audit_log
from app.models.models import User, AuthToken, UserStatus, UserRole
from app.schemas.schemas import (
    Token, UserCreate, UserOut, ChangePasswordRequest, ForgotPasswordRequest,
    ResetPasswordRequest
)
from app.api.deps import get_current_user
from app.utils.notifications import send_email

router = APIRouter()

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new user (Restaurant, NGO, or Admin)."""
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
    user = get_user_by_email(db, email=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
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
        token=refresh_token,
        token_type="refresh",
        expires_at=expires_at,
        is_revoked=False
    )
    db.add(db_token)
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
def logout(refresh_token: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Revoke a refresh token on user logout."""
    db_token = db.query(AuthToken).filter(AuthToken.token == refresh_token).first()
    if db_token:
        db_token.is_revoked = True
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
def refresh(refresh_token: str, db: Session = Depends(get_db)):
    """Yield a new access token using a valid, unrevoked refresh token."""
    try:
        payload = decode_refresh_token(refresh_token)
        user_id = int(payload.get("sub"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token."
        )
        
    # Check token DB presence
    db_token = db.query(AuthToken).filter(
        AuthToken.token == refresh_token,
        AuthToken.is_revoked == False,
        AuthToken.expires_at > datetime.utcnow()
    ).first()
    
    if not db_token:
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
        token=new_refresh_token,
        token_type="refresh",
        expires_at=expires_at,
        is_revoked=False
    )
    db.add(new_db_token)
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
        
    reset_token = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=1)
    
    db_token = AuthToken(
        user_id=user.id,
        token=reset_token,
        token_type="reset",
        expires_at=expires_at,
        is_revoked=False
    )
    db.add(db_token)
    db.commit()
    
    reset_url = f"http://localhost:5173/reset-password?token={reset_token}"
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
    return {"detail": "Password reset link has been sent to your email."}

@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password using a valid reset token."""
    db_token = db.query(AuthToken).filter(
        AuthToken.token == req.token,
        AuthToken.token_type == "reset",
        AuthToken.is_revoked == False,
        AuthToken.expires_at > datetime.utcnow()
    ).first()
    
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token."
        )
        
    user = db_token.user
    user.hashed_password = get_password_hash(req.new_password)
    db_token.is_revoked = True
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
