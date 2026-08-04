from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import require_admin
from backend.app.core.database import get_db
from backend.app.core.responses import ApiResponse
from backend.app.models.enums import OrderStatus
from backend.app.models.user import User
from backend.app.schemas.common import PageData
from backend.app.schemas.trade import (
    AdminOrderDetail,
    AdminOrderSummary,
    ReviewAdmin,
    ReviewVisibilityUpdate,
)
from backend.app.services.trade import TradeService

router = APIRouter(prefix="/admin", tags=["管理端交易"])
DbSession = Annotated[AsyncSession, Depends(get_db)]
AdminUser = Annotated[User, Depends(require_admin)]


@router.get("/orders", response_model=ApiResponse[PageData[AdminOrderSummary]])
async def list_orders(
    session: DbSession,
    _: AdminUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    order_status: OrderStatus | None = None,
) -> ApiResponse[PageData[AdminOrderSummary]]:
    return ApiResponse(
        data=await TradeService(session).list_admin_orders(
            page=page, page_size=page_size, order_status=order_status
        )
    )


@router.get("/orders/{order_id}", response_model=ApiResponse[AdminOrderDetail])
async def get_order(
    order_id: int, session: DbSession, _: AdminUser
) -> ApiResponse[AdminOrderDetail]:
    return ApiResponse(data=await TradeService(session).get_admin_order(order_id))


@router.post("/orders/{order_id}/ship", response_model=ApiResponse[AdminOrderDetail])
async def ship_order(
    order_id: int, session: DbSession, _: AdminUser
) -> ApiResponse[AdminOrderDetail]:
    return ApiResponse(
        message="订单已发货",
        data=await TradeService(session).ship_order(order_id),
    )


@router.post("/orders/{order_id}/complete", response_model=ApiResponse[AdminOrderDetail])
async def complete_order(
    order_id: int, session: DbSession, _: AdminUser
) -> ApiResponse[AdminOrderDetail]:
    return ApiResponse(
        message="订单已完成",
        data=await TradeService(session).admin_complete_order(order_id),
    )


@router.get("/reviews", response_model=ApiResponse[PageData[ReviewAdmin]])
async def list_reviews(
    session: DbSession,
    _: AdminUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ApiResponse[PageData[ReviewAdmin]]:
    return ApiResponse(
        data=await TradeService(session).list_admin_reviews(page=page, page_size=page_size)
    )


@router.patch("/reviews/{review_id}", response_model=ApiResponse[ReviewAdmin])
async def update_review(
    review_id: int,
    payload: ReviewVisibilityUpdate,
    session: DbSession,
    _: AdminUser,
) -> ApiResponse[ReviewAdmin]:
    return ApiResponse(
        message="评价状态已更新",
        data=await TradeService(session).update_review_visibility(review_id, payload.visible),
    )
