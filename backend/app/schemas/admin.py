from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.enums import UserStatus


class AdminUserStatusUpdate(BaseModel):
    status: UserStatus


class AfterSaleRuleBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category_id: int | None = Field(default=None, ge=1)
    rule_type: str = Field(min_length=1, max_length=40)
    keywords: list[str] | None = None
    content: str = Field(min_length=1, max_length=10000)
    priority: int = Field(default=0, ge=0)
    enabled: bool = True


class AfterSaleRuleCreate(AfterSaleRuleBase):
    pass


class AfterSaleRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    category_id: int | None = Field(default=None, ge=1)
    rule_type: str | None = Field(default=None, min_length=1, max_length=40)
    keywords: list[str] | None = None
    content: str | None = Field(default=None, min_length=1, max_length=10000)
    priority: int | None = Field(default=None, ge=0)
    enabled: bool | None = None


class AfterSaleRulePublic(AfterSaleRuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
