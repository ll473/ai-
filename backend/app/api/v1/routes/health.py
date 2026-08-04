from fastapi import APIRouter

from backend.app.core.config import get_settings
from backend.app.core.responses import ApiResponse

router = APIRouter(tags=["系统"])


@router.get("/health", response_model=ApiResponse[dict[str, str]])
async def health() -> ApiResponse[dict[str, str]]:
    settings = get_settings()
    return ApiResponse(
        data={
            "status": "healthy",
            "service": settings.app_name,
            "environment": settings.app_env,
        }
    )

