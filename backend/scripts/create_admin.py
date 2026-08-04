import argparse
import asyncio
from getpass import getpass

from sqlalchemy import select

from backend.app.core.database import SessionLocal, engine
from backend.app.core.security import hash_password
from backend.app.models.enums import UserRole
from backend.app.models.user import User, Wallet


async def create_admin(username: str, password: str) -> None:
    async with SessionLocal() as session:
        existing = await session.scalar(select(User).where(User.username == username))
        if existing:
            raise SystemExit(f"User '{username}' already exists")
        admin = User(
            username=username,
            nickname="系统管理员",
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
        )
        session.add(admin)
        await session.flush()
        session.add(Wallet(user_id=admin.id))
        await session.commit()
    await engine.dispose()
    print(f"Admin '{username}' created")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the first administrator")
    parser.add_argument("username")
    args = parser.parse_args()
    password = getpass("Password: ")
    if len(password) < 8:
        raise SystemExit("Password must contain at least 8 characters")
    asyncio.run(create_admin(args.username, password))


if __name__ == "__main__":
    main()

