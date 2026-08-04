import hashlib
import json
import secrets
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

from openai import AsyncOpenAI
from openai.types.responses import FunctionToolParam, ResponseFunctionToolCall
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.crypto import decrypt_secret
from backend.app.core.exceptions import AppError, NotFoundError
from backend.app.models.ai import AgentRun, AgentStep
from backend.app.models.enums import AgentRunStatus, AgentStepType, StepStatus
from backend.app.repositories.ai import AiRepository
from backend.app.schemas.ai import (
    AgentRunPublic,
    AgentStepPublic,
    RecommendationItemPublic,
    RecommendationPublic,
    ShoppingGuideRequest,
)
from backend.app.schemas.common import PageData
from backend.app.services.tool_center import ToolCenter, ToolContext

DEFAULT_GUIDE_PROMPT = """你是商城智能导购。理解用户需求并使用提供的工具查询真实数据。
价格、库存、订单状态和用户数据必须来自工具结果，不得猜测或改写。
把用户说的“预算 N 元”理解为最高可接受价格：搜索时优先使用 max_price=N，min_price 留空；
除非用户明确给出最低价或价格区间。
先提取用户明确提到的商品类型或核心关键词进行搜索，不要先搜索“热门”，也不要在没有请求的情况下改搜无关品类。
若第一次没有结果，只放宽一次关键词或价格限制；不要连续尝试多个无关品类。通常最多进行三次商品搜索。
信息不足时可以继续调用工具；拿到符合条件的商品、SKU、真实价格和库存后，应尽快提交推荐并结束。
不要展示内部推理过程，只说明推荐依据和必要限制。"""
RECOMMENDATION_POLICY = """
如果最终回答包含具体商品推荐，必须先调用 submit_recommendation，只提交商品 ID、SKU ID 和理由。
最终回答中的价格与库存只能引用 submit_recommendation 返回的 verified_price 和 verified_stock。
若候选被后端拒绝，不得继续推荐该候选。"""


class ShoppingAgentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ai = AiRepository(session)

    async def run(self, user_id: int, payload: ShoppingGuideRequest) -> AgentRunPublic:
        config = await self.ai.get_default_model_config()
        if config is None:
            raise AppError("请先在管理端启用一个默认模型配置", code="AI_MODEL_NOT_CONFIGURED")
        settings = get_settings()
        api_key = (
            decrypt_secret(config.api_key_ciphertext)
            if config.api_key_ciphertext
            else settings.ai_api_key
        )
        if not api_key:
            raise AppError("默认模型尚未配置 API Key", code="AI_API_KEY_MISSING")

        prompt = await self.ai.get_scene_prompt("SHOPPING_GUIDE")
        tools = await self.ai.list_tools(enabled_only=True)
        if not tools:
            raise AppError("请先初始化并启用 Function Tools", code="AI_TOOLS_NOT_CONFIGURED")
        tool_params: list[FunctionToolParam] = [
            {
                "type": "function",
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema,
                "strict": True,
            }
            for tool in tools
        ]
        run = AgentRun(
            run_no=f"AR{secrets.token_hex(12).upper()}",
            user_id=user_id,
            model_config_id=config.id,
            request_text=payload.message,
            status=AgentRunStatus.RUNNING,
            max_steps=payload.max_steps,
            started_at=datetime.now(UTC),
        )
        self.ai.add(run)
        await self.session.commit()
        await self.session.refresh(run)

        client = AsyncOpenAI(api_key=api_key, base_url=config.base_url or settings.ai_base_url)
        started = perf_counter()
        previous_response_id: str | None = None
        current_input: Any = payload.message
        step_no = 0
        prompt_tokens = 0
        completion_tokens = 0
        try:
            while step_no < payload.max_steps:
                response = await client.responses.create(
                    model=config.chat_model,
                    instructions=(prompt.system_prompt if prompt else DEFAULT_GUIDE_PROMPT)
                    + RECOMMENDATION_POLICY,
                    input=current_input,
                    previous_response_id=previous_response_id,
                    tools=tool_params,
                    max_output_tokens=config.max_tokens,
                    max_tool_calls=payload.max_steps - step_no,
                    reasoning={"effort": "low"},
                    safety_identifier=self._safety_identifier(user_id),
                )
                if response.usage:
                    prompt_tokens += response.usage.input_tokens
                    completion_tokens += response.usage.output_tokens
                calls = [
                    item
                    for item in response.output
                    if isinstance(item, ResponseFunctionToolCall)
                ]
                if not calls:
                    answer = response.output_text.strip() or "暂时无法生成导购建议。"
                    step_no += 1
                    now = datetime.now(UTC)
                    self.ai.add(
                        AgentStep(
                            agent_run_id=run.id,
                            step_no=step_no,
                            step_type=AgentStepType.FINAL_ANSWER,
                            status=StepStatus.SUCCEEDED,
                            output_json={"answer": answer},
                            started_at=now,
                            finished_at=now,
                            duration_ms=0,
                        )
                    )
                    run.status = AgentRunStatus.SUCCEEDED
                    run.final_answer = answer
                    break

                outputs: list[dict[str, str]] = []
                for call in calls:
                    if step_no >= payload.max_steps:
                        break
                    step_no += 1
                    step_started_at = datetime.now(UTC)
                    try:
                        arguments = json.loads(call.arguments)
                        if not isinstance(arguments, dict):
                            raise ValueError
                    except (json.JSONDecodeError, ValueError):
                        arguments = {}
                    step = AgentStep(
                        agent_run_id=run.id,
                        step_no=step_no,
                        step_type=AgentStepType.TOOL_CALL,
                        status=StepStatus.RUNNING,
                        tool_name=call.name,
                        input_json=arguments,
                        started_at=step_started_at,
                    )
                    self.ai.add(step)
                    await self.session.flush()
                    execution = await ToolCenter(self.session).execute_by_name(
                        call.name,
                        arguments,
                        ToolContext(
                            user_id=user_id,
                            agent_run_id=run.id,
                            agent_step_id=step.id,
                        ),
                    )
                    step.status = execution.status
                    step.output_json = execution.result
                    step.error_message = execution.error_message
                    step.duration_ms = execution.duration_ms
                    step.finished_at = datetime.now(UTC)
                    await self.session.commit()
                    output_payload = {
                        "ok": execution.status == StepStatus.SUCCEEDED,
                        "data": execution.result,
                        "error": execution.error_message,
                    }
                    outputs.append(
                        {
                            "type": "function_call_output",
                            "call_id": call.call_id,
                            "output": json.dumps(output_payload, ensure_ascii=False),
                        }
                    )
                previous_response_id = response.id
                current_input = outputs
            else:
                run.status = AgentRunStatus.MAX_STEPS_REACHED
                run.final_answer = "已达到最大工具调用步数，请缩小需求范围后重试。"
        except Exception as exc:
            run.status = AgentRunStatus.FAILED
            run.error_message = f"模型调用失败：{type(exc).__name__}"
            run.actual_steps = step_no
            run.prompt_tokens = prompt_tokens
            run.completion_tokens = completion_tokens
            run.total_duration_ms = max(0, int((perf_counter() - started) * 1000))
            run.finished_at = datetime.now(UTC)
            await self.session.commit()
            raise AppError("AI 导购暂时不可用，请稍后重试", code="AI_RUN_FAILED") from exc
        finally:
            await client.close()

        run.actual_steps = step_no
        run.prompt_tokens = prompt_tokens
        run.completion_tokens = completion_tokens
        run.total_duration_ms = max(0, int((perf_counter() - started) * 1000))
        run.finished_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(run)
        return await self._run_public(run)

    async def get_run(self, user_id: int, run_id: int) -> AgentRunPublic:
        run = await self.ai.get_agent_run(run_id, user_id=user_id)
        if run is None:
            raise NotFoundError("Agent Run 不存在")
        return await self._run_public(run)

    async def get_admin_run(self, run_id: int) -> AgentRunPublic:
        run = await self.ai.get_agent_run(run_id)
        if run is None:
            raise NotFoundError("Agent Run 不存在")
        return await self._run_public(run)

    async def list_user_runs(
        self, user_id: int, *, page: int, page_size: int
    ) -> PageData[AgentRunPublic]:
        runs, total = await self.ai.list_agent_runs(
            page=page, page_size=page_size, user_id=user_id
        )
        return PageData(
            items=[await self._run_public(run) for run in runs],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def list_admin_runs(
        self, *, page: int, page_size: int
    ) -> PageData[AgentRunPublic]:
        runs, total = await self.ai.list_agent_runs(page=page, page_size=page_size)
        return PageData(
            items=[await self._run_public(run) for run in runs],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def _run_public(self, run: AgentRun) -> AgentRunPublic:
        steps = await self.ai.list_agent_steps(run.id)
        recommendation = await self.ai.get_recommendation(run.id)
        recommendation_public = None
        if recommendation is not None:
            rows = await self.ai.list_recommendation_items(recommendation.id)
            recommendation_public = RecommendationPublic(
                id=recommendation.id,
                summary=recommendation.summary,
                items=[
                    RecommendationItemPublic(
                        product_id=item.product_id,
                        sku_id=item.sku_id,
                        product_name=product.name,
                        sku_name=sku.name if sku else None,
                        main_image_url=product.main_image_url,
                        reason=item.reason,
                        price_snapshot=item.price_snapshot,
                        stock_snapshot=item.stock_snapshot,
                        validation_passed=item.validation_passed,
                    )
                    for item, product, sku in rows
                ],
            )
        return AgentRunPublic(
            id=run.id,
            run_no=run.run_no,
            status=run.status,
            request_text=run.request_text,
            final_answer=run.final_answer,
            error_message=run.error_message,
            actual_steps=run.actual_steps,
            max_steps=run.max_steps,
            total_duration_ms=run.total_duration_ms,
            started_at=run.started_at,
            finished_at=run.finished_at,
            steps=[AgentStepPublic.model_validate(step) for step in steps],
            recommendation=recommendation_public,
        )

    @staticmethod
    def _safety_identifier(user_id: int) -> str:
        secret = get_settings().secret_key
        return hashlib.sha256(f"{secret}:{user_id}".encode()).hexdigest()[:32]
