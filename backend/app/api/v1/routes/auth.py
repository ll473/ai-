from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user
from backend.app.core.database import get_db
from backend.app.core.responses import ApiResponse
from backend.app.models.user import User
from backend.app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserPublic
from backend.app.services.auth import AuthService

router = APIRouter()


@router.post(
    "/register",
    response_model=ApiResponse[UserPublic],
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[UserPublic]:
    user = await AuthService(session).register(payload)
    return ApiResponse(message="注册成功", data=UserPublic.model_validate(user))


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login(
    payload: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[TokenResponse]:
    user, token = await AuthService(session).authenticate(payload)
    return ApiResponse(
        message="登录成功",
        data=TokenResponse(access_token=token, user=UserPublic.model_validate(user)),
    )


@router.get("/me", response_model=ApiResponse[UserPublic])
async def me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[UserPublic]:
    return ApiResponse(data=UserPublic.model_validate(current_user))
