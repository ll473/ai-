import asyncio
import json
from typing import Any, Protocol

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.crypto import decrypt_secret
from backend.app.core.exceptions import AppError
from backend.app.repositories.ai import AiRepository
from backend.app.schemas.ai import ProductComparisonAiResult, ProductComparisonRequest
from backend.app.services.catalog import CatalogService


class ProductComparisonGateway(Protocol):
    async def compare(
        self, facts: list[dict[str, Any]], preference: str | None
    ) -> ProductComparisonAiResult: ...

    async def close(self) -> None: ...


class BailianProductComparisonGateway:
    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        base_url: str | None = None,
        client: Any | None = None,
    ) -> None:
        settings = get_settings()
        self.model = model
        self.client = client or AsyncOpenAI(
            api_key=api_key, base_url=base_url or settings.ai_base_url
        )

    async def compare(
        self, facts: list[dict[str, Any]], preference: str | None
    ) -> ProductComparisonAiResult:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是商城商品对比助手。仅依据服务端提供的商品事实给出选择建议，"
                            "不得编造价格、库存、促销或未提供的参数。"
                            "必须只输出 JSON 对象，字段为 recommended_product_id、summary、"
                            "items、considerations；items 每项仅包含 product_id、strengths、"
                            "weaknesses、suitable_for。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {"facts": facts, "preference": preference}, ensure_ascii=False
                        ),
                    },
                ],
                response_format={"type": "json_object"},
                extra_body={"enable_thinking": False},
                temperature=0.2,
                max_tokens=800,
            )
        except (APIConnectionError, APITimeoutError, APIStatusError) as exc:
            raise AppError(
                "AI 对比服务暂时不可用，请稍后重试",
                code="AI_MODEL_UNAVAILABLE",
                status_code=503,
            ) from exc
        try:
            content = response.choices[0].message.content
            if not content or not content.strip():
                raise ValueError("empty model response")
            return ProductComparisonAiResult.model_validate_json(content)
        except (AttributeError, IndexError, TypeError, ValueError) as exc:
            raise AppError(
                "AI 对比分析结果格式无效",
                code="AI_INVALID_RESPONSE",
                status_code=502,
            ) from exc

    async def close(self) -> None:
        await self.client.close()


class ProductComparisonAiService:
    def __init__(
        self,
        session: AsyncSession,
        gateway: ProductComparisonGateway | None = None,
        *,
        timeout_seconds: float = 20,
    ) -> None:
        self.session = session
        self.ai = AiRepository(session)
        self.gateway = gateway
        self.timeout_seconds = timeout_seconds

    async def compare(self, payload: ProductComparisonRequest) -> ProductComparisonAiResult:
        facts_result = await CatalogService(self.session).compare_products(payload.product_ids)
        if facts_result.unavailable_ids or len(facts_result.items) != len(payload.product_ids):
            raise AppError(
                "所选商品已下架或不可用，请更新对比清单后重试",
                code="COMPARISON_PRODUCT_UNAVAILABLE",
                status_code=422,
                details={"unavailable_ids": facts_result.unavailable_ids},
            )
        facts = [self._compact_fact(item.model_dump(mode="json")) for item in facts_result.items]
        gateway = await self._resolve_gateway()
        try:
            try:
                async with asyncio.timeout(self.timeout_seconds):
                    result = await gateway.compare(facts, payload.preference)
            except TimeoutError as exc:
                raise AppError(
                    "AI 对比分析超时，请稍后重试",
                    code="AI_COMPARISON_TIMEOUT",
                    status_code=504,
                ) from exc
            self._validate_result(result, {item["product_id"] for item in facts})
            return result
        finally:
            if self.gateway is None:
                await gateway.close()

    async def _resolve_gateway(self) -> ProductComparisonGateway:
        if self.gateway is not None:
            return self.gateway
        config = await self.ai.get_default_model_config()
        if config is None:
            raise AppError(
                "当前没有可用的默认 AI 模型配置",
                code="AI_MODEL_UNAVAILABLE",
                status_code=503,
            )
        settings = get_settings()
        api_key = (
            decrypt_secret(config.api_key_ciphertext)
            if config.api_key_ciphertext
            else settings.ai_api_key
        )
        if not api_key:
            raise AppError(
                "默认 AI 模型尚未配置 API Key",
                code="AI_MODEL_UNAVAILABLE",
                status_code=503,
            )
        return BailianProductComparisonGateway(
            model=config.chat_model,
            api_key=api_key,
            base_url=config.base_url,
        )

    @staticmethod
    def _compact_fact(item: dict[str, Any]) -> dict[str, Any]:
        parameters = item.get("parameters")
        normalized_parameters = (
            {str(key)[:80]: str(value)[:300] for key, value in parameters.items()}
            if isinstance(parameters, dict)
            else {}
        )
        return {
            "product_id": item["id"],
            "name": item["name"],
            "subtitle": item.get("subtitle"),
            "category": item["category_name"],
            "brand": item.get("brand_name"),
            "parameters": normalized_parameters,
            "rating": item.get("rating"),
            "review_count": item.get("review_count"),
            "sales_count": item.get("sales_count"),
            "sku_names": [sku["name"] for sku in item.get("skus", [])],
        }

    @staticmethod
    def _validate_result(result: ProductComparisonAiResult, candidate_ids: set[int]) -> None:
        item_ids = [item.product_id for item in result.items]
        if (
            result.recommended_product_id not in candidate_ids
            or any(item_id not in candidate_ids for item_id in item_ids)
            or len(item_ids) != len(set(item_ids))
        ):
            raise AppError(
                "AI 对比分析结果包含无效商品",
                code="AI_INVALID_RESPONSE",
                status_code=502,
            )
