from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from app.core.config import settings
from fastapi import Depends, HTTPException, status, Security, Request
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.services.api_key import APIKeyService
from app.services.authorization import require_active_user, require_admin
from app.services.auth_sessions import authenticate_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_password(plain_password: str, hashed_password: Optional[str]) -> bool:
    # Added by ChatGPT: OTP-only identities must fail password login without crashing.
    if not hashed_password:
        return False
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt 

def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme)
) -> User:
    # Added by ChatGPT: OTP cutover rejects legacy JWTs; cookies never bypass CSRF via Bearer.
    if settings.EMAIL_OTP_ENABLED:
        return authenticate_session(db, request)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if not isinstance(username, str) or not username:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    # Added by ChatGPT: system identities cannot authenticate through any credential type.
    return require_active_user(user)


def get_current_admin(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> User:
    # Added by ChatGPT: role/allowlist revocations take effect on the next request.
    return require_admin(db, current_user)

def get_api_key_user(
    db: Session = Depends(get_db),
    api_key: str = Security(api_key_header),
) -> User:
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key header missing",
        )
    
    api_key_obj = APIKeyService.get_api_key_by_key(db=db, key=api_key)
    if not api_key_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    
    if not api_key_obj.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive API key",
        )
    
    user = require_active_user(api_key_obj.user)
    APIKeyService.update_last_used(db=db, api_key=api_key_obj)
    return user
