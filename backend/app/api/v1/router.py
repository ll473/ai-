from fastapi import APIRouter

from backend.app.api.v1.routes import (
    admin_ai,
    admin_catalog,
    admin_knowledge,
    admin_operations,
    admin_system,
    admin_trade,
    ai,
    auth,
    catalog,
    health,
    trade,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(catalog.router)
api_router.include_router(admin_catalog.router)
api_router.include_router(admin_knowledge.router)
api_router.include_router(admin_operations.router)
api_router.include_router(admin_system.router)
api_router.include_router(trade.router)
api_router.include_router(admin_trade.router)
api_router.include_router(admin_ai.router)
api_router.include_router(ai.router)
