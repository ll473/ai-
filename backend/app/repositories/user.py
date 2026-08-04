from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_username(self, username: str) -> User | None:
        result = await self.session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_account(self, account: str) -> User | None:
        result = await self.session.execute(
            select(User).where(
                or_(
                    User.username == account,
                    User.email == account,
                    User.phone == account,
                )
            )
        )
        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        result = await self.session.execute(select(User.id).where(User.email == email).limit(1))
        return result.scalar_one_or_none() is not None

    async def phone_exists(self, phone: str) -> bool:
        result = await self.session.execute(select(User.id).where(User.phone == phone).limit(1))
        return result.scalar_one_or_none() is not None

    def add(self, user: User) -> None:
        self.session.add(user)

