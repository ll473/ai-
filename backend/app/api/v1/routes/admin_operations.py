from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import require_admin
from backend.app.core.database import get_db
from backend.app.core.responses import ApiResponse
from backend.app.models.user import User
from backend.app.schemas.ai import (
    OperationReportGenerateRequest,
    OperationReportPublic,
    OperationsDashboardPublic,
    ReviewAnalysisGenerateRequest,
    ReviewAnalysisPublic,
)
from backend.app.services.operations_ai import OperationsAiService

router = APIRouter(prefix="/admin/operations", tags=["管理端运营分析"])
DbSession = Annotated[AsyncSession, Depends(get_db)]
AdminUser = Annotated[User, Depends(require_admin)]


@router.get("/dashboard", response_model=ApiResponse[OperationsDashboardPublic])
async def get_dashboard(
    session: DbSession,
    _: AdminUser,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> ApiResponse[OperationsDashboardPublic]:
    return ApiResponse(data=await OperationsAiService(session).get_dashboard(days))


@router.get("/review-analyses", response_model=ApiResponse[list[ReviewAnalysisPublic]])
async def list_review_analyses(
    session: DbSession, _: AdminUser
) -> ApiResponse[list[ReviewAnalysisPublic]]:
    return ApiResponse(data=await OperationsAiService(session).list_review_analyses())


@router.post(
    "/review-analyses",
    response_model=ApiResponse[ReviewAnalysisPublic],
    status_code=status.HTTP_201_CREATED,
)
async def generate_review_analysis(
    payload: ReviewAnalysisGenerateRequest, session: DbSession, _: AdminUser
) -> ApiResponse[ReviewAnalysisPublic]:
    return ApiResponse(
        message="评价分析已生成",
        data=await OperationsAiService(session).generate_review_analysis(payload),
    )


@router.get("/reports", response_model=ApiResponse[list[OperationReportPublic]])
async def list_reports(
    session: DbSession, _: AdminUser
) -> ApiResponse[list[OperationReportPublic]]:
    return ApiResponse(data=await OperationsAiService(session).list_reports())


@router.post(
    "/reports",
    response_model=ApiResponse[OperationReportPublic],
    status_code=status.HTTP_201_CREATED,
)
async def generate_report(
    payload: OperationReportGenerateRequest, session: DbSession, _: AdminUser
) -> ApiResponse[OperationReportPublic]:
    return ApiResponse(
        message="运营报告已生成",
        data=await OperationsAiService(session).generate_report(payload),
    )


@router.get("/reports/{report_id}", response_model=ApiResponse[OperationReportPublic])
async def get_report(
    report_id: int, session: DbSession, _: AdminUser
) -> ApiResponse[OperationReportPublic]:
    return ApiResponse(data=await OperationsAiService(session).get_report(report_id))
