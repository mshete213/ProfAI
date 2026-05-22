from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from config import get_settings
from core.security import decode_token
from models import User, UserRole, get_db

settings = get_settings()
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    try:
        payload = decode_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong token type")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject")

    user = db.query(User).filter(User.id == UUID(user_id)).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


def require_professor(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != UserRole.PROFESSOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Professor role required")
    return user


def require_student(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != UserRole.STUDENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student role required")
    return user


def verify_internal_key(x_internal_key: Annotated[str | None, Header(alias="X-Internal-Key")] = None) -> None:
    if x_internal_key != settings.internal_mcp_api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid internal key")
