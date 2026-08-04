import asyncio

from sqlalchemy import select

from backend.app.core.database import SessionLocal, engine
from backend.app.models.trade import AfterSaleRule

DEFAULT_RULES = [
    {
        "name": "七天无理由退货规则",
        "rule_type": "RETURN",
        "keywords": ["七天无理由", "退货", "不喜欢"],
        "content": (
            "商品完好且不影响二次销售时，可在签收后 7 天内申请退货；"
            "审核通过后请按页面指引寄回。"
        ),
        "priority": 100,
    },
    {
        "name": "数码商品质量问题换货规则",
        "rule_type": "EXCHANGE",
        "keywords": ["质量问题", "故障", "换货"],
        "content": "数码商品出现非人为质量问题时，可提交故障说明与图片；审核通过后安排换货。",
        "priority": 90,
    },
    {
        "name": "家电商品质保维修规则",
        "rule_type": "WARRANTY",
        "keywords": ["保修", "维修", "家电"],
        "content": "质保期内的非人为故障可申请维修，具体期限与范围以商品详情和品牌官方政策为准。",
        "priority": 80,
    },
    {
        "name": "未发货订单退款规则",
        "rule_type": "REFUND",
        "keywords": ["取消订单", "未发货", "退款"],
        "content": "已支付但尚未发货的订单可申请取消，审核通过后退款原路返回或退回商城钱包。",
        "priority": 70,
    },
    {
        "name": "物流异常处理规则",
        "rule_type": "LOGISTICS",
        "keywords": ["物流异常", "未更新", "破损", "丢失"],
        "content": (
            "物流长时间未更新、签收异常或包装破损时，请提交订单信息，"
            "客服将在 1 个工作日内反馈处理结果。"
        ),
        "priority": 60,
    },
]


async def seed_after_sale_rules() -> None:
    async with SessionLocal() as session:
        for payload in DEFAULT_RULES:
            existing = await session.scalar(
                select(AfterSaleRule).where(AfterSaleRule.name == payload["name"])
            )
            if existing is None:
                session.add(AfterSaleRule(category_id=None, enabled=True, **payload))
        await session.commit()
    await engine.dispose()
    print("Default after-sale rules ready")


if __name__ == "__main__":
    asyncio.run(seed_after_sale_rules())
