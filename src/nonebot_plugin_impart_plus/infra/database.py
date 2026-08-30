"""数据库引擎和会话工厂

提供全局 engine 和 async_session_factory，以及数据库初始化。
"""

from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..core.models import Base


def create_engine(db_path: Path):
    """创建异步引擎"""
    return create_async_engine(f"sqlite+aiosqlite:///{db_path}")


def create_session_factory(engine) -> async_sessionmaker[AsyncSession]:
    """创建异步会话工厂"""
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_db(engine) -> None:
    """初始化数据库：建表 + 迁移旧列"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _check_and_add_columns(engine)


async def _check_and_add_columns(engine) -> None:
    """检查并添加缺失的列（兼容旧数据库）"""
    migrations: list[tuple[str, str]] = [
        (
            "win_probability",
            "ALTER TABLE userdata ADD COLUMN win_probability FLOAT DEFAULT 0.5",
        ),
        (
            "is_challenging",
            "ALTER TABLE userdata ADD COLUMN is_challenging BOOLEAN DEFAULT FALSE",
        ),
        (
            "challenge_completed",
            "ALTER TABLE userdata ADD COLUMN challenge_completed BOOLEAN DEFAULT FALSE",
        ),
        (
            "is_near_zero",
            "ALTER TABLE userdata ADD COLUMN is_near_zero BOOLEAN DEFAULT FALSE",
        ),
        (
            "is_zero_or_neg",
            "ALTER TABLE userdata ADD COLUMN is_zero_or_neg BOOLEAN DEFAULT FALSE",
        ),
    ]
    async with engine.begin() as conn:
        result = await conn.execute(sa.text("PRAGMA table_info(userdata)"))
        existing_columns = {row[1] for row in result}
        for col_name, sql in migrations:
            if col_name not in existing_columns:
                await conn.execute(sa.text(sql))
