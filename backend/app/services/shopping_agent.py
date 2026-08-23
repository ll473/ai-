import hashlib
import json
import logging
import re
import secrets
from datetime import UTC, datetime, timedelta
from time import perf_counter
from typing import Any, cast

from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    InternalServerError,
    RateLimitError,
)
from openai.types.responses import FunctionToolParam, ResponseFunctionToolCall
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.crypto import decrypt_secret
from backend.app.core.exceptions import AppError, NotFoundError
from backend.app.models.ai import AgentRun, AgentStep, Conversation, ConversationMessage
from backend.app.models.enums import (
    AgentRunStatus,
    AgentStepType,
    ConversationRole,
    StepStatus,
)
from backend.app.repositories.ai import AiRepository
from backend.app.schemas.ai import (
    AgentRunAdminPublic,
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
一旦商品搜索返回符合条件的候选，不要继续换关键词搜索；应查询候选的价格库存并提交推荐。
不要展示内部推理过程，只说明推荐依据和必要限制。"""
RECOMMENDATION_POLICY = """
如果最终回答包含具体商品推荐，必须先调用 submit_recommendation，只提交商品 ID、SKU ID 和理由。
最终回答中的价格与库存只能引用 submit_recommendation 返回的 verified_price 和 verified_stock。
若候选被后端拒绝，不得继续推荐该候选。"""

TRANSIENT_MODEL_ERRORS = (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)

logger = logging.getLogger("uvicorn.error.shopping_agent")


class ShoppingAgentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ai = AiRepository(session)

    async def run(self, user_id: int, payload: ShoppingGuideRequest) -> AgentRunPublic:
        settings = get_settings()
        recent_runs = await self.ai.count_user_runs_since(
            user_id, datetime.now(UTC) - timedelta(hours=1)
        )
        if recent_runs >= settings.ai_max_runs_per_hour:
            raise AppError(
                "智能导购请求过于频繁，请稍后再试",
                code="AI_RATE_LIMITED",
                status_code=429,
            )
        config = await self.ai.get_default_model_config()
        if config is None:
            raise AppError("请先在管理端启用一个默认模型配置", code="AI_MODEL_NOT_CONFIGURED")
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
        conversation, prior_messages = await self._conversation_context(user_id, payload)
        now = datetime.now(UTC)
        user_message = ConversationMessage(
            conversation_id=conversation.id,
            role=ConversationRole.USER,
            content=payload.message,
        )
        conversation.last_message_at = now
        self.ai.add(user_message)
        run = AgentRun(
            run_no=f"AR{secrets.token_hex(12).upper()}",
            user_id=user_id,
            conversation_id=conversation.id,
            model_config_id=config.id,
            request_text=payload.message,
            status=AgentRunStatus.RUNNING,
            max_steps=payload.max_steps,
            started_at=datetime.now(UTC),
        )
        self.ai.add(run)
        await self.session.commit()
        await self.session.refresh(run)

        client = AsyncOpenAI(
            api_key=api_key,
            base_url=config.base_url or settings.ai_base_url,
            default_headers={"x-dashscope-session-cache": "enable"},
        )
        started = perf_counter()
        previous_response_id: str | None = None
        current_input: Any = self._conversation_prompt(prior_messages, payload.message)
        model_call_no = 0
        step_no = 0
        prompt_tokens = 0
        completion_tokens = 0
        search_calls = 0
        product_search_attempted = False
        product_search_found = False
        discovered_products: dict[int, dict[str, Any]] = {}
        search_enabled = True
        recommendation_submitted = False
        shopping_model = settings.ai_shopping_model
        try:
            while step_no < payload.max_steps:
                if (
                    step_no >= payload.max_steps - 1
                    and discovered_products
                    and not recommendation_submitted
                ):
                    run.final_answer, step_no = await self._submit_discovered_recommendation(
                        run=run,
                        user_id=user_id,
                        request_text=payload.message,
                        items=list(discovered_products.values()),
                        step_no=step_no,
                    )
                    run.status = AgentRunStatus.SUCCEEDED
                    recommendation_submitted = True
                    break
                available_tools = [
                    tool
                    for tool in tool_params
                    if search_enabled or tool["name"] != "search_products"
                ]
                model_call_no += 1
                model_call_started = perf_counter()
                model_used = shopping_model
                request_options: dict[str, Any] = {
                    "instructions": (
                        prompt.system_prompt if prompt else DEFAULT_GUIDE_PROMPT
                    )
                    + RECOMMENDATION_POLICY,
                    "input": current_input,
                    "previous_response_id": previous_response_id,
                    "tools": available_tools,
                    "max_output_tokens": config.max_tokens,
                    # Keep one model turn to one deterministic tool action. Allowing
                    # the whole remaining budget here lets the model issue several
                    # parallel searches and exhaust max_steps before it can submit.
                    "max_tool_calls": 1,
                    "reasoning": {"effort": "none"},
                    "safety_identifier": self._safety_identifier(user_id),
                }
                try:
                    response = await client.responses.create(
                        model=model_used, **request_options
                    )
                except TRANSIENT_MODEL_ERRORS:
                    if model_used == config.chat_model:
                        raise
                    model_used = config.chat_model
                    logger.warning(
                        "shopping_agent_model_fallback agent_run_id=%s "
                        "model_call_no=%s primary_model=%s fallback_model=%s",
                        run.id,
                        model_call_no,
                        shopping_model,
                        model_used,
                    )
                    response = await client.responses.create(
                        model=model_used, **request_options
                    )
                model_call_duration_ms = max(
                    0, int((perf_counter() - model_call_started) * 1000)
                )
                if response.usage:
                    prompt_tokens += response.usage.input_tokens
                    completion_tokens += response.usage.output_tokens
                calls = [
                    item
                    for item in response.output
                    if isinstance(item, ResponseFunctionToolCall)
                ]
                input_details = (
                    getattr(response.usage, "input_tokens_details", None)
                    if response.usage
                    else None
                )
                output_details = (
                    getattr(response.usage, "output_tokens_details", None)
                    if response.usage
                    else None
                )
                model_metrics = {
                    "agent_run_id": run.id,
                    "model_call_no": model_call_no,
                    "model": model_used,
                    "reasoning_effort": "none",
                    "duration_ms": model_call_duration_ms,
                    "input_tokens": response.usage.input_tokens if response.usage else 0,
                    "output_tokens": response.usage.output_tokens if response.usage else 0,
                    "cached_tokens": getattr(input_details, "cached_tokens", 0) or 0,
                    "reasoning_tokens": getattr(output_details, "reasoning_tokens", 0) or 0,
                    "tool_call_count": len(calls),
                    "response_id": response.id,
                    "request_id": getattr(response, "_request_id", None),
                }
                logger.info(
                    "shopping_agent_model_call %s",
                    " ".join(f"{key}={value}" for key, value in model_metrics.items()),
                    extra=model_metrics,
                )
                if calls and all(
                    call.name == "search_products" and not search_enabled for call in calls
                ):
                    run.status = AgentRunStatus.SUCCEEDED
                    run.final_answer = (
                        "当前在售商品中暂未找到符合该需求的商品。"
                        "你可以换一个更具体的商品类型或用途后再试。"
                    )
                    break
                if not calls:
                    if (
                        not recommendation_submitted
                        and (not product_search_attempted or not product_search_found)
                        and self._is_purchase_request(payload.message)
                    ):
                        run.final_answer, step_no = await self._fallback_recommendation(
                            run=run,
                            user_id=user_id,
                            request_text=payload.message,
                            step_no=step_no,
                            model_unavailable=False,
                        )
                        run.status = AgentRunStatus.SUCCEEDED
                        break
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
                catalog_fallback_required = False
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
                    if call.name == "search_products":
                        product_search_attempted = True
                        search_calls += 1
                        result_count = int((execution.result or {}).get("count", 0))
                        product_search_found = product_search_found or result_count > 0
                        for item in (execution.result or {}).get("items", []):
                            product_id = int(item.get("product_id") or 0)
                            if product_id > 0:
                                discovered_products[product_id] = item
                        if result_count > 0 or search_calls >= 3:
                            search_enabled = False
                        if search_calls >= 3 and not product_search_found:
                            catalog_fallback_required = True
                            break
                    if (
                        call.name == "submit_recommendation"
                        and execution.status == StepStatus.SUCCEEDED
                        and execution.result
                    ):
                        run.status = AgentRunStatus.SUCCEEDED
                        run.final_answer = self._recommendation_answer(execution.result)
                        recommendation_submitted = True
                        break
                if catalog_fallback_required:
                    run.final_answer, step_no = await self._fallback_recommendation(
                        run=run,
                        user_id=user_id,
                        request_text=payload.message,
                        step_no=step_no,
                        model_unavailable=False,
                    )
                    run.status = AgentRunStatus.SUCCEEDED
                    break
                if recommendation_submitted:
                    break
                previous_response_id = response.id
                current_input = outputs
            else:
                run.status = AgentRunStatus.MAX_STEPS_REACHED
                run.final_answer = "已达到最大工具调用步数，请缩小需求范围后重试。"
        except TRANSIENT_MODEL_ERRORS:
            run.final_answer, step_no = await self._fallback_recommendation(
                run=run,
                user_id=user_id,
                request_text=payload.message,
                step_no=step_no,
                model_unavailable=True,
            )
            run.status = AgentRunStatus.SUCCEEDED
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
        if run.final_answer:
            self.ai.add(
                ConversationMessage(
                    conversation_id=conversation.id,
                    role=ConversationRole.ASSISTANT,
                    content=run.final_answer,
                )
            )
            conversation.last_message_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(run)
        return await self._run_public(run, include_steps=False)

    async def _submit_discovered_recommendation(
        self,
        *,
        run: AgentRun,
        user_id: int,
        request_text: str,
        items: list[dict[str, Any]],
        step_no: int,
    ) -> tuple[str, int]:
        budget = self._extract_budget(request_text)
        candidates = self._rank_fallback_candidates(request_text, items)[:3]
        submit, step_no = await self._execute_fallback_tool(
            run,
            user_id,
            step_no + 1,
            "submit_recommendation",
            {
                "summary": "已根据预算、使用场景和商城实时数据整理推荐。",
                "items": [
                    {
                        "product_id": int(item["product_id"]),
                        "sku_id": None,
                        "reason": self._fallback_reason(request_text, item, budget),
                    }
                    for item in candidates
                ],
            },
        )
        if submit.status != StepStatus.SUCCEEDED or not submit.result:
            return "候选商品校验未通过，请调整需求后重试。", step_no
        return self._recommendation_answer(submit.result), step_no

    async def _fallback_recommendation(
        self,
        *,
        run: AgentRun,
        user_id: int,
        request_text: str,
        step_no: int,
        model_unavailable: bool,
    ) -> tuple[str, int]:
        """Build a verified recommendation after model or search fallback."""
        budget = self._extract_budget(request_text)
        search_args: dict[str, Any] = {
            "keyword": self._extract_product_keyword(request_text),
            "min_price": None,
            "max_price": budget,
            "limit": 10,
        }
        search, step_no = await self._execute_fallback_tool(
            run, user_id, step_no + 1, "search_products", search_args
        )
        items = list((search.result or {}).get("items", [])) if search.result else []
        if not items and search_args["keyword"]:
            search_args["keyword"] = None
            search, step_no = await self._execute_fallback_tool(
                run, user_id, step_no + 1, "search_products", search_args
            )
            items = list((search.result or {}).get("items", [])) if search.result else []
        ranked_candidates = self._rank_fallback_candidates(request_text, items)
        strong_candidates = [
            item
            for item in ranked_candidates
            if self._fallback_relevance_score(request_text, item) >= 2
        ]
        weak_candidates = [
            item
            for item in ranked_candidates
            if self._fallback_relevance_score(request_text, item) == 1
        ]
        weak_relevance = not strong_candidates
        candidates = (strong_candidates or weak_candidates or ranked_candidates)[:3]
        if not candidates:
            clarification = (
                "请补充父母的年龄、兴趣或具体使用场景后再试。"
                if "父母" in request_text
                else "请补充使用人群、具体用途、偏好或商品类型后再试。"
            )
            prefix = "外部 AI 服务暂时无法连接；" if model_unavailable else ""
            return f"{prefix}当前商城暂未找到与需求明确匹配的在售商品。{clarification}", step_no
        if weak_relevance:
            prefix = "外部 AI 服务暂时不可用；" if model_unavailable else ""
            summary = (
                f"{prefix}当前商城暂无高度匹配的商品，以下为相关性较弱的备选推荐，"
                "请结合实际需求判断。价格与库存均已实时校验。"
            )
        else:
            summary = (
                "外部 AI 服务暂时不可用，已根据预算、用途和商城实时数据生成基础推荐。"
                if model_unavailable
                else "已从商城在售商品中找到与需求明确相关的基础推荐，价格与库存均已实时校验。"
            )
        submit, step_no = await self._execute_fallback_tool(
            run,
            user_id,
            step_no + 1,
            "submit_recommendation",
            {
                "summary": summary,
                "items": [
                    {
                        "product_id": int(item["product_id"]),
                        "sku_id": None,
                        "reason": self._fallback_reason(
                            request_text,
                            item,
                            budget,
                            weak_relevance=weak_relevance,
                        ),
                    }
                    for item in candidates
                ],
            },
        )
        if submit.status != StepStatus.SUCCEEDED or not submit.result:
            return "外部 AI 服务暂时无法连接，基础推荐校验未通过，请稍后重试。", step_no
        return self._recommendation_answer(submit.result), step_no

    async def _execute_fallback_tool(
        self,
        run: AgentRun,
        user_id: int,
        step_no: int,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> tuple[Any, int]:
        started_at = datetime.now(UTC)
        step = AgentStep(
            agent_run_id=run.id,
            step_no=step_no,
            step_type=AgentStepType.TOOL_CALL,
            status=StepStatus.RUNNING,
            tool_name=tool_name,
            input_json=arguments,
            started_at=started_at,
        )
        self.ai.add(step)
        await self.session.flush()
        execution = await ToolCenter(self.session).execute_by_name(
            tool_name,
            arguments,
            ToolContext(user_id=user_id, agent_run_id=run.id, agent_step_id=step.id),
        )
        step.status = execution.status
        step.output_json = execution.result
        step.error_message = execution.error_message
        step.duration_ms = execution.duration_ms
        step.finished_at = datetime.now(UTC)
        await self.session.commit()
        return execution, step_no

    @staticmethod
    def _extract_budget(request_text: str) -> float | None:
        match = re.search(
            r"(?:预算|不超过|最多|以内)\s*[¥￥]?\s*(\d+(?:\.\d+)?)", request_text
        )
        if not match:
            match = re.search(r"(\d+(?:\.\d+)?)\s*元", request_text)
        return float(match.group(1)) if match else None

    @staticmethod
    def _is_purchase_request(request_text: str) -> bool:
        return any(
            signal in request_text
            for signal in ("买", "购买", "推荐", "挑", "选购", "预算", "适合")
        )

    @staticmethod
    def _extract_product_keyword(request_text: str) -> str | None:
        for keyword in ("办公椅", "椅子", "键盘", "耳机", "咖啡", "电脑", "手机", "手表"):
            if keyword in request_text:
                return "椅" if keyword in {"办公椅", "椅子"} else keyword
        return None

    @staticmethod
    def _fallback_relevance_score(request_text: str, item: dict[str, Any]) -> int:
        text = f"{item.get('name', '')} {item.get('subtitle', '')}"
        exact_signals = (
            "办公",
            "久坐",
            "通勤",
            "降噪",
            "游戏",
            "学习",
            "生活",
            "礼物",
            "键盘",
            "耳机",
            "椅",
            "咖啡",
            "电脑",
            "手机",
            "手表",
        )
        aliases = {
            "礼物": ("礼盒", "礼品"),
            "父母": ("老人", "长辈"),
            "操作简单": ("易用", "简便", "一键", "大字"),
            "轻便": ("轻量", "便携"),
            "耐用": ("耐磨", "坚固"),
        }
        exact_score = sum(
            2 for signal in exact_signals if signal in request_text and signal in text
        )
        alias_score = sum(
            1
            for signal, related_words in aliases.items()
            if signal in request_text and any(word in text for word in related_words)
        )
        return exact_score + alias_score

    @staticmethod
    def _rank_fallback_candidates(
        request_text: str, items: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        def score(item: dict[str, Any]) -> tuple[int, float, int]:
            return (
                ShoppingAgentService._fallback_relevance_score(request_text, item),
                float(item.get("rating") or 0),
                int(item.get("sales_count") or 0),
            )

        return sorted(items, key=score, reverse=True)

    @staticmethod
    def _fallback_reason(
        request_text: str,
        item: dict[str, Any],
        budget: float | None,
        *,
        weak_relevance: bool = False,
    ) -> str:
        reasons = []
        if weak_relevance:
            reasons.append("与部分需求缺少明确匹配，仅作为低相关性备选")
        item_text = f"{item.get('name', '')} {item.get('subtitle', '')}"
        if "礼物" in request_text and any(word in item_text for word in ("礼盒", "礼品")):
            reasons.append("商品为礼盒形式，可作为礼物备选")
        if "办公" in request_text and "办公" in str(item.get("subtitle") or ""):
            reasons.append("商品说明明确适用于办公场景")
        if budget is not None:
            reasons.append(f"最低售价不超过你的 {budget:g} 元预算")
        reasons.append("当前在售，价格与库存由系统实时校验")
        return "；".join(reasons)

    async def get_run(self, user_id: int, run_id: int) -> AgentRunPublic:
        run = await self.ai.get_agent_run(run_id, user_id=user_id)
        if run is None:
            raise NotFoundError("Agent Run 不存在")
        return await self._run_public(run, include_steps=False)

    async def get_admin_run(self, run_id: int) -> AgentRunAdminPublic:
        run = await self.ai.get_agent_run(run_id)
        if run is None:
            raise NotFoundError("Agent Run 不存在")
        return cast(AgentRunAdminPublic, await self._run_public(run, include_steps=True))

    async def list_user_runs(
        self, user_id: int, *, page: int, page_size: int
    ) -> PageData[AgentRunPublic]:
        runs, total = await self.ai.list_agent_runs(
            page=page, page_size=page_size, user_id=user_id
        )
        return PageData(
            items=[await self._run_public(run, include_steps=False) for run in runs],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def list_admin_runs(
        self, *, page: int, page_size: int
    ) -> PageData[AgentRunAdminPublic]:
        runs, total = await self.ai.list_agent_runs(page=page, page_size=page_size)
        return PageData(
            items=[
                cast(AgentRunAdminPublic, await self._run_public(run, include_steps=True))
                for run in runs
            ],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def _run_public(
        self, run: AgentRun, *, include_steps: bool
    ) -> AgentRunPublic | AgentRunAdminPublic:
        steps = await self.ai.list_agent_steps(run.id) if include_steps else []
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
        public_values = dict(
            id=run.id,
            run_no=run.run_no,
            conversation_id=run.conversation_id,
            status=run.status,
            request_text=run.request_text,
            final_answer=run.final_answer,
            error_message=run.error_message,
            actual_steps=run.actual_steps,
            max_steps=run.max_steps,
            total_duration_ms=run.total_duration_ms,
            started_at=run.started_at,
            finished_at=run.finished_at,
            recommendation=recommendation_public,
        )
        if include_steps:
            return AgentRunAdminPublic(
                **public_values,
                steps=[AgentStepPublic.model_validate(step) for step in steps],
            )
        return AgentRunPublic(**public_values)

    async def _conversation_context(
        self, user_id: int, payload: ShoppingGuideRequest
    ) -> tuple[Conversation, list[ConversationMessage]]:
        if payload.conversation_id is not None:
            conversation = await self.ai.get_conversation(
                payload.conversation_id, user_id=user_id
            )
            if conversation is None or conversation.scene != "SHOPPING_GUIDE":
                raise NotFoundError("导购会话不存在")
            return conversation, await self.ai.list_conversation_messages(
                conversation.id, limit=12
            )
        conversation = Conversation(
            user_id=user_id,
            scene="SHOPPING_GUIDE",
            title=payload.message[:40],
            last_message_at=datetime.now(UTC),
        )
        self.ai.add(conversation)
        await self.session.flush()
        return conversation, []

    @staticmethod
    def _conversation_prompt(
        prior_messages: list[ConversationMessage], current_message: str
    ) -> str:
        if not prior_messages:
            return current_message
        history = "\n".join(
            f"{'用户' if item.role == ConversationRole.USER else '助手'}：{item.content}"
            for item in prior_messages
            if item.role in {ConversationRole.USER, ConversationRole.ASSISTANT}
        )
        return f"以下是同一导购会话的近期上下文：\n{history}\n\n用户本轮需求：{current_message}"

    @staticmethod
    def _safety_identifier(user_id: int) -> str:
        secret = get_settings().secret_key
        return hashlib.sha256(f"{secret}:{user_id}".encode()).hexdigest()[:32]

    @staticmethod
    def _recommendation_answer(result: dict[str, Any]) -> str:
        summary = str(result.get("summary") or "已根据你的需求整理出推荐商品。")
        items = result.get("accepted_items") or []
        lines = [summary]
        for index, item in enumerate(items, start=1):
            promotion = item.get("promotion") or {}
            promotion_text = (
                f"，当前优惠 {promotion.get('name')}"
                f"（预计优惠 ¥{promotion.get('discount_amount')}）"
                if promotion
                else ""
            )
            lines.append(
                f"{index}. {item.get('product_name')} / {item.get('sku_name')}："
                f"¥{item.get('verified_price')}，可售库存 {item.get('verified_stock')} 件"
                f"{promotion_text}。{item.get('reason')}"
            )
        return "\n".join(lines)
