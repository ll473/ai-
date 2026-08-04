from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.ai import (
    AgentRun,
    AgentStep,
    AiModelConfig,
    FunctionTool,
    KnowledgeChunk,
    KnowledgeDocument,
    OperationReport,
    PromptTemplate,
    Recommendation,
    RecommendationItem,
    ReviewAnalysis,
    ToolCallLog,
)
from backend.app.models.catalog import Product, ProductSku

ToolLogRow = tuple[ToolCallLog, FunctionTool]
KnowledgeDocumentRow = tuple[KnowledgeDocument, int]
KnowledgeChunkRow = tuple[KnowledgeChunk, KnowledgeDocument]
RecommendationItemRow = tuple[RecommendationItem, Product, ProductSku | None]


class AiRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_model_configs(self) -> list[AiModelConfig]:
        return list(
            (
                await self.session.scalars(
                    select(AiModelConfig).order_by(
                        AiModelConfig.is_default.desc(), AiModelConfig.created_at.desc()
                    )
                )
            ).all()
        )

    async def get_model_config(self, config_id: int) -> AiModelConfig | None:
        return await self.session.get(AiModelConfig, config_id)

    async def get_default_model_config(self) -> AiModelConfig | None:
        result = await self.session.execute(
            select(AiModelConfig)
            .where(AiModelConfig.enabled.is_(True), AiModelConfig.is_default.is_(True))
            .order_by(AiModelConfig.id)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def clear_default_model_configs(self, *, exclude_id: int | None = None) -> None:
        statement = update(AiModelConfig)
        if exclude_id is not None:
            statement = statement.where(AiModelConfig.id != exclude_id)
        await self.session.execute(statement.values(is_default=False))

    async def model_name_exists(self, name: str, *, exclude_id: int | None = None) -> bool:
        statement = select(AiModelConfig.id).where(AiModelConfig.name == name)
        if exclude_id is not None:
            statement = statement.where(AiModelConfig.id != exclude_id)
        return await self.session.scalar(statement.limit(1)) is not None

    async def list_prompts(self) -> list[PromptTemplate]:
        statement = select(PromptTemplate).order_by(
            PromptTemplate.scene, PromptTemplate.code, PromptTemplate.version.desc()
        )
        return list((await self.session.scalars(statement)).all())

    async def get_prompt(self, prompt_id: int) -> PromptTemplate | None:
        return await self.session.get(PromptTemplate, prompt_id)

    async def get_scene_prompt(self, scene: str) -> PromptTemplate | None:
        result = await self.session.execute(
            select(PromptTemplate)
            .where(PromptTemplate.scene == scene, PromptTemplate.enabled.is_(True))
            .order_by(PromptTemplate.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def prompt_version_exists(self, code: str, version: int) -> bool:
        return (
            await self.session.scalar(
                select(PromptTemplate.id).where(
                    PromptTemplate.code == code, PromptTemplate.version == version
                )
            )
            is not None
        )

    async def list_tools(self, *, enabled_only: bool = False) -> list[FunctionTool]:
        statement = select(FunctionTool)
        if enabled_only:
            statement = statement.where(FunctionTool.enabled.is_(True))
        return list((await self.session.scalars(statement.order_by(FunctionTool.name))).all())

    async def get_tool(self, tool_id: int) -> FunctionTool | None:
        return await self.session.get(FunctionTool, tool_id)

    async def get_tool_by_name(self, name: str) -> FunctionTool | None:
        result = await self.session.execute(select(FunctionTool).where(FunctionTool.name == name))
        return result.scalar_one_or_none()

    async def list_tool_logs(
        self, *, page: int, page_size: int
    ) -> tuple[list[ToolLogRow], int]:
        base = select(ToolCallLog, FunctionTool).join(
            FunctionTool, FunctionTool.id == ToolCallLog.tool_id
        )
        total = int(
            await self.session.scalar(
                select(func.count()).select_from(base.order_by(None).subquery())
            )
            or 0
        )
        statement = (
            base.order_by(ToolCallLog.created_at.desc(), ToolCallLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await self.session.execute(statement)).tuples().all()), total

    async def get_agent_run(self, run_id: int, *, user_id: int | None = None) -> AgentRun | None:
        statement = select(AgentRun).where(AgentRun.id == run_id)
        if user_id is not None:
            statement = statement.where(AgentRun.user_id == user_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_agent_runs(
        self, *, page: int, page_size: int, user_id: int | None = None
    ) -> tuple[list[AgentRun], int]:
        base = select(AgentRun)
        if user_id is not None:
            base = base.where(AgentRun.user_id == user_id)
        total = int(
            await self.session.scalar(
                select(func.count()).select_from(base.order_by(None).subquery())
            )
            or 0
        )
        statement = (
            base.order_by(AgentRun.created_at.desc(), AgentRun.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await self.session.scalars(statement)).all()), total

    async def list_agent_steps(self, run_id: int) -> list[AgentStep]:
        statement = (
            select(AgentStep)
            .where(AgentStep.agent_run_id == run_id)
            .order_by(AgentStep.step_no)
        )
        return list((await self.session.scalars(statement)).all())

    async def get_recommendation(self, run_id: int) -> Recommendation | None:
        result = await self.session.execute(
            select(Recommendation).where(Recommendation.agent_run_id == run_id)
        )
        return result.scalar_one_or_none()

    async def list_recommendation_items(
        self, recommendation_id: int
    ) -> list[RecommendationItemRow]:
        statement = (
            select(RecommendationItem, Product, ProductSku)
            .join(Product, Product.id == RecommendationItem.product_id)
            .outerjoin(ProductSku, ProductSku.id == RecommendationItem.sku_id)
            .where(RecommendationItem.recommendation_id == recommendation_id)
            .order_by(RecommendationItem.id)
        )
        return list((await self.session.execute(statement)).tuples().all())

    async def list_knowledge_documents(
        self, *, page: int, page_size: int
    ) -> tuple[list[KnowledgeDocumentRow], int]:
        total = int(await self.session.scalar(select(func.count(KnowledgeDocument.id))) or 0)
        statement = (
            select(KnowledgeDocument, func.count(KnowledgeChunk.id))
            .outerjoin(KnowledgeChunk, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .group_by(KnowledgeDocument.id)
            .order_by(KnowledgeDocument.updated_at.desc(), KnowledgeDocument.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self.session.execute(statement)).tuples().all()
        return [(document, int(chunk_count)) for document, chunk_count in rows], total

    async def get_knowledge_document(self, document_id: int) -> KnowledgeDocument | None:
        return await self.session.get(KnowledgeDocument, document_id)

    async def get_product_knowledge_document(
        self, product_id: int, source_type: str
    ) -> KnowledgeDocument | None:
        result = await self.session.execute(
            select(KnowledgeDocument).where(
                KnowledgeDocument.product_id == product_id,
                KnowledgeDocument.source_type == source_type,
            )
        )
        return result.scalar_one_or_none()

    async def list_knowledge_chunks(self, document_id: int) -> list[KnowledgeChunk]:
        statement = (
            select(KnowledgeChunk)
            .where(KnowledgeChunk.document_id == document_id)
            .order_by(KnowledgeChunk.chunk_index)
        )
        return list((await self.session.scalars(statement)).all())

    async def page_knowledge_chunks(
        self,
        *,
        page: int,
        page_size: int,
        document_id: int | None = None,
        product_id: int | None = None,
        keyword: str | None = None,
    ) -> tuple[list[KnowledgeChunkRow], int]:
        statement = select(KnowledgeChunk, KnowledgeDocument).join(
            KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id
        )
        if document_id is not None:
            statement = statement.where(KnowledgeChunk.document_id == document_id)
        if product_id is not None:
            statement = statement.where(KnowledgeChunk.product_id == product_id)
        if keyword:
            statement = statement.where(KnowledgeChunk.content.ilike(f"%{keyword.strip()}%"))
        total = int(
            await self.session.scalar(select(func.count()).select_from(statement.subquery())) or 0
        )
        rows = list(
            (
                await self.session.execute(
                    statement.order_by(
                        KnowledgeDocument.updated_at.desc(), KnowledgeChunk.chunk_index
                    )
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).tuples().all()
        )
        return rows, total

    async def get_knowledge_chunks_by_point_ids(
        self, point_ids: list[str]
    ) -> list[KnowledgeChunkRow]:
        if not point_ids:
            return []
        statement = (
            select(KnowledgeChunk, KnowledgeDocument)
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
            .where(
                KnowledgeChunk.vector_point_id.in_(point_ids),
                KnowledgeDocument.status == "READY",
            )
        )
        return list((await self.session.execute(statement)).tuples().all())

    async def delete_knowledge_chunks(self, document_id: int) -> None:
        await self.session.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id)
        )

    async def list_review_analyses(
        self, *, limit: int = 30
    ) -> list[tuple[ReviewAnalysis, Product | None]]:
        statement = (
            select(ReviewAnalysis, Product)
            .outerjoin(Product, Product.id == ReviewAnalysis.product_id)
            .order_by(ReviewAnalysis.created_at.desc(), ReviewAnalysis.id.desc())
            .limit(limit)
        )
        return list((await self.session.execute(statement)).tuples().all())

    async def list_operation_reports(self, *, limit: int = 30) -> list[OperationReport]:
        statement = (
            select(OperationReport)
            .order_by(OperationReport.created_at.desc(), OperationReport.id.desc())
            .limit(limit)
        )
        return list((await self.session.scalars(statement)).all())

    async def get_operation_report(self, report_id: int) -> OperationReport | None:
        return await self.session.get(OperationReport, report_id)

    def add(self, entity: object) -> None:
        self.session.add(entity)
