from collections.abc import Mapping
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.crypto import encrypt_secret
from backend.app.core.exceptions import ConflictError, NotFoundError
from backend.app.models.ai import AiModelConfig, FunctionTool, PromptTemplate
from backend.app.repositories.ai import AiRepository
from backend.app.schemas.ai import (
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
)
from backend.app.schemas.common import PageData


def _apply_changes(entity: object, changes: Mapping[str, Any]) -> None:
    for field, value in changes.items():
        setattr(entity, field, value)


def _model_public(config: AiModelConfig) -> ModelConfigPublic:
    values = ModelConfigPublic.model_validate(
        {**config.__dict__, "has_api_key": bool(config.api_key_ciphertext)}
    )
    return values


BUILTIN_TOOLS = [
    FunctionToolCreate(
        name="search_products",
        display_name="搜索在售商品",
        description="按关键词和价格范围搜索真实在售商品，返回商品 ID、价格、评分和销量。",
        executor="catalog.search_products",
        input_schema={
            "type": "object",
            "properties": {
                "keyword": {"type": ["string", "null"], "description": "商品关键词"},
                "min_price": {"type": ["number", "null"], "minimum": 0},
                "max_price": {"type": ["number", "null"], "minimum": 0},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20},
            },
            "required": ["keyword", "min_price", "max_price", "limit"],
            "additionalProperties": False,
        },
    ),
    FunctionToolCreate(
        name="get_product_price_stock",
        display_name="查询商品价格库存",
        description="按商品 ID 查询所有可售 SKU 的实时价格与可售库存。",
        executor="catalog.get_product_price_stock",
        input_schema={
            "type": "object",
            "properties": {"product_id": {"type": "integer", "minimum": 1}},
            "required": ["product_id"],
            "additionalProperties": False,
        },
    ),
    FunctionToolCreate(
        name="get_my_order_status",
        display_name="查询我的订单状态",
        description="按订单号查询当前登录用户自己的订单状态与关键时间。",
        executor="orders.get_user_order_status",
        input_schema={
            "type": "object",
            "properties": {"order_no": {"type": "string", "minLength": 1}},
            "required": ["order_no"],
            "additionalProperties": False,
        },
    ),
    FunctionToolCreate(
        name="get_user_summary",
        display_name="查询用户消费概况",
        description="读取当前用户钱包余额和各状态订单数量，不返回敏感身份信息。",
        executor="profile.get_user_summary",
        input_schema={
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    ),
    FunctionToolCreate(
        name="submit_recommendation",
        display_name="提交推荐结果",
        description=(
            "提交准备推荐的商品 ID、可选 SKU ID 与推荐理由。后端会重新校验商品状态、"
            "SKU 归属、真实价格和可售库存，只保存通过校验的推荐。"
        ),
        executor="recommendations.submit",
        input_schema={
            "type": "object",
            "properties": {
                "summary": {"type": "string", "minLength": 2, "maxLength": 2000},
                "items": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 5,
                    "items": {
                        "type": "object",
                        "properties": {
                            "product_id": {"type": "integer", "minimum": 1},
                            "sku_id": {"type": ["integer", "null"], "minimum": 1},
                            "reason": {
                                "type": "string",
                                "minLength": 2,
                                "maxLength": 1000,
                            },
                        },
                        "required": ["product_id", "sku_id", "reason"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["summary", "items"],
            "additionalProperties": False,
        },
    ),
]


class AiManagementService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ai = AiRepository(session)

    async def list_model_configs(self) -> list[ModelConfigPublic]:
        return [_model_public(item) for item in await self.ai.list_model_configs()]

    async def create_model_config(self, payload: ModelConfigCreate) -> ModelConfigPublic:
        if await self.ai.model_name_exists(payload.name):
            raise ConflictError("模型配置名称已存在")
        values = payload.model_dump(exclude={"api_key"})
        if payload.is_default:
            await self.ai.clear_default_model_configs()
        config = AiModelConfig(
            **values,
            api_key_ciphertext=encrypt_secret(payload.api_key) if payload.api_key else None,
        )
        self.ai.add(config)
        await self.session.commit()
        await self.session.refresh(config)
        return _model_public(config)

    async def update_model_config(
        self, config_id: int, payload: ModelConfigUpdate
    ) -> ModelConfigPublic:
        config = await self.ai.get_model_config(config_id)
        if config is None:
            raise NotFoundError("模型配置不存在")
        changes = payload.model_dump(exclude_unset=True, exclude={"api_key"})
        if changes.get("name") and await self.ai.model_name_exists(
            changes["name"], exclude_id=config_id
        ):
            raise ConflictError("模型配置名称已存在")
        if changes.get("is_default"):
            await self.ai.clear_default_model_configs(exclude_id=config_id)
        if payload.api_key:
            config.api_key_ciphertext = encrypt_secret(payload.api_key)
        _apply_changes(config, changes)
        await self.session.commit()
        await self.session.refresh(config)
        return _model_public(config)

    async def list_prompts(self) -> list[PromptTemplatePublic]:
        return [PromptTemplatePublic.model_validate(item) for item in await self.ai.list_prompts()]

    async def create_prompt(self, payload: PromptTemplateCreate) -> PromptTemplatePublic:
        if await self.ai.prompt_version_exists(payload.code, payload.version):
            raise ConflictError("Prompt 编码与版本已存在")
        prompt = PromptTemplate(**payload.model_dump())
        self.ai.add(prompt)
        await self.session.commit()
        await self.session.refresh(prompt)
        return PromptTemplatePublic.model_validate(prompt)

    async def update_prompt(
        self, prompt_id: int, payload: PromptTemplateUpdate
    ) -> PromptTemplatePublic:
        prompt = await self.ai.get_prompt(prompt_id)
        if prompt is None:
            raise NotFoundError("Prompt 模板不存在")
        _apply_changes(prompt, payload.model_dump(exclude_unset=True))
        await self.session.commit()
        await self.session.refresh(prompt)
        return PromptTemplatePublic.model_validate(prompt)

    async def list_tools(self) -> list[FunctionToolPublic]:
        return [FunctionToolPublic.model_validate(item) for item in await self.ai.list_tools()]

    async def create_tool(self, payload: FunctionToolCreate) -> FunctionToolPublic:
        if await self.ai.get_tool_by_name(payload.name):
            raise ConflictError("工具名称已存在")
        tool = FunctionTool(**payload.model_dump())
        self.ai.add(tool)
        await self.session.commit()
        await self.session.refresh(tool)
        return FunctionToolPublic.model_validate(tool)

    async def update_tool(
        self, tool_id: int, payload: FunctionToolUpdate
    ) -> FunctionToolPublic:
        tool = await self.ai.get_tool(tool_id)
        if tool is None:
            raise NotFoundError("Function Tool 不存在")
        changes = payload.model_dump(exclude_unset=True)
        if "input_schema" in changes:
            FunctionToolCreate(
                name=tool.name,
                display_name=changes.get("display_name", tool.display_name),
                description=changes.get("description", tool.description),
                input_schema=changes["input_schema"],
                executor=changes.get("executor", tool.executor),
                timeout_seconds=changes.get("timeout_seconds", tool.timeout_seconds),
                enabled=changes.get("enabled", tool.enabled),
            )
        _apply_changes(tool, changes)
        await self.session.commit()
        await self.session.refresh(tool)
        return FunctionToolPublic.model_validate(tool)

    async def seed_builtin_tools(self) -> list[FunctionToolPublic]:
        for payload in BUILTIN_TOOLS:
            existing = await self.ai.get_tool_by_name(payload.name)
            if existing is None:
                self.ai.add(FunctionTool(**payload.model_dump()))
        await self.session.commit()
        return await self.list_tools()

    async def list_tool_logs(
        self, *, page: int, page_size: int
    ) -> PageData[ToolCallLogPublic]:
        rows, total = await self.ai.list_tool_logs(page=page, page_size=page_size)
        items = [
            ToolCallLogPublic(
                id=log.id,
                call_no=log.call_no,
                tool_id=log.tool_id,
                tool_name=tool.name,
                user_id=log.user_id,
                arguments_json=log.arguments_json,
                result_json=log.result_json,
                status=log.status,
                error_message=log.error_message,
                duration_ms=log.duration_ms,
                created_at=log.created_at,
            )
            for log, tool in rows
        ]
        return PageData(items=items, page=page, page_size=page_size, total=total)
