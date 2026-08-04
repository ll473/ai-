import asyncio

from backend.app.core.database import SessionLocal, engine
from backend.app.schemas.ai import ModelConfigCreate
from backend.app.services.ai_management import AiManagementService


async def setup_ai() -> None:
    async with SessionLocal() as session:
        service = AiManagementService(session)
        configs = await service.list_model_configs()
        if configs:
            print(f"Model config already exists: {configs[0].name}")
        else:
            config = await service.create_model_config(
                ModelConfigCreate(
                    name="阿里云百炼默认模型",
                    provider="ALIBABA_BAILIAN",
                    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                    chat_model="qwen3.7-plus",
                    embedding_model="qwen3.7-text-embedding",
                    api_key=None,
                    enabled=True,
                    is_default=True,
                )
            )
            print(f"Model config created: {config.name}")
        tools = await service.seed_builtin_tools()
        print(f"Built-in tools ready: {len(tools)}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(setup_ai())
