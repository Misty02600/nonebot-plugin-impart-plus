"""ORM 数据模型

定义数据库表结构，不包含业务逻辑。使用 SQLAlchemy 2.0 Mapped 类型注解。
"""

from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """ORM 基类"""


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
    """注入数据表"""

    __tablename__ = "ejaculation_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    userid: Mapped[int] = mapped_column(index=True)
    date: Mapped[str] = mapped_column(String(20))
    volume: Mapped[float]
