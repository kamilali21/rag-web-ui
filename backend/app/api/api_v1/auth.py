from datetime import datetime, timedelta
from typing import Any
import re
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from requests.exceptions import RequestException

from app.core import security
from app.core.security import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.services.authorization import assign_researcher, normalize_email, require_active_user, effective_roles
from app.schemas.authentication import OTPRequest, OTPVerification
from app.services import auth_sessions, email_otp

router = APIRouter()

# Added by ChatGPT: failed account lookups still do a password hash comparison.
_DUMMY_PASSWORD_HASH = security.get_password_hash("not-a-user-password")


@router.get("/methods")
def auth_methods(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return {"email_otp": settings.EMAIL_OTP_ENABLED}


@router.post("/request-otp")
def request_otp(payload: OTPRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    auth_sessions.require_origin(request)
    response.headers["Cache-Control"] = "no-store"
    return email_otp.request_code(db, str(payload.email), request, payload.purpose)


@router.post("/verify-otp")
def verify_otp(payload: OTPVerification, request: Request, response: Response, db: Session = Depends(get_db)):
    auth_sessions.require_origin(request)
    response.headers["Cache-Control"] = "no-store"
    return email_otp.verify_code(db, str(payload.email), payload.code, request, payload.password, payload.purpose)


@router.get("/me")
def current_identity(response: Response, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    response.headers["Cache-Control"] = "no-store"
    return {"id": user.id, "username": user.username, "email": user.email,
            "roles": sorted(effective_roles(db, user))}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    if settings.EMAIL_OTP_ENABLED:
        auth_sessions.require_origin(request)
        session = auth_sessions.find_session(db, request)
        if session is not None:
            auth_sessions.require_csrf(request, session)
            session.revoked_at = datetime.utcnow()
            db.commit()
    auth_sessions.clear_session_cookies(response)
    return {"message": "Signed out"}


@router.post("/register", response_model=UserResponse)
def register(*, request: Request, response: Response, db: Session = Depends(get_db), user_in: UserCreate) -> Any:
    """
    Register a new user.
    """
    # Added by ChatGPT: registration reserves an unverified Researcher identity, never a session.
    response.headers["Cache-Control"] = "no-store"
    if settings.EMAIL_OTP_ENABLED:
        auth_sessions.require_origin(request)
        security.validate_new_password(user_in.password)
        if not re.fullmatch(r"[A-Za-z0-9_.-]{3,64}", user_in.username):
            raise HTTPException(400, "Username must be 3-64 letters, numbers, dots, underscores or hyphens.")
        email_otp.lock_limits(db, normalize_email(str(user_in.email)), auth_sessions.client_address(request), "register")
        db.commit()
    try:
        # Added by ChatGPT: registration can assign only researcher, never allowlist-based admin.
        email = normalize_email(str(user_in.email))
        # Check if user with this email exists
        user = db.query(User).filter(User.email == email).first()
        if user:
            raise HTTPException(
                status_code=400,
                detail="Account already exists. Sign in, verify your email, or reset your password.",
            )
        
        # Check if user with this username exists
        user = db.query(User).filter(User.username == user_in.username).first()
        if user:
            raise HTTPException(
                status_code=400,
                detail="A user with this username already exists.",
            )
        
        # Create new user
        user = User(
            email=email,
            username=user_in.username,
            hashed_password=security.get_password_hash(user_in.password),
        )
        assign_researcher(db, user)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email or username is already registered.") from None
    except RequestException as e:
        raise HTTPException(
            status_code=503,
            detail="Network error or server is unreachable. Please try again later.",
        ) from e

@router.post("/token")
def login_access_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    # Added by ChatGPT: normal password sign-in uses opaque sessions when email verification is enabled.
    identifier = form_data.username.strip()
    if len(identifier) > 255:
        raise HTTPException(401, "Incorrect email, username or password")
    if settings.EMAIL_OTP_ENABLED:
        auth_sessions.require_origin(request)
        email_otp.lock_limits(db, normalize_email(identifier), auth_sessions.client_address(request), "password")
    query = db.query(User).filter(User.email == normalize_email(identifier) if "@" in identifier else User.username == identifier)
    user = query.first()
    # Lock only existing users: serialize password changes without gap-locking new signups.
    if user is not None:
        user = db.query(User).filter_by(id=user.id).populate_existing().with_for_update().one()
    exact_identity = user and (normalize_email(user.email) == normalize_email(identifier) if "@" in identifier else user.username == identifier)
    valid_password = security.verify_password(form_data.password, user.hashed_password if user and user.hashed_password else _DUMMY_PASSWORD_HASH)
    if not exact_identity or not user.hashed_password or not valid_password or not user.is_active or user.is_system:
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email, username or password. OTP-only accounts must set a password first.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    require_active_user(user)
    if settings.EMAIL_OTP_ENABLED:
        if user.email_verified_at is None:
            db.commit()
            response.headers["Cache-Control"] = "no-store"
            return {"verification_required": True, "email": user.email}
        token, csrf = auth_sessions.create_session(db, user, request)
        db.commit()
        auth_sessions.set_session_cookies(response, token, csrf, request)
        return {"authenticated": True}
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    # Added by ChatGPT: stale OTP CSRF cookies must not shadow this explicitly enabled legacy token.
    auth_sessions.clear_session_cookies(response)
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/test-token", response_model=UserResponse)
def test_token(current_user: User = Depends(get_current_user)) -> Any:
    """
    Test access token by getting current user.
    """
    return current_user
