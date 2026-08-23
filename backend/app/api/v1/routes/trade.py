from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user
from backend.app.core.config import get_settings
from backend.app.core.database import get_db
from backend.app.core.exceptions import AuthorizationError
from backend.app.core.responses import ApiResponse
from backend.app.models.user import User
from backend.app.schemas.catalog import ProductSummary
from backend.app.schemas.common import PageData
from backend.app.schemas.trade import (
    AddressCreate,
    AddressPublic,
    AddressUpdate,
    CartAddRequest,
    CartSelectRequest,
    CartSummary,
    CartUpdateRequest,
    CheckoutRequest,
    OrderDetail,
    OrderSummary,
    PaymentResult,
    RechargeRequest,
    ReviewCreate,
    ReviewPublic,
    WalletPublic,
    WalletTransactionPublic,
)
from backend.app.services.trade import TradeService

router = APIRouter(tags=["交易闭环"])
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/favorites", response_model=ApiResponse[PageData[ProductSummary]])
async def list_favorites(
    session: DbSession,
    user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> ApiResponse[PageData[ProductSummary]]:
    return ApiResponse(
        data=await TradeService(session).list_favorites(
            user.id, page=page, page_size=page_size
        )
    )


@router.get("/favorites/{product_id}/status", response_model=ApiResponse[bool])
async def favorite_status(
    product_id: int, session: DbSession, user: CurrentUser
) -> ApiResponse[bool]:
    return ApiResponse(data=await TradeService(session).is_favorite(user.id, product_id))


@router.post("/favorites/{product_id}", response_model=ApiResponse[ProductSummary])
async def add_favorite(
    product_id: int, session: DbSession, user: CurrentUser
) -> ApiResponse[ProductSummary]:
    return ApiResponse(
        message="已加入收藏",
        data=await TradeService(session).add_favorite(user.id, product_id),
    )


@router.delete("/favorites/{product_id}", response_model=ApiResponse[None])
async def remove_favorite(
    product_id: int, session: DbSession, user: CurrentUser
) -> ApiResponse[None]:
    await TradeService(session).remove_favorite(user.id, product_id)
    return ApiResponse(message="已取消收藏")


@router.get("/addresses", response_model=ApiResponse[list[AddressPublic]])
async def list_addresses(session: DbSession, user: CurrentUser) -> ApiResponse[list[AddressPublic]]:
    return ApiResponse(data=await TradeService(session).list_addresses(user.id))


@router.post(
    "/addresses",
    response_model=ApiResponse[AddressPublic],
    status_code=status.HTTP_201_CREATED,
)
async def create_address(
    payload: AddressCreate, session: DbSession, user: CurrentUser
) -> ApiResponse[AddressPublic]:
    return ApiResponse(
        message="收货地址已保存",
        data=await TradeService(session).create_address(user.id, payload),
    )


@router.patch("/addresses/{address_id}", response_model=ApiResponse[AddressPublic])
async def update_address(
    address_id: int,
    payload: AddressUpdate,
    session: DbSession,
    user: CurrentUser,
) -> ApiResponse[AddressPublic]:
    return ApiResponse(
        data=await TradeService(session).update_address(user.id, address_id, payload)
    )


@router.delete("/addresses/{address_id}", response_model=ApiResponse[None])
async def delete_address(
    address_id: int, session: DbSession, user: CurrentUser
) -> ApiResponse[None]:
    await TradeService(session).delete_address(user.id, address_id)
    return ApiResponse(message="收货地址已删除")


@router.get("/cart", response_model=ApiResponse[CartSummary])
async def get_cart(session: DbSession, user: CurrentUser) -> ApiResponse[CartSummary]:
    return ApiResponse(data=await TradeService(session).get_cart(user.id))


@router.post(
    "/cart/items", response_model=ApiResponse[CartSummary], status_code=status.HTTP_201_CREATED
)
async def add_to_cart(
    payload: CartAddRequest, session: DbSession, user: CurrentUser
) -> ApiResponse[CartSummary]:
    return ApiResponse(
        message="已加入购物车",
        data=await TradeService(session).add_to_cart(user.id, payload),
    )


@router.patch("/cart/items/{item_id}", response_model=ApiResponse[CartSummary])
async def update_cart_item(
    item_id: int,
    payload: CartUpdateRequest,
    session: DbSession,
    user: CurrentUser,
) -> ApiResponse[CartSummary]:
    return ApiResponse(data=await TradeService(session).update_cart_item(user.id, item_id, payload))


@router.put("/cart/selection", response_model=ApiResponse[CartSummary])
async def select_all_cart_items(
    payload: CartSelectRequest, session: DbSession, user: CurrentUser
) -> ApiResponse[CartSummary]:
    return ApiResponse(
        data=await TradeService(session).select_all_cart_items(user.id, payload.selected)
    )


@router.delete("/cart/items/{item_id}", response_model=ApiResponse[CartSummary])
async def delete_cart_item(
    item_id: int, session: DbSession, user: CurrentUser
) -> ApiResponse[CartSummary]:
    return ApiResponse(data=await TradeService(session).delete_cart_item(user.id, item_id))


@router.get("/wallet", response_model=ApiResponse[WalletPublic])
async def get_wallet(session: DbSession, user: CurrentUser) -> ApiResponse[WalletPublic]:
    return ApiResponse(data=await TradeService(session).get_wallet(user.id))


@router.post("/wallet/recharge", response_model=ApiResponse[WalletPublic])
async def recharge_wallet(
    payload: RechargeRequest, session: DbSession, user: CurrentUser
) -> ApiResponse[WalletPublic]:
    if not get_settings().enable_demo_recharge:
        raise AuthorizationError("演示充值功能未启用")
    return ApiResponse(
        message="充值成功",
        data=await TradeService(session).recharge_wallet(user.id, payload.amount),
    )


@router.get(
    "/wallet/transactions",
    response_model=ApiResponse[PageData[WalletTransactionPublic]],
)
async def list_wallet_transactions(
    session: DbSession,
    user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> ApiResponse[PageData[WalletTransactionPublic]]:
    return ApiResponse(
        data=await TradeService(session).list_wallet_transactions(
            user.id, page=page, page_size=page_size
        )
    )


@router.post(
    "/orders",
    response_model=ApiResponse[OrderDetail],
    status_code=status.HTTP_201_CREATED,
)
async def create_order(
    payload: CheckoutRequest, session: DbSession, user: CurrentUser
) -> ApiResponse[OrderDetail]:
    return ApiResponse(
        message="订单已创建，请完成支付",
        data=await TradeService(session).create_order(user.id, payload),
    )


@router.get("/orders", response_model=ApiResponse[PageData[OrderSummary]])
async def list_orders(
    session: DbSession,
    user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> ApiResponse[PageData[OrderSummary]]:
    return ApiResponse(
        data=await TradeService(session).list_orders(user.id, page=page, page_size=page_size)
    )


@router.get("/orders/{order_id}", response_model=ApiResponse[OrderDetail])
async def get_order(
    order_id: int, session: DbSession, user: CurrentUser
) -> ApiResponse[OrderDetail]:
    return ApiResponse(data=await TradeService(session).get_order(user.id, order_id))


@router.post("/orders/{order_id}/pay", response_model=ApiResponse[PaymentResult])
async def pay_order(
    order_id: int, session: DbSession, user: CurrentUser
) -> ApiResponse[PaymentResult]:
    return ApiResponse(
        message="支付成功",
        data=await TradeService(session).pay_order(user.id, order_id),
    )


@router.post("/orders/{order_id}/cancel", response_model=ApiResponse[OrderDetail])
async def cancel_order(
    order_id: int, session: DbSession, user: CurrentUser
) -> ApiResponse[OrderDetail]:
    return ApiResponse(
        message="订单已取消",
        data=await TradeService(session).cancel_order(user.id, order_id),
    )


@router.post("/orders/{order_id}/complete", response_model=ApiResponse[OrderDetail])
async def complete_order(
    order_id: int, session: DbSession, user: CurrentUser
) -> ApiResponse[OrderDetail]:
    return ApiResponse(
        message="已确认收货",
        data=await TradeService(session).complete_order(user.id, order_id),
    )


@router.post(
    "/reviews",
    response_model=ApiResponse[ReviewPublic],
    status_code=status.HTTP_201_CREATED,
)
async def create_review(
    payload: ReviewCreate, session: DbSession, user: CurrentUser
) -> ApiResponse[ReviewPublic]:
    return ApiResponse(
        message="评价发布成功",
        data=await TradeService(session).create_review(user, payload),
    )
