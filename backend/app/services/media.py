from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.exceptions import AppError, NotFoundError
from backend.app.models.catalog import ProductImage
from backend.app.repositories.catalog import CatalogRepository
from backend.app.schemas.catalog import UploadedImage

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


class MediaService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()
        self.catalog = CatalogRepository(session)

    async def save_product_image(
        self,
        product_id: int,
        file: UploadFile,
        *,
        alt_text: str | None,
        sort_order: int,
    ) -> UploadedImage:
        product = await self.catalog.get_product(product_id)
        if product is None:
            raise NotFoundError("商品不存在")
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise AppError(
                "仅支持 JPG、PNG、WebP 和 GIF 图片",
                code="UNSUPPORTED_IMAGE_TYPE",
                status_code=415,
            )

        max_bytes = self.settings.max_upload_size_mb * 1024 * 1024
        content = await file.read(max_bytes + 1)
        await file.close()
        if len(content) > max_bytes:
            raise AppError(
                f"图片不能超过 {self.settings.max_upload_size_mb} MB",
                code="FILE_TOO_LARGE",
                status_code=413,
            )

        image = ProductImage(
            product_id=product_id,
            image_url="",
            content_type=file.content_type,
            content=content,
            alt_text=alt_text,
            sort_order=sort_order,
        )
        self.session.add(image)
        await self.session.flush()
        image.image_url = f"/api/v1/catalog/images/{image.id}"
        await self.session.commit()
        await self.session.refresh(image)

        if not product.main_image_url:
            product.main_image_url = image.image_url
            await self.session.commit()

        return UploadedImage(
            id=image.id,
            url=image.image_url,
            content_type=file.content_type,
            size=len(content),
        )

    async def get_product_image(self, image_id: int) -> tuple[bytes, str]:
        image = await self.catalog.get_product_image(image_id)
        if image is None or image.content is None:
            raise NotFoundError("商品图片不存在")
        return image.content, image.content_type or "application/octet-stream"
