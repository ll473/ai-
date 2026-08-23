from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user
from backend.app.core.database import get_db
from backend.app.core.exceptions import AppError, NotFoundError
from backend.app.core.responses import ApiResponse
from backend.app.models.ai import Conversation, ConversationMessage
from backend.app.models.enums import ConversationRole, QuestionType
from backend.app.models.trade import AfterSaleRule, Order
from backend.app.models.user import User
from backend.app.repositories.ai import AiRepository
from backend.app.schemas.ai import (
    AgentRunPublic,
    ConversationDetail,
    ConversationMessagePublic,
    ConversationPublic,
    ProductQuestionRequest,
    ProductQuestionResponse,
    ShoppingGuideRequest,
)
from backend.app.schemas.common import PageData
from backend.app.services.knowledge import KnowledgeService
from backend.app.services.product_price_stock import ProductPriceStockService
from backend.app.services.shopping_agent import ShoppingAgentService

router = APIRouter(prefix="/ai", tags=["AI 导购"])
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("/shopping-guide", response_model=ApiResponse[AgentRunPublic])
async def shopping_guide(
    payload: ShoppingGuideRequest, session: DbSession, user: CurrentUser
) -> ApiResponse[AgentRunPublic]:
    return ApiResponse(
        message="导购任务执行完成",
        data=await ShoppingAgentService(session).run(user.id, payload),
    )


@router.get("/runs", response_model=ApiResponse[PageData[AgentRunPublic]])
async def list_runs(
    session: DbSession,
    user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=30)] = 10,
) -> ApiResponse[PageData[AgentRunPublic]]:
    return ApiResponse(
        data=await ShoppingAgentService(session).list_user_runs(
            user.id, page=page, page_size=page_size
        )
    )


@router.get("/runs/{run_id}", response_model=ApiResponse[AgentRunPublic])
async def get_run(
    run_id: int, session: DbSession, user: CurrentUser
) -> ApiResponse[AgentRunPublic]:
    return ApiResponse(data=await ShoppingAgentService(session).get_run(user.id, run_id))


@router.post("/product-qa", response_model=ApiResponse[ProductQuestionResponse])
async def product_question(
    payload: ProductQuestionRequest, session: DbSession, user: CurrentUser
) -> ApiResponse[ProductQuestionResponse]:
    repository = AiRepository(session)
    if payload.conversation_id is not None:
        conversation = await repository.get_conversation(
            payload.conversation_id, user_id=user.id
        )
        if conversation is None or conversation.scene != "PRODUCT_QA":
            raise NotFoundError("问答会话不存在")
    else:
        conversation = Conversation(
            user_id=user.id,
            title=payload.question[:40],
            scene="PRODUCT_QA",
            last_message_at=datetime.now(UTC),
        )
        repository.add(conversation)
        await session.flush()
    repository.add(
        ConversationMessage(
            conversation_id=conversation.id,
            role=ConversationRole.USER,
            content=payload.question,
            question_type=payload.question_type,
            metadata_json={"product_id": payload.product_id, "order_no": payload.order_no},
        )
    )
    if payload.question_type == QuestionType.PRODUCT_KNOWLEDGE:
        result = await KnowledgeService(session).ask(payload)
    elif payload.question_type == QuestionType.PRICE_STOCK:
        if payload.product_id is None:
            raise AppError("查询价格库存时必须选择商品", code="PRODUCT_REQUIRED")
        price_stock = await ProductPriceStockService(session).get(payload.product_id)
        lines: list[str] = []
        for item in price_stock.skus:
            line = f"{item.sku_name}：¥{item.price}，可售库存 {item.available_stock} 件"
            if item.promotion is not None:
                line += (
                    f"，优惠 {item.promotion.name}，"
                    f"预计优惠 ¥{item.promotion.discount_amount}"
                )
            lines.append(line)
        result = ProductQuestionResponse(
            answer="；".join(lines) or "当前没有可售规格。",
            question_type=payload.question_type,
            citations=[],
        )
    elif payload.question_type == QuestionType.ORDER_STATUS:
        if not payload.order_no:
            raise AppError("查询订单状态时必须填写订单号", code="ORDER_NO_REQUIRED")
        order = await session.scalar(
            select(Order).where(Order.user_id == user.id, Order.order_no == payload.order_no)
        )
        if order is None:
            raise NotFoundError("未找到该订单")
        result = ProductQuestionResponse(
            answer=(
                f"订单 {order.order_no} 当前状态为 {order.status.value}，"
                f"应付 ¥{order.payable_amount}，已支付 ¥{order.paid_amount}。"
            ),
            question_type=payload.question_type,
            citations=[],
        )
    else:
        rules = list(
            (
                await session.scalars(
                    select(AfterSaleRule)
                    .where(AfterSaleRule.enabled.is_(True))
                    .order_by(AfterSaleRule.priority.desc(), AfterSaleRule.id)
                )
            ).all()
        )
        normalized = payload.question.lower()
        matched = [
            rule for rule in rules
            if not rule.keywords or any(word.lower() in normalized for word in rule.keywords)
        ]
        result = ProductQuestionResponse(
            answer="\n\n".join(f"【{rule.name}】{rule.content}" for rule in matched[:3])
            or "暂未找到匹配的售后规则，请联系人工客服。",
            question_type=payload.question_type,
            citations=[],
        )
    result.conversation_id = conversation.id
    repository.add(
        ConversationMessage(
            conversation_id=conversation.id,
            role=ConversationRole.ASSISTANT,
            content=result.answer,
            question_type=payload.question_type,
            metadata_json={"citations": [item.model_dump() for item in result.citations]},
        )
    )
    conversation.last_message_at = datetime.now(UTC)
    await session.commit()
    return ApiResponse(data=result)


@router.get("/conversations", response_model=ApiResponse[PageData[ConversationPublic]])
async def list_conversations(
    session: DbSession,
    user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=30)] = 10,
) -> ApiResponse[PageData[ConversationPublic]]:
    rows, total = await AiRepository(session).list_conversations(
        user.id, page=page, page_size=page_size
    )
    return ApiResponse(
        data=PageData(
            items=[
                ConversationPublic(
                    id=item.id,
                    title=item.title,
                    scene=item.scene,
                    last_message_at=item.last_message_at,
                    message_count=count,
                    created_at=item.created_at,
                )
                for item, count in rows
            ],
            page=page,
            page_size=page_size,
            total=total,
        )
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ApiResponse[ConversationDetail],
)
async def get_conversation(
    conversation_id: int, session: DbSession, user: CurrentUser
) -> ApiResponse[ConversationDetail]:
    repository = AiRepository(session)
    conversation = await repository.get_conversation(conversation_id, user_id=user.id)
    if conversation is None:
        raise NotFoundError("会话不存在")
    messages = await repository.list_conversation_messages(conversation.id, limit=100)
    return ApiResponse(
        data=ConversationDetail(
            id=conversation.id,
            title=conversation.title,
            scene=conversation.scene,
            last_message_at=conversation.last_message_at,
            message_count=len(messages),
            created_at=conversation.created_at,
            messages=[ConversationMessagePublic.model_validate(item) for item in messages],
        )
    )
