from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app.core.exceptions import NotFoundError
from backend.app.models import Base
from backend.app.models.ai import AiModelConfig, KnowledgeChunk, KnowledgeDocument
from backend.app.models.catalog import Brand, Category, Product, ProductSku
from backend.app.models.enums import DocumentStatus, ProductStatus
from backend.app.schemas.catalog import SearchEventRequest
from backend.app.services.catalog_search import (
    CatalogSearchService,
    KnowledgeCatalogSemanticSearch,
    expand_search_terms,
    fuse_rankings,
)
from backend.app.services.knowledge import VectorMatch


def test_expand_search_terms_connects_gift_requests_to_catalog_words() -> None:
    assert expand_search_terms("父母礼物") == (
        "父母礼物",
        "父母",
        "长辈",
        "老人",
        "礼物",
        "礼盒",
        "礼品",
    )


def test_fuse_rankings_combines_keyword_and_semantic_results() -> None:
    assert fuse_rankings([10, 20, 30], [30, 20, 40]) == [30, 20, 10, 40]


def test_fuse_rankings_uses_business_quality_to_break_recall_ties() -> None:
    assert fuse_rankings(
        [10, 20],
        [20, 10],
        business_scores={10: 0.1, 20: 0.9},
    ) == [20, 10]


def test_search_event_filters_reject_unbounded_or_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        SearchEventRequest(
            event_type="search",
            query="办公椅",
            session_key="session-001",
            filters={"unexpected_payload": "x" * 5000},
        )


@pytest.mark.asyncio
async def test_suggestions_use_synonyms_and_only_return_sellable_products() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        session.add_all(
            [
                Category(id=1, name="礼品", slug="gifts", enabled=True),
                Brand(id=1, name="Morrow", slug="morrow", enabled=True),
                Product(
                    id=1,
                    category_id=1,
                    brand_id=1,
                    name="Morrow 手冲咖啡礼盒套装",
                    product_no="GIFT-001",
                    min_price=Decimal("369.00"),
                    max_price=Decimal("369.00"),
                    status=ProductStatus.ON_SALE,
                ),
                Product(
                    id=2,
                    category_id=1,
                    brand_id=1,
                    name="已下架礼盒",
                    product_no="GIFT-002",
                    min_price=Decimal("99.00"),
                    max_price=Decimal("99.00"),
                    status=ProductStatus.OFF_SALE,
                ),
            ]
        )
        await session.commit()

        suggestions = await CatalogSearchService(session).suggest("父母礼物", limit=8)

        assert [(item.kind, item.label, item.product_id) for item in suggestions] == [
            ("product", "Morrow 手冲咖啡礼盒套装", 1),
            ("category", "礼品", None),
        ]

    await engine.dispose()


@pytest.mark.asyncio
async def test_search_facets_include_stock_and_filter_out_disabled_skus() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        session.add_all(
            [
                Category(id=1, name="办公", slug="office", enabled=True),
                Brand(id=1, name="EonFlex", slug="eonflex", enabled=True),
                Product(
                    id=1,
                    category_id=1,
                    brand_id=1,
                    name="EonFlex 人体工学办公椅",
                    subtitle="适合长时间办公",
                    product_no="CHAIR-001",
                    min_price=Decimal("1299.00"),
                    max_price=Decimal("1299.00"),
                    rating=Decimal("4.90"),
                    sales_count=20,
                    status=ProductStatus.ON_SALE,
                ),
                Product(
                    id=2,
                    category_id=1,
                    brand_id=1,
                    name="基础办公椅",
                    product_no="CHAIR-002",
                    min_price=Decimal("399.00"),
                    max_price=Decimal("399.00"),
                    status=ProductStatus.ON_SALE,
                ),
                ProductSku(
                    id=1,
                    product_id=1,
                    sku_no="CHAIR-001-BLACK",
                    name="曜石黑",
                    price=Decimal("1299.00"),
                    stock=8,
                    locked_stock=2,
                    enabled=True,
                ),
                ProductSku(
                    id=2,
                    product_id=2,
                    sku_no="CHAIR-002-GRAY",
                    name="灰色",
                    price=Decimal("399.00"),
                    stock=20,
                    locked_stock=0,
                    enabled=False,
                ),
            ]
        )
        await session.commit()

        result = await CatalogSearchService(session).search(
            page=1,
            page_size=20,
            keyword="办公椅",
            category_id=None,
            brand_id=None,
            min_price=None,
            max_price=None,
            in_stock=True,
            sort="relevance",
        )

        assert [item.id for item in result.items] == [1]
        assert result.total == 1
        assert result.facets.in_stock_count == 1
        assert [(item.id, item.count) for item in result.facets.categories] == [(1, 1)]
        assert [(item.id, item.count) for item in result.facets.brands] == [(1, 1)]

        all_result = await CatalogSearchService(session).search(
            page=1,
            page_size=20,
            keyword="办公椅",
            category_id=None,
            brand_id=None,
            min_price=None,
            max_price=None,
            in_stock=False,
            sort="relevance",
        )
        assert all_result.total == 2
        assert all_result.facets.in_stock_count == 1

    await engine.dispose()


@pytest.mark.asyncio
async def test_category_facets_keep_alternative_categories_visible() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        session.add_all(
            [
                Category(id=1, name="礼盒", slug="gift-boxes", enabled=True),
                Category(id=2, name="健康", slug="health", enabled=True),
                Product(
                    id=1,
                    category_id=1,
                    name="长辈茶礼盒",
                    product_no="GIFT-BOX",
                    min_price=Decimal("199.00"),
                    max_price=Decimal("199.00"),
                    status=ProductStatus.ON_SALE,
                ),
                Product(
                    id=2,
                    category_id=2,
                    name="长辈健康礼盒",
                    product_no="GIFT-HEALTH",
                    min_price=Decimal("299.00"),
                    max_price=Decimal("299.00"),
                    status=ProductStatus.ON_SALE,
                ),
            ]
        )
        await session.commit()

        result = await CatalogSearchService(session).search(
            page=1,
            page_size=20,
            keyword="父母礼物",
            category_id=1,
            brand_id=None,
            min_price=None,
            max_price=None,
            in_stock=False,
            sort="relevance",
        )

        assert [item.id for item in result.items] == [1]
        assert [(item.id, item.count) for item in result.facets.categories] == [
            (1, 1),
            (2, 1),
        ]

    await engine.dispose()


@pytest.mark.asyncio
async def test_record_search_event_persists_anonymous_query_context() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        event = await CatalogSearchService(session).record_event(
            SearchEventRequest(
                event_type="search",
                query="父母礼物",
                session_key="session-001",
                result_count=3,
                filters={"in_stock": True},
            ),
            user_id=None,
        )

        assert event.id is not None
        assert event.query == "父母礼物"
        assert event.session_key == "session-001"
        assert event.result_count == 3
        assert event.filters == {"in_stock": True}

    await engine.dispose()


@pytest.mark.asyncio
async def test_click_event_rejects_unknown_product() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        with pytest.raises(NotFoundError):
            await CatalogSearchService(session).record_event(
                SearchEventRequest(
                    event_type="click",
                    product_id=999,
                    query="办公椅",
                    session_key="session-001",
                ),
                user_id=None,
            )

    await engine.dispose()


@pytest.mark.asyncio
async def test_click_event_accepts_reloaded_sellable_product() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        session.add_all(
            [
                Category(id=1, name="办公", slug="office-click", enabled=True),
                Product(
                    id=1,
                    category_id=1,
                    name="人体工学椅",
                    product_no="CLICK-CHAIR",
                    min_price=Decimal("999.00"),
                    max_price=Decimal("999.00"),
                    status=ProductStatus.ON_SALE,
                ),
            ]
        )
        await session.commit()

    async with session_factory() as session:
        event = await CatalogSearchService(session).record_event(
            SearchEventRequest(
                event_type="click",
                product_id=1,
                query="办公椅",
                session_key="session-001",
            ),
            user_id=None,
        )
        assert event.product_id == 1

    await engine.dispose()


@pytest.mark.asyncio
async def test_search_falls_back_when_semantic_provider_is_unavailable() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def unavailable_semantic_search(_: str, __: int) -> list[int]:
        raise TimeoutError

    async with session_factory() as session:
        session.add_all(
            [
                Category(id=1, name="礼品", slug="gifts", enabled=True),
                Product(
                    id=1,
                    category_id=1,
                    name="长辈养生礼盒",
                    product_no="GIFT-003",
                    min_price=Decimal("199.00"),
                    max_price=Decimal("199.00"),
                    status=ProductStatus.ON_SALE,
                ),
            ]
        )
        await session.commit()

        result = await CatalogSearchService(
            session, semantic_search=unavailable_semantic_search
        ).search(
            page=1,
            page_size=20,
            keyword="父母礼物",
            category_id=None,
            brand_id=None,
            min_price=None,
            max_price=None,
            in_stock=False,
            sort="relevance",
        )

        assert [item.id for item in result.items] == [1]
        assert result.search_mode == "catalog"

    await engine.dispose()


@pytest.mark.asyncio
async def test_semantic_search_maps_vector_matches_to_unique_products() -> None:
    class FakeEmbeddings:
        async def embed(self, texts: list[str]) -> list[list[float]]:
            assert texts == ["适合长时间工作的座椅"]
            return [[0.1, 0.2]]

    class FakeVectors:
        async def search(
            self, vector: list[float], *, product_id: int | None, limit: int
        ) -> list[VectorMatch]:
            assert vector == [0.1, 0.2]
            assert product_id is None
            assert limit == 6
            return [
                VectorMatch(point_id="chunk-2", score=0.9),
                VectorMatch(point_id="chunk-1", score=0.8),
            ]

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        session.add_all(
            [
                Category(id=1, name="办公", slug="office", enabled=True),
                Product(
                    id=1,
                    category_id=1,
                    name="人体工学椅",
                    product_no="CHAIR-SEMANTIC",
                    min_price=Decimal("1299.00"),
                    max_price=Decimal("1299.00"),
                    status=ProductStatus.ON_SALE,
                ),
                KnowledgeDocument(
                    id=1,
                    title="人体工学椅详情",
                    source_type="PRODUCT_DETAIL",
                    product_id=1,
                    content="适合长时间办公",
                    status=DocumentStatus.READY,
                ),
                KnowledgeChunk(
                    id=1,
                    document_id=1,
                    product_id=1,
                    chunk_index=0,
                    content="腰部支撑",
                    vector_point_id="chunk-1",
                ),
                KnowledgeChunk(
                    id=2,
                    document_id=1,
                    product_id=1,
                    chunk_index=1,
                    content="长时间办公",
                    vector_point_id="chunk-2",
                ),
            ]
        )
        await session.commit()

        product_ids = await KnowledgeCatalogSemanticSearch(
            session,
            embeddings=FakeEmbeddings(),
            vectors=FakeVectors(),
        ).search("适合长时间工作的座椅", 2)

        assert product_ids == [1]

    await engine.dispose()


@pytest.mark.asyncio
async def test_semantic_search_config_failure_disables_semantic_mode() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        session.add(
            AiModelConfig(
                name="invalid-secret",
                provider="bailian",
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                api_key_ciphertext="not-a-valid-ciphertext",
                chat_model="qwen3.7-plus",
                embedding_model="qwen3.7-text-embedding",
                enabled=True,
                is_default=True,
            )
        )
        await session.commit()

        provider = await KnowledgeCatalogSemanticSearch.from_default_config(session)

        assert provider is None

    await engine.dispose()


@pytest.mark.asyncio
async def test_long_phrase_relevance_beats_generic_sales_popularity() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def empty_semantic_search(_: str, __: int) -> list[int]:
        return []

    async with session_factory() as session:
        session.add_all(
            [
                Category(id=1, name="办公", slug="office", enabled=True),
                Product(
                    id=1,
                    category_id=1,
                    name="自适应人体工学椅",
                    subtitle="动态腰托，为长时间办公提供稳定支撑",
                    product_no="CHAIR-PHRASE",
                    min_price=Decimal("1299.00"),
                    max_price=Decimal("1299.00"),
                    rating=Decimal("5.00"),
                    sales_count=286,
                    status=ProductStatus.ON_SALE,
                ),
                Product(
                    id=2,
                    category_id=1,
                    name="自适应降噪耳机",
                    subtitle="混合主动降噪，通勤办公都安静",
                    product_no="HEADPHONE-GENERIC",
                    min_price=Decimal("899.00"),
                    max_price=Decimal("899.00"),
                    rating=Decimal("5.00"),
                    sales_count=342,
                    status=ProductStatus.ON_SALE,
                ),
            ]
        )
        await session.commit()

        result = await CatalogSearchService(
            session, semantic_search=empty_semantic_search
        ).search(
            page=1,
            page_size=20,
            keyword="适合长时间办公",
            category_id=None,
            brand_id=None,
            min_price=None,
            max_price=None,
            in_stock=False,
            sort="relevance",
        )

        assert [item.id for item in result.items] == [1, 2]

    await engine.dispose()
