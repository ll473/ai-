from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import require_admin
from backend.app.core.database import get_db
from backend.app.core.exceptions import NotFoundError
from backend.app.core.responses import ApiResponse
from backend.app.models.trade import AfterSaleRule
from backend.app.models.user import User
from backend.app.schemas.admin import (
    AdminUserStatusUpdate,
    AfterSaleRuleCreate,
    AfterSaleRulePublic,
    AfterSaleRuleUpdate,
)
from backend.app.schemas.auth import UserPublic
from backend.app.schemas.common import PageData

router = APIRouter(prefix="/admin", tags=["管理端系统"])
DbSession = Annotated[AsyncSession, Depends(get_db)]
AdminUser = Annotated[User, Depends(require_admin)]


@router.get("/users", response_model=ApiResponse[PageData[UserPublic]])
async def list_users(
    session: DbSession,
    _: AdminUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    keyword: str | None = None,
    user_status: str | None = None,
) -> ApiResponse[PageData[UserPublic]]:
    statement = select(User)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        statement = statement.where(
            or_(
                User.username.ilike(pattern),
                User.nickname.ilike(pattern),
                User.email.ilike(pattern),
                User.phone.ilike(pattern),
            )
        )
    if user_status:
        statement = statement.where(User.status == user_status)
    total = int(await session.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    users = list(
        (
            await session.scalars(
                statement.order_by(User.created_at.desc(), User.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
    )
    return ApiResponse(
        data=PageData[UserPublic](
            items=[UserPublic.model_validate(user) for user in users],
            page=page,
            page_size=page_size,
            total=total,
        )
    )


@router.patch("/users/{user_id}/status", response_model=ApiResponse[UserPublic])
async def update_user_status(
    user_id: int,
    payload: AdminUserStatusUpdate,
    session: DbSession,
    admin: AdminUser,
) -> ApiResponse[UserPublic]:
    user = await session.get(User, user_id)
    if user is None:
        raise NotFoundError("用户不存在")
    if user.id == admin.id and payload.status.value == "DISABLED":
        from backend.app.core.exceptions import AppError

        raise AppError("不能停用当前登录账号", code="CANNOT_DISABLE_SELF")
    user.status = payload.status
    await session.commit()
    await session.refresh(user)
    return ApiResponse(message="用户状态已更新", data=UserPublic.model_validate(user))


@router.get("/after-sale-rules", response_model=ApiResponse[PageData[AfterSaleRulePublic]])
async def list_after_sale_rules(
    session: DbSession,
    _: AdminUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    keyword: str | None = None,
    rule_type: str | None = None,
) -> ApiResponse[PageData[AfterSaleRulePublic]]:
    statement = select(AfterSaleRule)
    if keyword:
        statement = statement.where(AfterSaleRule.name.ilike(f"%{keyword.strip()}%"))
    if rule_type:
        statement = statement.where(AfterSaleRule.rule_type == rule_type)
    total = int(await session.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rules = list(
        (
            await session.scalars(
                statement.order_by(AfterSaleRule.priority.desc(), AfterSaleRule.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
    )
    return ApiResponse(
        data=PageData[AfterSaleRulePublic](
            items=[AfterSaleRulePublic.model_validate(rule) for rule in rules],
            page=page,
            page_size=page_size,
            total=total,
        )
    )


@router.post(
    "/after-sale-rules",
    response_model=ApiResponse[AfterSaleRulePublic],
    status_code=status.HTTP_201_CREATED,
)
async def create_after_sale_rule(
    payload: AfterSaleRuleCreate, session: DbSession, _: AdminUser
) -> ApiResponse[AfterSaleRulePublic]:
    rule = AfterSaleRule(**payload.model_dump())
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return ApiResponse(message="售后规则已创建", data=AfterSaleRulePublic.model_validate(rule))


@router.patch("/after-sale-rules/{rule_id}", response_model=ApiResponse[AfterSaleRulePublic])
async def update_after_sale_rule(
    rule_id: int, payload: AfterSaleRuleUpdate, session: DbSession, _: AdminUser
) -> ApiResponse[AfterSaleRulePublic]:
    rule = await session.get(AfterSaleRule, rule_id)
    if rule is None:
        raise NotFoundError("售后规则不存在")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    await session.commit()
    await session.refresh(rule)
    return ApiResponse(message="售后规则已更新", data=AfterSaleRulePublic.model_validate(rule))


@router.delete("/after-sale-rules/{rule_id}", response_model=ApiResponse[None])
async def delete_after_sale_rule(
    rule_id: int, session: DbSession, _: AdminUser
) -> ApiResponse[None]:
    rule = await session.get(AfterSaleRule, rule_id)
    if rule is None:
        raise NotFoundError("售后规则不存在")
    await session.delete(rule)
    await session.commit()
    return ApiResponse(message="售后规则已删除", data=None)
