from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from backend.app.api.v1.router import api_router
from backend.app.core.config import get_settings
from backend.app.core.database import engine
from backend.app.core.exceptions import AppError

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.app_debug,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir, check_dir=False), name="uploads")


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": exc.details,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "请求参数校验失败",
            "data": jsonable_encoder(exc.errors()),
        },
    )


@app.get("/health", include_in_schema=False)
async def root_health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/ready", include_in_schema=False)
async def readiness() -> dict[str, str]:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return {"status": "ready"}


app.include_router(api_router, prefix=settings.api_v1_prefix)


frontend_dist = settings.upload_dir.parent / "frontend" / "dist"
frontend_index = frontend_dist / "index.html"


@app.get("/", include_in_schema=False)
async def storefront() -> Response:
    """Serve the production storefront while keeping Vite available in development."""
    if frontend_index.is_file():
        return FileResponse(frontend_index)
    return JSONResponse({"status": "healthy", "docs": "/docs"})


@app.get("/{full_path:path}", include_in_schema=False)
async def storefront_route(full_path: str) -> Response:
    """Support Vue Router history URLs and built frontend assets."""
    root = frontend_dist.resolve()
    requested = (frontend_dist / full_path).resolve()
    if requested.is_file() and (requested == root or root in requested.parents):
        return FileResponse(requested)
    if frontend_index.is_file():
        return FileResponse(frontend_index)
    return JSONResponse({"code": "NOT_FOUND", "message": "Page not found"}, status_code=404)
