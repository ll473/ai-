from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, IdMixin, TimestampMixin
from backend.app.models.enums import UserRole, UserStatus, WalletTransactionType


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(30), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    nickname: Mapped[str | None] = mapped_column(String(80))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    role: Mapped[UserRole] = mapped_column(String(20), default=UserRole.USER, index=True)
    status: Mapped[UserStatus] = mapped_column(String(20), default=UserStatus.ACTIVE, index=True)


class UserAddress(IdMixin, TimestampMixin, Base):
    __tablename__ = "user_addresses"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    receiver_name: Mapped[str] = mapped_column(String(80))
    receiver_phone: Mapped[str] = mapped_column(String(30))
    province: Mapped[str] = mapped_column(String(80))
    city: Mapped[str] = mapped_column(String(80))
    district: Mapped[str] = mapped_column(String(80))
    detail: Mapped[str] = mapped_column(String(255))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class Wallet(IdMixin, TimestampMixin, Base):
    __tablename__ = "wallets"
    __table_args__ = (UniqueConstraint("user_id"),)

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    version: Mapped[int] = mapped_column(default=0, comment="Optimistic lock version")


class WalletTransaction(IdMixin, TimestampMixin, Base):
    __tablename__ = "wallet_transactions"

    wallet_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("wallets.id"), index=True)
    transaction_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    transaction_type: Mapped[WalletTransactionType] = mapped_column(String(20), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    balance_before: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    balance_after: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    reference_type: Mapped[str | None] = mapped_column(String(40))
    reference_id: Mapped[str | None] = mapped_column(String(64), index=True)
    remark: Mapped[str | None] = mapped_column(Text)

