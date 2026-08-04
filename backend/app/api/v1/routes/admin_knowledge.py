from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import require_admin
from backend.app.core.database import get_db
from backend.app.core.responses import ApiResponse
from backend.app.models.user import User
from backend.app.schemas.ai import (
    KnowledgeChunkPublic,
    KnowledgeDocumentCreate,
    KnowledgeDocumentPublic,
    KnowledgeDocumentUpdate,
    ProductKnowledgeSyncRequest,
)
from backend.app.schemas.common import PageData
from backend.app.services.knowledge import KnowledgeService

router = APIRouter(prefix="/admin/knowledge", tags=["管理端知识库"])
DbSession = Annotated[AsyncSession, Depends(get_db)]
AdminUser = Annotated[User, Depends(require_admin)]


@router.get("/chunks", response_model=ApiResponse[PageData[KnowledgeChunkPublic]])
async def list_chunks(
    session: DbSession,
    _: AdminUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    document_id: int | None = None,
    product_id: int | None = None,
    keyword: str | None = None,
) -> ApiResponse[PageData[KnowledgeChunkPublic]]:
    from backend.app.repositories.ai import AiRepository

    rows, total = await AiRepository(session).page_knowledge_chunks(
        page=page,
        page_size=page_size,
        document_id=document_id,
        product_id=product_id,
        keyword=keyword,
    )
    items = [
        KnowledgeChunkPublic(
            id=chunk.id,
            document_id=chunk.document_id,
            document_title=document.title,
            product_id=chunk.product_id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            token_count=chunk.token_count,
            vector_point_id=chunk.vector_point_id,
            metadata_json=chunk.metadata_json,
            created_at=chunk.created_at,
        )
        for chunk, document in rows
    ]
    return ApiResponse(
        data=PageData[KnowledgeChunkPublic](
            items=items, page=page, page_size=page_size, total=total
        )
    )


@router.get("/documents", response_model=ApiResponse[PageData[KnowledgeDocumentPublic]])
async def list_documents(
    session: DbSession,
    _: AdminUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ApiResponse[PageData[KnowledgeDocumentPublic]]:
    return ApiResponse(
        data=await KnowledgeService(session).list_documents(page=page, page_size=page_size)
    )


@router.post(
    "/documents",
    response_model=ApiResponse[KnowledgeDocumentPublic],
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    payload: KnowledgeDocumentCreate, session: DbSession, _: AdminUser
) -> ApiResponse[KnowledgeDocumentPublic]:
    return ApiResponse(
        message="知识文档已创建",
        data=await KnowledgeService(session).create_document(payload),
    )


@router.patch(
    "/documents/{document_id}", response_model=ApiResponse[KnowledgeDocumentPublic]
)
async def update_document(
    document_id: int,
    payload: KnowledgeDocumentUpdate,
    session: DbSession,
    _: AdminUser,
) -> ApiResponse[KnowledgeDocumentPublic]:
    return ApiResponse(
        message="知识文档已更新",
        data=await KnowledgeService(session).update_document(document_id, payload),
    )


@router.post(
    "/documents/{document_id}/index", response_model=ApiResponse[KnowledgeDocumentPublic]
)
async def index_document(
    document_id: int, session: DbSession, _: AdminUser
) -> ApiResponse[KnowledgeDocumentPublic]:
    return ApiResponse(
        message="知识文档索引完成",
        data=await KnowledgeService(session).index_document(document_id),
    )


@router.post("/sync-product", response_model=ApiResponse[KnowledgeDocumentPublic])
async def sync_product(
    payload: ProductKnowledgeSyncRequest, session: DbSession, _: AdminUser
) -> ApiResponse[KnowledgeDocumentPublic]:
    return ApiResponse(
        message="商品资料已同步到知识库，请执行索引",
        data=await KnowledgeService(session).sync_product(payload.product_id),
    )
