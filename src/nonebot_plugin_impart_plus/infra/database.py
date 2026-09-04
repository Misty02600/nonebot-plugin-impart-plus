"""NoneBot ORM 数据模型。"""

from typing import ClassVar

from nonebot_plugin_orm import Model
from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

# Ref 与日期按 utf8mb4 计算最多占 1100 字节，低于 MySQL 8 的 3072 字节索引上限。
PERSISTED_REF_MAX_LENGTH = 255
PERSISTED_NAMESPACE_MAX_LENGTH = 128
SCENE_TYPE_MAX_LENGTH = 32


class UserData(Model):
    """用户数据表"""

    __bind_key__: ClassVar[str] = ""

    user_ref: Mapped[str] = mapped_column(
        String(PERSISTED_REF_MAX_LENGTH),
        primary_key=True,
    )
    user_namespace: Mapped[str] = mapped_column(
        String(PERSISTED_NAMESPACE_MAX_LENGTH),
        index=True,
    )
    jj_length: Mapped[float]
    win_probability: Mapped[float] = mapped_column(default=0.5)
    is_challenging: Mapped[bool] = mapped_column(default=False)
    challenge_completed: Mapped[bool] = mapped_column(default=False)
    is_near_zero: Mapped[bool] = mapped_column(default=False)
    is_zero_or_neg: Mapped[bool] = mapped_column(default=False)


class SceneData(Model):
    """场景开关数据表"""

    __bind_key__: ClassVar[str] = ""

    scene_ref: Mapped[str] = mapped_column(
        String(PERSISTED_REF_MAX_LENGTH),
        primary_key=True,
    )
    scene_namespace: Mapped[str] = mapped_column(
        String(PERSISTED_NAMESPACE_MAX_LENGTH),
        index=True,
    )
    scene_type: Mapped[str] = mapped_column(String(SCENE_TYPE_MAX_LENGTH), index=True)
    allow: Mapped[bool]


class EjaculationData(Model):
    """被注入数据表"""

    __bind_key__: ClassVar[str] = ""
    __table_args__ = (UniqueConstraint("user_ref", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_ref: Mapped[str] = mapped_column(String(PERSISTED_REF_MAX_LENGTH), index=True)
    date: Mapped[str] = mapped_column(String(20))
    volume: Mapped[float]
