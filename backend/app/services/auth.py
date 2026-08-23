from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import AuthenticationError, ConflictError
from backend.app.core.security import create_access_token, hash_password, verify_password
from backend.app.models.enums import UserStatus
from backend.app.models.user import User, Wallet
from backend.app.repositories.user import UserRepository
from backend.app.schemas.auth import (
    LoginRequest,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    RegisterRequest,
)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def register(self, payload: RegisterRequest) -> User:
        if await self.users.get_by_username(payload.username):
            raise ConflictError("用户名已存在")
        if payload.email and await self.users.email_exists(payload.email):
            raise ConflictError("邮箱已被注册")
        if payload.phone and await self.users.phone_exists(payload.phone):
            raise ConflictError("手机号已被注册")

        user = User(
            username=payload.username,
            password_hash=hash_password(payload.password),
            email=payload.email,
            phone=payload.phone,
            nickname=payload.nickname or payload.username,
        )
        self.users.add(user)
        await self.session.flush()
        self.session.add(Wallet(user_id=user.id))
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def authenticate(self, payload: LoginRequest) -> tuple[User, str]:
        user = await self.users.get_by_account(payload.account)
        if user is None or not verify_password(payload.password, user.password_hash):
            raise AuthenticationError("账号或密码错误")
        if user.status != UserStatus.ACTIVE:
            raise AuthenticationError("账号已被禁用")

        token = create_access_token(str(user.id), extra={"role": str(user.role)})
        return user, token

    async def update_profile(self, user: User, payload: ProfileUpdateRequest) -> User:
        if payload.email and await self.users.email_exists(payload.email, exclude_id=user.id):
            raise ConflictError("邮箱已被其他账号使用")
        if payload.phone and await self.users.phone_exists(payload.phone, exclude_id=user.id):
            raise ConflictError("手机号已被其他账号使用")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def change_password(self, user: User, payload: PasswordChangeRequest) -> None:
        if not verify_password(payload.current_password, user.password_hash):
            raise AuthenticationError("当前密码不正确")
        if verify_password(payload.new_password, user.password_hash):
            raise ConflictError("新密码不能与当前密码相同")
        user.password_hash = hash_password(payload.new_password)
        await self.session.commit()
