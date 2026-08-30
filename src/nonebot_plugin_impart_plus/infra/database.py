"""数据库模型与生命周期。"""

from pathlib import Path

import sqlalchemy as sa
from nonebot import require
from sqlalchemy import String
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

DATA_PATH: Path = store.get_plugin_data_dir()

engine = create_async_engine(f"sqlite+aiosqlite:///{DATA_PATH}/impart.db")
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class UserData(Base):
    """用户数据表"""

    __tablename__ = "userdata"

    userid: Mapped[int] = mapped_column(primary_key=True, index=True)
    jj_length: Mapped[float]
    last_masturbation_time: Mapped[int] = mapped_column(default=0)
    win_probability: Mapped[float] = mapped_column(default=0.5)
    is_challenging: Mapped[bool] = mapped_column(default=False)
    challenge_completed: Mapped[bool] = mapped_column(default=False)
    is_near_zero: Mapped[bool] = mapped_column(default=False)
    is_zero_or_neg: Mapped[bool] = mapped_column(default=False)


class GroupData(Base):
    """群数据表"""

    __tablename__ = "groupdata"

    groupid: Mapped[int] = mapped_column(primary_key=True, index=True)
    allow: Mapped[bool]


class EjaculationData(Base):
    """被注入数据表"""

    __tablename__ = "ejaculation_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    userid: Mapped[int] = mapped_column(index=True)
    date: Mapped[str] = mapped_column(String(20))
    volume: Mapped[float]


async def check_and_add_column():
    """检查是否存在win_probability、is_challenging、challenge_completed列, 若无则添加"""
    async with engine.begin() as conn:
        result = await conn.execute(sa.text("PRAGMA table_info(userdata)"))
        columns = [row[1] for row in result]
        if "win_probability" not in columns:
            await conn.execute(
                sa.text(
                    "ALTER TABLE userdata ADD COLUMN win_probability FLOAT DEFAULT 0.5"
                )
            )
        if "is_challenging" not in columns:
            await conn.execute(
                sa.text(
                    "ALTER TABLE userdata ADD COLUMN is_challenging BOOLEAN DEFAULT FALSE"
                )
            )
        if "challenge_completed" not in columns:
            await conn.execute(
                sa.text(
                    "ALTER TABLE userdata ADD COLUMN challenge_completed BOOLEAN DEFAULT FALSE"
                )
            )
        if "is_near_zero" not in columns:
            await conn.execute(
                sa.text(
                    "ALTER TABLE userdata ADD COLUMN is_near_zero BOOLEAN DEFAULT FALSE"
                )
            )
        if "is_zero_or_neg" not in columns:
            await conn.execute(
                sa.text(
                    "ALTER TABLE userdata ADD COLUMN is_zero_or_neg BOOLEAN DEFAULT FALSE"
                )
            )


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await check_and_add_column()
