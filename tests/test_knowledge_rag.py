from collections.abc import Sequence
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app.models import Base
from backend.app.models.ai import Conversation, ConversationMessage
from backend.app.models.catalog import Category, Product, ProductSku
from backend.app.models.enums import ConversationRole, DocumentStatus, ProductStatus, QuestionType
from backend.app.schemas.ai import KnowledgeDocumentCreate, ProductQuestionRequest
from backend.app.services.knowledge import (
    BailianAnswerGateway,
    KnowledgeService,
    VectorMatch,
    VectorRecord,
    content_checksum,
    split_knowledge_text,
)


class FakeEmbeddings:
    def __init__(self) -> None:
        self.calls = 0

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls += 1
        return [[float(len(text)), 1.0, 0.5] for text in texts]


class FakeVectors:
    def __init__(self) -> None:
        self.records: list[VectorRecord] = []
        self.dimension = 0
        self.search_calls = 0

    async def ensure_collection(self, dimension: int) -> None:
        self.dimension = dimension

    async def upsert(self, records: Sequence[VectorRecord]) -> None:
        self.records = list(records)

    async def delete(self, point_ids: Sequence[str]) -> None:
        self.records = [item for item in self.records if item.point_id not in point_ids]

    async def search(
        self, vector: list[float], *, product_id: int | None, limit: int
    ) -> list[VectorMatch]:
        self.search_calls += 1
        matches = [
            VectorMatch(point_id=item.point_id, score=0.91)
            for item in self.records
            if product_id is None or item.payload["product_id"] == product_id
        ]
        return matches[:limit]


class FakeAnswers:
    async def answer(self, question: str, contexts: Sequence[str]) -> str:
        assert question == "适合长时间办公吗？"
        assert contexts
        return "资料显示这款椅子提供腰部支撑和可调节扶手。"


class UnavailableVectors(FakeVectors):
    async def search(
        self, vector: list[float], *, product_id: int | None, limit: int
    ) -> list[VectorMatch]:
        raise ConnectionError("vector store unavailable")


class ProductDetailAnswers:
    async def answer(self, question: str, contexts: Sequence[str]) -> str:
        assert question == "适合长时间办公吗"
        assert "EonFlex 自适应人体工学椅" in contexts[0]
        assert "动态腰托" in contexts[0]
        assert "曜石黑标准款" in contexts[0]
        return "适合长时间办公，动态腰托和可调扶手可以提供持续支撑。"


class CountingAnswers:
    def __init__(self) -> None:
        self.calls = 0

    async def answer(self, question: str, contexts: Sequence[str]) -> str:
        self.calls += 1
        return "模型生成的回答"


def test_product_qa_answer_gateway_prefers_the_fast_model() -> None:
    config = SimpleNamespace(
        chat_model="qwen3.7-plus",
        base_url="https://example.invalid/v1",
        max_tokens=1000,
    )
    settings = SimpleNamespace(
        ai_shopping_model="qwen3.7-flash",
        ai_chat_model="qwen3.7-plus",
        ai_base_url="https://example.invalid/v1",
    )

    gateway = BailianAnswerGateway(config, "test-key", settings)

    assert gateway.model == "qwen3.7-flash"


def test_chunking_is_deterministic_and_overlapping() -> None:
    content = "第一段" * 80 + "\n\n" + "第二段" * 80
    first = split_knowledge_text(content, max_chars=160, overlap_chars=30)
    second = split_knowledge_text(content, max_chars=160, overlap_chars=30)
    assert first == second
    assert len(first) >= 3
    assert first[0][-30:] in first[1]
    assert content_checksum(content) == content_checksum(content)


@pytest.mark.asyncio
async def test_document_index_and_rag_answer_use_persisted_chunks() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    embeddings = FakeEmbeddings()
    vectors = FakeVectors()

    async with session_factory() as session:
        session.add_all(
            [
                Category(id=1, name="办公", slug="office"),
                Product(
                    id=1,
                    category_id=1,
                    name="人体工学椅",
                    product_no="CHAIR001",
                    min_price=Decimal("1299.00"),
                    max_price=Decimal("1299.00"),
                    status=ProductStatus.ON_SALE,
                ),
            ]
        )
        await session.commit()
        service = KnowledgeService(
            session,
            embeddings=embeddings,
            vectors=vectors,
            answers=FakeAnswers(),
        )
        document = await service.create_document(
            KnowledgeDocumentCreate(
                title="人体工学椅资料",
                product_id=1,
                content=("腰部支撑可调节，扶手支持多档调节。" * 80),
            )
        )
        indexed = await service.index_document(document.id)
        assert indexed.status == DocumentStatus.READY
        assert indexed.chunk_count >= 2
        assert vectors.dimension == 3

        embeddings.calls = 0
        vectors.search_calls = 0

        result = await service.ask(
            ProductQuestionRequest(question="适合长时间办公吗？", product_id=1)
        )
        assert "腰部支撑" in result.answer
        assert result.citations
        assert result.citations[0].document_title == "人体工学椅资料"
        assert embeddings.calls == 0
        assert vectors.search_calls == 0

    await engine.dispose()


@pytest.mark.asyncio
async def test_recall_question_returns_latest_answer_for_the_selected_product() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        session.add_all(
            [
                Category(id=1, name="办公", slug="office"),
                Product(
                    id=1,
                    category_id=1,
                    name="人体工学椅",
                    product_no="CHAIR001",
                    min_price=Decimal("1299.00"),
                    max_price=Decimal("1299.00"),
                    status=ProductStatus.ON_SALE,
                ),
                Conversation(
                    id=1,
                    user_id=1,
                    title="适合长时间办公吗",
                    scene="PRODUCT_QA",
                ),
                ConversationMessage(
                    conversation_id=1,
                    role=ConversationRole.USER,
                    content="适合长时间办公吗",
                    question_type=QuestionType.PRODUCT_KNOWLEDGE,
                    metadata_json={"product_id": 1, "order_no": None},
                ),
                ConversationMessage(
                    conversation_id=1,
                    role=ConversationRole.ASSISTANT,
                    content="这把椅子适合长时间办公。",
                    question_type=QuestionType.PRODUCT_KNOWLEDGE,
                ),
                ConversationMessage(
                    conversation_id=1,
                    role=ConversationRole.USER,
                    content="适合新手吗",
                    question_type=QuestionType.PRODUCT_KNOWLEDGE,
                    metadata_json={"product_id": 4, "order_no": None},
                ),
                ConversationMessage(
                    conversation_id=1,
                    role=ConversationRole.ASSISTANT,
                    content="这套咖啡礼盒适合新手。",
                    question_type=QuestionType.PRODUCT_KNOWLEDGE,
                ),
                ConversationMessage(
                    conversation_id=1,
                    role=ConversationRole.USER,
                    content="你刚刚说什么",
                    question_type=QuestionType.PRODUCT_KNOWLEDGE,
                    metadata_json={"product_id": 1, "order_no": None},
                ),
                ConversationMessage(
                    conversation_id=1,
                    role=ConversationRole.ASSISTANT,
                    content="现有资料不足以确认，建议咨询客服。",
                    question_type=QuestionType.PRODUCT_KNOWLEDGE,
                ),
            ]
        )
        await session.commit()
        answers = CountingAnswers()

        result = await KnowledgeService(
            session,
            embeddings=FakeEmbeddings(),
            vectors=FakeVectors(),
            answers=answers,
        ).ask(
            ProductQuestionRequest(
                question="你刚刚说什么",
                product_id=1,
                conversation_id=1,
            )
        )

        assert result.answer == "这把椅子适合长时间办公。"
        assert answers.calls == 0

    await engine.dispose()


@pytest.mark.asyncio
async def test_question_uses_product_details_when_vector_store_is_unavailable() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        session.add_all(
            [
                Category(id=1, name="办公效率", slug="office"),
                Product(
                    id=1,
                    category_id=1,
                    name="EonFlex 自适应人体工学椅",
                    product_no="CHAIR001",
                    subtitle="动态腰托与 4D 扶手，适合长时间办公",
                    detail_markdown="动态腰托会随坐姿变化提供腰部支撑。",
                    parameters={"扶手": "4D 可调", "椅背": "透气网布"},
                    min_price=Decimal("1299.00"),
                    max_price=Decimal("1499.00"),
                    status=ProductStatus.ON_SALE,
                ),
                ProductSku(
                    id=1,
                    product_id=1,
                    sku_no="CHAIR-SKU-1",
                    name="曜石黑标准款",
                    attributes={"颜色": "曜石黑"},
                    price=Decimal("1299.00"),
                    stock=10,
                    enabled=True,
                ),
            ]
        )
        await session.commit()

        result = await KnowledgeService(
            session,
            embeddings=FakeEmbeddings(),
            vectors=UnavailableVectors(),
            answers=ProductDetailAnswers(),
        ).ask(
            ProductQuestionRequest(
                question="适合长时间办公吗",
                product_id=1,
            )
        )

        assert result.answer.startswith("适合长时间办公")
        assert result.citations == []

    await engine.dispose()
