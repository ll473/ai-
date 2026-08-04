# ruff: noqa: E501

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import SessionLocal, engine
from backend.app.core.security import hash_password
from backend.app.models.ai import KnowledgeDocument, PromptTemplate
from backend.app.models.catalog import Brand, Category, Product, ProductImage, ProductSku
from backend.app.models.enums import (
    DocumentStatus,
    OrderStatus,
    ProductStatus,
    UserRole,
)
from backend.app.models.trade import Order, OrderItem, Review
from backend.app.models.user import User, UserAddress, Wallet

PRODUCTS: list[dict[str, Any]] = [
    {
        "product_no": "DEMO-CHAIR-001",
        "category_slug": "office-efficiency",
        "brand_slug": "aster-living",
        "name": "EonFlex 自适应人体工学椅",
        "subtitle": "动态腰托、4D 扶手与透气网背，为长时间办公提供稳定支撑",
        "image": "/uploads/demo-products/ergonomic-chair.png",
        "min_price": Decimal("1299.00"),
        "max_price": Decimal("1499.00"),
        "rating": Decimal("5.00"),
        "review_count": 1,
        "sales_count": 286,
        "parameters": {
            "材质": "高弹透气网布",
            "腰托": "自适应双区腰托",
            "扶手": "4D 多向调节",
            "承重": "120 kg",
            "保修": "3 年",
        },
        "detail": """## 为久坐设计的动态支撑\n\n椅背随坐姿变化提供连续支撑，双区腰托可独立微调，降低长时间办公时的腰背压力。\n\n### 核心配置\n\n- 4D 扶手与多档头枕\n- 透气网背和高回弹坐垫\n- 坐深、后仰阻尼和椅背高度可调\n- 通过 120 kg 静态承重测试""",
        "skus": [
            ("DEMO-CHAIR-BLACK", "曜石黑标准款", Decimal("1299.00"), 36, {"颜色": "曜石黑", "脚托": "无"}),
            ("DEMO-CHAIR-GRAY", "云雾灰脚托款", Decimal("1499.00"), 18, {"颜色": "云雾灰", "脚托": "有"}),
        ],
    },
    {
        "product_no": "DEMO-KEYBOARD-001",
        "category_slug": "digital-audio",
        "brand_slug": "keynest",
        "name": "KeyNest K75 三模机械键盘",
        "subtitle": "75% 紧凑配列、热插拔轴座与金属旋钮，兼顾办公和游戏",
        "image": "/uploads/demo-products/mechanical-keyboard.png",
        "min_price": Decimal("499.00"),
        "max_price": Decimal("529.00"),
        "rating": Decimal("4.00"),
        "review_count": 1,
        "sales_count": 518,
        "parameters": {
            "连接": "蓝牙 / 2.4G / USB-C",
            "布局": "75% · 82 键",
            "轴座": "全键热插拔",
            "续航": "约 120 小时",
            "系统": "Windows / macOS",
        },
        "detail": """## 桌面空间与输入手感的平衡\n\n保留独立方向键和功能区，同时缩短键盘宽度。Gasket 结构与多层消音材料带来干净、稳定的敲击反馈。\n\n### 使用体验\n\n- 三模连接可快速切换三台设备\n- 全键热插拔，兼容主流机械轴体\n- PBT 键帽耐磨不易打油\n- 旋钮可调节音量和静音""",
        "skus": [
            ("DEMO-K75-WHITE", "暖白线性轴", Decimal("499.00"), 64, {"配色": "暖白", "轴体": "线性轴"}),
            ("DEMO-K75-GRAPHITE", "石墨段落轴", Decimal("529.00"), 42, {"配色": "石墨", "轴体": "段落轴"}),
        ],
    },
    {
        "product_no": "DEMO-HEADPHONE-001",
        "category_slug": "digital-audio",
        "brand_slug": "echoarc",
        "name": "EchoArc H1 自适应降噪耳机",
        "subtitle": "混合主动降噪、空间音频与柔软记忆棉耳罩，通勤办公都安静",
        "image": "/uploads/demo-products/noise-cancelling-headphones.png",
        "min_price": Decimal("899.00"),
        "max_price": Decimal("899.00"),
        "rating": Decimal("5.00"),
        "review_count": 1,
        "sales_count": 342,
        "parameters": {
            "降噪": "混合主动降噪",
            "单元": "40 mm 动圈",
            "续航": "开启降噪 42 小时",
            "连接": "蓝牙 5.4 / 3.5 mm",
            "重量": "248 g",
        },
        "detail": """## 把嘈杂留在耳机之外\n\n多麦克风实时采集环境噪声并自动调整降噪强度，透明模式无需摘下耳机即可自然交流。\n\n### 声音与佩戴\n\n- 40 mm 大尺寸动圈单元\n- 支持多设备同时连接\n- 记忆棉耳罩与轻量头梁\n- 充电 10 分钟可播放约 5 小时""",
        "skus": [
            ("DEMO-H1-NAVY", "深海蓝", Decimal("899.00"), 31, {"颜色": "深海蓝"}),
            ("DEMO-H1-GRAY", "珍珠灰", Decimal("899.00"), 25, {"颜色": "珍珠灰"}),
        ],
    },
    {
        "product_no": "DEMO-COFFEE-001",
        "category_slug": "quality-living",
        "brand_slug": "morrow-home",
        "name": "Morrow 手冲咖啡礼盒套装",
        "subtitle": "细口壶、陶瓷滤杯与耐热玻璃分享壶，一套完成稳定手冲",
        "image": "/uploads/demo-products/pour-over-coffee-set.png",
        "min_price": Decimal("369.00"),
        "max_price": Decimal("399.00"),
        "rating": Decimal("4.80"),
        "review_count": 0,
        "sales_count": 176,
        "parameters": {
            "容量": "分享壶 600 ml",
            "滤杯": "02 号陶瓷滤杯",
            "手冲壶": "不锈钢细口壶 700 ml",
            "材质": "陶瓷 / 高硼硅玻璃 / 胡桃木",
            "适用": "1–4 人",
        },
        "detail": """## 从第一杯开始稳定复现\n\n适合新手的完整手冲组合，细口壶水流容易控制，纵向沟槽滤杯让萃取更均匀。\n\n### 套装包含\n\n- 700 ml 不锈钢细口壶\n- 02 号陶瓷滤杯\n- 600 ml 耐热玻璃分享壶\n- 咖啡量勺与滤纸收纳架""",
        "skus": [
            ("DEMO-COFFEE-WALNUT", "胡桃木经典款", Decimal("369.00"), 28, {"木色": "胡桃木"}),
            ("DEMO-COFFEE-DARK", "深胡桃礼盒款", Decimal("399.00"), 16, {"木色": "深胡桃", "包装": "礼盒"}),
        ],
    },
]


async def get_or_create_category(session: AsyncSession, name: str, slug: str, order: int) -> Category:
    category = await session.scalar(select(Category).where(Category.slug == slug))
    if category is None:
        category = Category(name=name, slug=slug, sort_order=order, enabled=True)
        session.add(category)
        await session.flush()
    return category


async def get_or_create_brand(
    session: AsyncSession, name: str, slug: str, description: str
) -> Brand:
    brand = await session.scalar(select(Brand).where(Brand.slug == slug))
    if brand is None:
        brand = Brand(name=name, slug=slug, description=description, enabled=True)
        session.add(brand)
        await session.flush()
    return brand


async def seed_catalog(session: AsyncSession) -> dict[str, tuple[Product, ProductSku]]:
    categories = {
        "office-efficiency": await get_or_create_category(session, "办公效率", "office-efficiency", 1),
        "digital-audio": await get_or_create_category(session, "数码影音", "digital-audio", 2),
        "quality-living": await get_or_create_category(session, "品质生活", "quality-living", 3),
    }
    brands = {
        "aster-living": await get_or_create_brand(session, "Aster Living", "aster-living", "关注人体工学与现代办公空间。"),
        "keynest": await get_or_create_brand(session, "KeyNest", "keynest", "为高频输入用户打造可靠桌面装备。"),
        "echoarc": await get_or_create_brand(session, "EchoArc", "echoarc", "专注轻量化个人音频体验。"),
        "morrow-home": await get_or_create_brand(session, "Morrow Home", "morrow-home", "把实用器物做得温和耐看。"),
    }
    seeded: dict[str, tuple[Product, ProductSku]] = {}
    for data in PRODUCTS:
        product = await session.scalar(
            select(Product).where(Product.product_no == data["product_no"])
        )
        if product is None:
            product = Product(
                category_id=categories[data["category_slug"]].id,
                brand_id=brands[data["brand_slug"]].id,
                name=data["name"],
                subtitle=data["subtitle"],
                product_no=data["product_no"],
                main_image_url=data["image"],
                detail_markdown=data["detail"],
                parameters=data["parameters"],
                min_price=data["min_price"],
                max_price=data["max_price"],
                rating=data["rating"],
                review_count=data["review_count"],
                sales_count=data["sales_count"],
                status=ProductStatus.ON_SALE,
            )
            session.add(product)
            await session.flush()
        else:
            product.main_image_url = data["image"]
            product.detail_markdown = data["detail"]
            product.parameters = data["parameters"]
            product.status = ProductStatus.ON_SALE
        image = await session.scalar(
            select(ProductImage).where(
                ProductImage.product_id == product.id,
                ProductImage.image_url == data["image"],
            )
        )
        if image is None:
            session.add(
                ProductImage(
                    product_id=product.id,
                    image_url=data["image"],
                    alt_text=f"{product.name}商品图",
                    sort_order=0,
                )
            )
        first_sku: ProductSku | None = None
        for sku_no, name, price, stock, attributes in data["skus"]:
            sku = await session.scalar(select(ProductSku).where(ProductSku.sku_no == sku_no))
            if sku is None:
                sku = ProductSku(
                    product_id=product.id,
                    sku_no=sku_no,
                    name=name,
                    attributes=attributes,
                    price=price,
                    market_price=(price * Decimal("1.18")).quantize(Decimal("0.01")),
                    stock=stock,
                    locked_stock=0,
                    enabled=True,
                )
                session.add(sku)
                await session.flush()
            if first_sku is None:
                first_sku = sku
        if first_sku is None:
            raise RuntimeError(f"Product {product.product_no} has no SKU")
        seeded[product.product_no] = (product, first_sku)
        document = await session.scalar(
            select(KnowledgeDocument).where(
                KnowledgeDocument.product_id == product.id,
                KnowledgeDocument.source_type == "DEMO_PRODUCT",
            )
        )
        if document is None:
            document = KnowledgeDocument(
                title=f"{product.name} · 演示商品资料",
                source_type="DEMO_PRODUCT",
                source_id=str(product.id),
                product_id=product.id,
                content=(
                    f"商品：{product.name}\n副标题：{product.subtitle}\n"
                    f"参数：{product.parameters}\n详情：{product.detail_markdown}"
                ),
                status=DocumentStatus.PENDING,
            )
            session.add(document)
    return seeded


async def seed_trade(session: AsyncSession, products: dict[str, tuple[Product, ProductSku]]) -> None:
    user = await session.scalar(select(User).where(User.username == "demo_buyer"))
    if user is None:
        user = User(
            username="demo_buyer",
            email="demo.buyer@example.com",
            nickname="林小满",
            password_hash=hash_password("Demo@2026Shop!"),
            role=UserRole.USER,
        )
        session.add(user)
        await session.flush()
        session.add(Wallet(user_id=user.id, balance=Decimal("5000.00")))
        session.add(
            UserAddress(
                user_id=user.id,
                receiver_name="林小满",
                receiver_phone="13800000000",
                province="浙江省",
                city="杭州市",
                district="西湖区",
                detail="文三路 88 号演示地址",
                postal_code="310000",
                is_default=True,
            )
        )
    now = datetime.now(UTC)
    order_specs = [
        ("DEMO202608040001", "DEMO-CHAIR-001", Decimal("1299.00"), 5, "腰背支撑很自然，坐了一整天也没有明显疲劳。安装步骤如果能配视频会更好。"),
        ("DEMO202608040002", "DEMO-KEYBOARD-001", Decimal("499.00"), 4, "三台设备切换很方便，键帽触感不错，办公室使用声音也能接受。"),
        ("DEMO202608040003", "DEMO-HEADPHONE-001", Decimal("899.00"), 5, "地铁降噪效果明显，耳罩柔软，连续戴两三个小时没有夹头感。"),
    ]
    for index, (order_no, product_no, amount, rating, review_content) in enumerate(order_specs):
        order = await session.scalar(select(Order).where(Order.order_no == order_no))
        if order is not None:
            continue
        product, sku = products[product_no]
        completed_at = now - timedelta(days=3 - index)
        order = Order(
            order_no=order_no,
            user_id=user.id,
            status=OrderStatus.COMPLETED,
            address_snapshot={
                "receiver_name": "林小满",
                "receiver_phone": "13800000000",
                "full_address": "浙江省杭州市西湖区文三路 88 号演示地址",
            },
            product_amount=amount,
            discount_amount=Decimal("0.00"),
            shipping_amount=Decimal("0.00"),
            payable_amount=amount,
            paid_amount=amount,
            buyer_remark="演示订单",
            paid_at=completed_at - timedelta(hours=2),
            shipped_at=completed_at - timedelta(hours=1),
            completed_at=completed_at,
        )
        session.add(order)
        await session.flush()
        order_item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            sku_id=sku.id,
            product_name=product.name,
            sku_name=sku.name,
            sku_attributes=sku.attributes,
            image_url=product.main_image_url,
            unit_price=amount,
            quantity=1,
            total_amount=amount,
        )
        session.add(order_item)
        await session.flush()
        session.add(
            Review(
                user_id=user.id,
                product_id=product.id,
                order_item_id=order_item.id,
                rating=rating,
                content=review_content,
                image_urls=None,
                anonymous=False,
                visible=True,
            )
        )


async def seed_prompts(session: AsyncSession) -> None:
    prompts = [
        (
            "DEMO_SHOPPING_GUIDE",
            "演示导购 Prompt",
            "SHOPPING_GUIDE",
            """你是商城智能导购，必须使用工具查询真实商品、价格和库存。
把“预算 N 元”理解为最高可接受价格，优先用 max_price=N 且不设置 min_price；除非用户明确给出最低价或区间。
先用用户明确提到的商品类型或核心关键词搜索，不要先搜“热门”，不要擅自切换到无关品类。
首次无结果时只放宽一次关键词或价格限制，通常最多搜索三次。找到合适商品后调用 submit_recommendation，回答简洁并说明推荐依据。""",
        ),
        ("DEMO_REVIEW_ANALYSIS", "演示评价分析 Prompt", "REVIEW_ANALYSIS", "你是电商评价分析师，只根据真实评价输出 JSON，不得虚构；缺少证据的类别返回空数组。"),
        ("DEMO_OPERATIONS_REPORT", "演示运营报告 Prompt", "OPERATIONS_REPORT", "你是电商运营负责人，只根据真实指标快照生成中文 Markdown 报告，不得改写或补造指标。"),
    ]
    for code, name, scene, system_prompt in prompts:
        existing = await session.scalar(
            select(PromptTemplate).where(PromptTemplate.code == code, PromptTemplate.version == 1)
        )
        if existing is None:
            session.add(
                PromptTemplate(
                    code=code,
                    name=name,
                    scene=scene,
                    version=1,
                    system_prompt=system_prompt,
                    enabled=True,
                )
            )
        else:
            existing.name = name
            existing.scene = scene
            existing.system_prompt = system_prompt
            existing.enabled = True


async def seed_demo() -> None:
    async with SessionLocal() as session:
        products = await seed_catalog(session)
        await seed_trade(session, products)
        await seed_prompts(session)
        await session.commit()
        print("Demo data ready: 3 categories, 4 brands, 4 products, 8 SKUs, 3 orders")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_demo())
