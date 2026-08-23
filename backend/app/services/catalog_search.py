import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from difflib import SequenceMatcher
from math import log1p

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.crypto import decrypt_secret
from backend.app.core.exceptions import AppError, NotFoundError
from backend.app.models.catalog import Product, SearchEvent
from backend.app.models.enums import ProductStatus
from backend.app.repositories.ai import AiRepository
from backend.app.repositories.catalog import CatalogRepository
from backend.app.schemas.catalog import (
    CatalogSearchResult,
    ProductSummary,
    SearchEventRequest,
    SearchFacetItem,
    SearchFacets,
    SearchSuggestion,
)
from backend.app.services.knowledge import (
    BailianEmbeddingGateway,
    EmbeddingGateway,
    QdrantKnowledgeGateway,
    VectorGateway,
)

SemanticSearch = Callable[[str, int], Awaitable[Sequence[int]]]
logger = logging.getLogger(__name__)

SEARCH_SYNONYMS: dict[str, tuple[str, ...]] = {
    "父母": ("长辈", "老人"),
    "礼物": ("礼盒", "礼品"),
    "办公": ("办公室", "工作"),
    "耳机": ("降噪", "蓝牙"),
}


def expand_search_terms(query: str) -> tuple[str, ...]:
    normalized = " ".join(query.strip().split())
    if not normalized:
        return ()
    terms: list[str] = [normalized]
    for source, related in SEARCH_SYNONYMS.items():
        if source not in normalized:
            continue
        terms.append(source)
        terms.extend(related)
    return tuple(dict.fromkeys(terms))


def fuse_rankings(
    keyword_ids: Sequence[int],
    semantic_ids: Sequence[int],
    *,
    k: int = 60,
    business_scores: Mapping[int, float] | None = None,
) -> list[int]:
    scores: dict[int, float] = {}
    first_seen: dict[int, int] = {}
    seen_no = 0
    for ranking in (keyword_ids, semantic_ids):
        for position, product_id in enumerate(ranking, start=1):
            if product_id not in first_seen:
                first_seen[product_id] = seen_no
                seen_no += 1
            scores[product_id] = scores.get(product_id, 0.0) + 1 / (k + position)
    if business_scores:
        for product_id, quality in business_scores.items():
            if product_id in scores:
                scores[product_id] += max(0.0, min(1.0, quality)) * 0.002
    return sorted(scores, key=lambda item: (-scores[item], first_seen[item]))


class KnowledgeCatalogSemanticSearch:
    def __init__(
        self,
        session: AsyncSession,
        *,
        embeddings: EmbeddingGateway,
        vectors: VectorGateway,
    ) -> None:
        self.ai = AiRepository(session)
        self.embeddings = embeddings
        self.vectors = vectors

    @classmethod
    async def from_default_config(
        cls, session: AsyncSession
    ) -> "KnowledgeCatalogSemanticSearch | None":
        ai = AiRepository(session)
        config = await ai.get_default_model_config()
        if config is None:
            return None
        settings = get_settings()
        try:
            api_key = (
                decrypt_secret(config.api_key_ciphertext)
                if config.api_key_ciphertext
                else settings.ai_api_key
            )
        except AppError as exc:
            logger.warning(
                "Catalog semantic search configuration is invalid; disabling semantic mode",
                extra={"error_code": exc.code},
            )
            return None
        if not api_key or not (config.embedding_model or settings.ai_embedding_model):
            return None
        return cls(
            session,
            embeddings=BailianEmbeddingGateway(config, api_key, settings),
            vectors=QdrantKnowledgeGateway(settings),
        )

    async def search(self, query: str, limit: int) -> list[int]:
        embedded = await self.embeddings.embed([query])
        if len(embedded) != 1 or not embedded[0]:
            return []
        matches = await self.vectors.search(
            embedded[0], product_id=None, limit=max(limit * 3, limit)
        )
        rows = await self.ai.get_knowledge_chunks_by_point_ids(
            [match.point_id for match in matches]
        )
        by_point = {
            chunk.vector_point_id: (chunk.product_id or document.product_id)
            for chunk, document in rows
        }
        product_ids: list[int] = []
        for match in matches:
            product_id = by_point.get(match.point_id)
            if product_id is not None and product_id not in product_ids:
                product_ids.append(product_id)
                if len(product_ids) >= limit:
                    break
        return product_ids


class CatalogSearchService:
    def __init__(
        self, session: AsyncSession, *, semantic_search: SemanticSearch | None = None
    ) -> None:
        self.catalog = CatalogRepository(session)
        self.session = session
        self.semantic_search = semantic_search

    async def suggest(self, query: str, *, limit: int = 8) -> list[SearchSuggestion]:
        normalized = " ".join(query.strip().split())
        if not normalized:
            return []
        products, categories, brands = await self.catalog.search_suggestions(
            expand_search_terms(normalized), limit=limit
        )
        suggestions = [
            SearchSuggestion(kind="product", label=item.name, value=item.name, product_id=item.id)
            for item in products
        ]
        suggestions.extend(
            SearchSuggestion(kind="category", label=item.name, value=item.name)
            for item in categories
        )
        suggestions.extend(
            SearchSuggestion(kind="brand", label=item.name, value=item.name) for item in brands
        )
        return suggestions[:limit]

    async def record_event(
        self, payload: SearchEventRequest, *, user_id: int | None
    ) -> SearchEvent:
        if payload.event_type == "click":
            product = await self.catalog.get_product(payload.product_id or 0)
            if product is None or product.status != ProductStatus.ON_SALE:
                raise NotFoundError("商品不存在或已下架")
        event = SearchEvent(
            user_id=user_id,
            product_id=payload.product_id,
            session_key=payload.session_key,
            event_type=payload.event_type,
            query=(payload.query or "").strip() or None,
            filters=payload.filters.model_dump(mode="json", exclude_none=True)
            if payload.filters
            else None,
            result_count=payload.result_count,
            occurred_at=datetime.now(UTC),
        )
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def search(
        self,
        *,
        page: int,
        page_size: int,
        keyword: str | None,
        category_id: int | None,
        brand_id: int | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
        in_stock: bool,
        sort: str,
    ) -> CatalogSearchResult:
        query = " ".join((keyword or "").strip().split())
        terms = expand_search_terms(query)
        needs_relevance_ranking = bool(query) and sort == "relevance"
        candidate_limit = min(max(page * page_size, 200), 1000)
        lexical = await self.catalog.search_catalog_products(
            terms=terms,
            category_id=category_id,
            brand_id=brand_id,
            min_price=min_price,
            max_price=max_price,
            in_stock=in_stock,
            offset=0 if needs_relevance_ranking else (page - 1) * page_size,
            limit=candidate_limit if needs_relevance_ranking else page_size,
            sort=sort,
        )
        search_mode = "catalog"
        products_by_id = {item.id: item for item in lexical}
        if needs_relevance_ranking:
            lexical = sorted(
                lexical,
                key=lambda item: self._lexical_score(item, query, terms),
                reverse=True,
            )
        ranked_ids = [item.id for item in lexical]
        if needs_relevance_ranking and self.semantic_search is not None:
            try:
                semantic_ids = list(
                    await asyncio.wait_for(self.semantic_search(query, 60), timeout=1.5)
                )
            except Exception as exc:
                logger.warning(
                    "Catalog semantic search unavailable; using catalog fallback",
                    extra={"error_type": type(exc).__name__},
                )
                semantic_ids = []
            if semantic_ids:
                search_mode = "hybrid"
            semantic_products = await self.catalog.search_catalog_products(
                terms=(),
                category_id=category_id,
                brand_id=brand_id,
                min_price=min_price,
                max_price=max_price,
                in_stock=in_stock,
                product_ids=semantic_ids,
            )
            products_by_id.update((item.id, item) for item in semantic_products)
            in_stock_ids = await self.catalog.list_in_stock_product_ids(
                list(products_by_id)
            )
            ranked_ids = fuse_rankings(
                ranked_ids,
                semantic_ids,
                business_scores={
                    item.id: self._business_quality(item, item.id in in_stock_ids)
                    for item in products_by_id.values()
                },
            )
            ranked_ids = [item for item in ranked_ids if item in products_by_id]

        products = [products_by_id[item] for item in ranked_ids]
        if needs_relevance_ranking and search_mode == "catalog":
            products = sorted(
                products,
                key=lambda item: self._lexical_score(item, query, terms),
                reverse=True,
            )

        facets = await self._build_facets(
            terms=terms,
            category_id=category_id,
            brand_id=brand_id,
            min_price=min_price,
            max_price=max_price,
            in_stock=in_stock,
        )
        total = await self.catalog.count_catalog_products(
            terms=terms,
            category_id=category_id,
            brand_id=brand_id,
            min_price=min_price,
            max_price=max_price,
            in_stock=in_stock,
        )
        start = (page - 1) * page_size if needs_relevance_ranking else 0
        return CatalogSearchResult(
            items=[
                ProductSummary.model_validate(item) for item in products[start : start + page_size]
            ],
            page=page,
            page_size=page_size,
            total=total,
            facets=facets,
            search_mode=search_mode,
        )

    async def _build_facets(
        self,
        *,
        terms: Sequence[str],
        category_id: int | None,
        brand_id: int | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
        in_stock: bool,
    ) -> SearchFacets:
        category_rows, brand_rows, facet_min, facet_max, stock_count = (
            await self.catalog.search_catalog_facets(
                terms=terms,
                category_id=category_id,
                brand_id=brand_id,
                min_price=min_price,
                max_price=max_price,
                in_stock=in_stock,
            )
        )
        return SearchFacets(
            categories=[
                SearchFacetItem(id=item, name=name, count=count)
                for item, name, count in category_rows
            ],
            brands=[
                SearchFacetItem(id=item, name=name, count=count)
                for item, name, count in brand_rows
            ],
            min_price=facet_min,
            max_price=facet_max,
            in_stock_count=stock_count,
        )

    @staticmethod
    def _sort_products(products: Sequence[Product], sort: str) -> list[Product]:
        if sort == "price_asc":
            return sorted(products, key=lambda item: (item.min_price, item.id))
        if sort == "price_desc":
            return sorted(products, key=lambda item: (item.max_price, item.id), reverse=True)
        if sort == "sales":
            return sorted(products, key=lambda item: (item.sales_count, item.id), reverse=True)
        if sort == "rating":
            return sorted(
                products, key=lambda item: (item.rating, item.review_count, item.id), reverse=True
            )
        return sorted(products, key=lambda item: (item.created_at, item.id), reverse=True)

    @staticmethod
    def _lexical_score(product: Product, query: str, terms: Sequence[str]) -> float:
        name = product.name.casefold()
        subtitle = (product.subtitle or "").casefold()
        normalized = query.casefold()
        score = 0.0
        if name == normalized:
            score += 100
        elif normalized in name:
            score += 60
        elif normalized in subtitle:
            score += 30
        phrase_length = max(
            SequenceMatcher(None, normalized, name, autojunk=False).find_longest_match().size,
            SequenceMatcher(None, normalized, subtitle, autojunk=False)
            .find_longest_match()
            .size,
        )
        if phrase_length >= 2:
            score += phrase_length**2 * 2
        score += sum(12 for term in terms[1:] if term.casefold() in name)
        score += sum(5 for term in terms[1:] if term.casefold() in subtitle)
        score += float(product.rating) * 0.5 + log1p(product.sales_count) * 0.25
        return score

    @staticmethod
    def _business_quality(product: Product, in_stock: bool) -> float:
        rating_quality = min(1.0, float(product.rating) / 5) * 0.5
        sales_quality = min(1.0, log1p(product.sales_count) / 10) * 0.3
        stock_quality = 0.2 if in_stock else 0.0
        return rating_quality + sales_quality + stock_quality
