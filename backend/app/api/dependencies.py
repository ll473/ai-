from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.database import get_db
from backend.app.core.exceptions import AuthenticationError, AuthorizationError
from backend.app.core.security import decode_access_token
from backend.app.models.enums import UserRole, UserStatus
from backend.app.models.user import User
from backend.app.repositories.user import UserRepository

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{get_settings().api_v1_prefix}/auth/login",
    auto_error=False,
)


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if not token:
        raise AuthenticationError("请先登录")
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise AuthenticationError("登录凭证无效或已过期") from exc

    user = await UserRepository(session).get_by_id(user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise AuthenticationError("用户不存在或已被禁用")
    return user


async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise AuthorizationError("需要管理员权限")
    return current_user
