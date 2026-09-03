"""数据库模型与生命周期。"""

from pathlib import Path

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

    __tablename__ = "user_data"

    user_ref: Mapped[str] = mapped_column(String, primary_key=True)
    user_namespace: Mapped[str] = mapped_column(String, index=True)
    jj_length: Mapped[float]
    last_masturbation_time: Mapped[int] = mapped_column(default=0)
    win_probability: Mapped[float] = mapped_column(default=0.5)
    is_challenging: Mapped[bool] = mapped_column(default=False)
    challenge_completed: Mapped[bool] = mapped_column(default=False)
    is_near_zero: Mapped[bool] = mapped_column(default=False)
    is_zero_or_neg: Mapped[bool] = mapped_column(default=False)


class SceneData(Base):
    """场景开关数据表"""

    __tablename__ = "scene_data"

    scene_ref: Mapped[str] = mapped_column(String, primary_key=True)
    scene_namespace: Mapped[str] = mapped_column(String, index=True)
    scene_type: Mapped[str] = mapped_column(String, index=True)
    allow: Mapped[bool]


class EjaculationData(Base):
    """被注入数据表"""

    __tablename__ = "ejaculation_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_ref: Mapped[str] = mapped_column(String, index=True)
    date: Mapped[str] = mapped_column(String(20))
    volume: Mapped[float]


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
