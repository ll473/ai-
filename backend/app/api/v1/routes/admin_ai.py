from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import require_admin
from backend.app.core.database import get_db
from backend.app.core.responses import ApiResponse
from backend.app.models.user import User
from backend.app.repositories.ai import AiRepository
from backend.app.schemas.ai import (
    AgentRunPublic,
    FunctionToolCreate,
    FunctionToolPublic,
    FunctionToolUpdate,
    ModelConfigCreate,
    ModelConfigPublic,
    ModelConfigUpdate,
    PromptTemplateCreate,
    PromptTemplatePublic,
    PromptTemplateUpdate,
    ToolCallLogPublic,
    ToolExecuteRequest,
    ToolExecutionPublic,
)
from backend.app.schemas.common import PageData
from backend.app.services.ai_management import AiManagementService
from backend.app.services.shopping_agent import ShoppingAgentService
from backend.app.services.tool_center import ToolCenter, ToolContext

router = APIRouter(prefix="/admin/ai", tags=["管理端 AI"])
DbSession = Annotated[AsyncSession, Depends(get_db)]
AdminUser = Annotated[User, Depends(require_admin)]


@router.get("/models", response_model=ApiResponse[list[ModelConfigPublic]])
async def list_models(session: DbSession, _: AdminUser) -> ApiResponse[list[ModelConfigPublic]]:
    return ApiResponse(data=await AiManagementService(session).list_model_configs())


@router.post(
    "/models",
    response_model=ApiResponse[ModelConfigPublic],
    status_code=status.HTTP_201_CREATED,
)
async def create_model(
    payload: ModelConfigCreate, session: DbSession, _: AdminUser
) -> ApiResponse[ModelConfigPublic]:
    return ApiResponse(
        message="模型配置已创建",
        data=await AiManagementService(session).create_model_config(payload),
    )


@router.patch("/models/{config_id}", response_model=ApiResponse[ModelConfigPublic])
async def update_model(
    config_id: int,
    payload: ModelConfigUpdate,
    session: DbSession,
    _: AdminUser,
) -> ApiResponse[ModelConfigPublic]:
    return ApiResponse(
        message="模型配置已更新",
        data=await AiManagementService(session).update_model_config(config_id, payload),
    )


@router.get("/prompts", response_model=ApiResponse[list[PromptTemplatePublic]])
async def list_prompts(
    session: DbSession, _: AdminUser
) -> ApiResponse[list[PromptTemplatePublic]]:
    return ApiResponse(data=await AiManagementService(session).list_prompts())


@router.post(
    "/prompts",
    response_model=ApiResponse[PromptTemplatePublic],
    status_code=status.HTTP_201_CREATED,
)
async def create_prompt(
    payload: PromptTemplateCreate, session: DbSession, _: AdminUser
) -> ApiResponse[PromptTemplatePublic]:
    return ApiResponse(
        message="Prompt 模板已创建",
        data=await AiManagementService(session).create_prompt(payload),
    )


@router.patch("/prompts/{prompt_id}", response_model=ApiResponse[PromptTemplatePublic])
async def update_prompt(
    prompt_id: int,
    payload: PromptTemplateUpdate,
    session: DbSession,
    _: AdminUser,
) -> ApiResponse[PromptTemplatePublic]:
    return ApiResponse(
        message="Prompt 模板已更新",
        data=await AiManagementService(session).update_prompt(prompt_id, payload),
    )


@router.get("/tools", response_model=ApiResponse[list[FunctionToolPublic]])
async def list_tools(
    session: DbSession, _: AdminUser
) -> ApiResponse[list[FunctionToolPublic]]:
    return ApiResponse(data=await AiManagementService(session).list_tools())


@router.post("/tools/seed-builtins", response_model=ApiResponse[list[FunctionToolPublic]])
async def seed_tools(
    session: DbSession, _: AdminUser
) -> ApiResponse[list[FunctionToolPublic]]:
    return ApiResponse(
        message="内置工具已初始化",
        data=await AiManagementService(session).seed_builtin_tools(),
    )


@router.post(
    "/tools",
    response_model=ApiResponse[FunctionToolPublic],
    status_code=status.HTTP_201_CREATED,
)
async def create_tool(
    payload: FunctionToolCreate, session: DbSession, _: AdminUser
) -> ApiResponse[FunctionToolPublic]:
    return ApiResponse(
        message="Function Tool 已创建",
        data=await AiManagementService(session).create_tool(payload),
    )


@router.patch("/tools/{tool_id}", response_model=ApiResponse[FunctionToolPublic])
async def update_tool(
    tool_id: int,
    payload: FunctionToolUpdate,
    session: DbSession,
    _: AdminUser,
) -> ApiResponse[FunctionToolPublic]:
    return ApiResponse(
        message="Function Tool 已更新",
        data=await AiManagementService(session).update_tool(tool_id, payload),
    )


@router.post("/tools/{tool_id}/test", response_model=ApiResponse[ToolExecutionPublic])
async def test_tool(
    tool_id: int,
    payload: ToolExecuteRequest,
    session: DbSession,
    admin: AdminUser,
) -> ApiResponse[ToolExecutionPublic]:
    tool = await AiRepository(session).get_tool(tool_id)
    if tool is None:
        from backend.app.core.exceptions import NotFoundError

        raise NotFoundError("Function Tool 不存在")
    return ApiResponse(
        data=await ToolCenter(session).execute(
            tool, payload.arguments, ToolContext(user_id=admin.id)
        )
    )


@router.get("/tool-logs", response_model=ApiResponse[PageData[ToolCallLogPublic]])
async def list_tool_logs(
    session: DbSession,
    _: AdminUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ApiResponse[PageData[ToolCallLogPublic]]:
    return ApiResponse(
        data=await AiManagementService(session).list_tool_logs(
            page=page, page_size=page_size
        )
    )


@router.get("/runs", response_model=ApiResponse[PageData[AgentRunPublic]])
async def list_runs(
    session: DbSession,
    _: AdminUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ApiResponse[PageData[AgentRunPublic]]:
    return ApiResponse(
        data=await ShoppingAgentService(session).list_admin_runs(
            page=page, page_size=page_size
        )
    )


@router.get("/runs/{run_id}", response_model=ApiResponse[AgentRunPublic])
async def get_run(
    run_id: int, session: DbSession, _: AdminUser
) -> ApiResponse[AgentRunPublic]:
    return ApiResponse(data=await ShoppingAgentService(session).get_admin_run(run_id))
