from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user
from backend.app.core.database import get_db
from backend.app.core.responses import ApiResponse
from backend.app.models.user import User
from backend.app.schemas.ai import (
    AgentRunPublic,
    ProductQuestionRequest,
    ProductQuestionResponse,
    ShoppingGuideRequest,
)
from backend.app.schemas.common import PageData
from backend.app.services.knowledge import KnowledgeService
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
    payload: ProductQuestionRequest, session: DbSession, _: CurrentUser
) -> ApiResponse[ProductQuestionResponse]:
    return ApiResponse(data=await KnowledgeService(session).ask(payload))
