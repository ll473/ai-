from collections.abc import Sequence
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app.models import Base
from backend.app.models.catalog import Category, Product
from backend.app.models.enums import DocumentStatus, ProductStatus
from backend.app.schemas.ai import KnowledgeDocumentCreate, ProductQuestionRequest
from backend.app.services.knowledge import (
    KnowledgeService,
    VectorMatch,
    VectorRecord,
    content_checksum,
    split_knowledge_text,
)


class FakeEmbeddings:
    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [[float(len(text)), 1.0, 0.5] for text in texts]


class FakeVectors:
    def __init__(self) -> None:
        self.records: list[VectorRecord] = []
        self.dimension = 0

    async def ensure_collection(self, dimension: int) -> None:
        self.dimension = dimension

    async def upsert(self, records: Sequence[VectorRecord]) -> None:
        self.records = list(records)

    async def delete(self, point_ids: Sequence[str]) -> None:
        self.records = [item for item in self.records if item.point_id not in point_ids]

    async def search(
        self, vector: list[float], *, product_id: int | None, limit: int
    ) -> list[VectorMatch]:
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
            embeddings=FakeEmbeddings(),
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

        result = await service.ask(
            ProductQuestionRequest(question="适合长时间办公吗？", product_id=1)
        )
        assert "腰部支撑" in result.answer
        assert result.citations
        assert result.citations[0].document_title == "人体工学椅资料"

    await engine.dispose()
