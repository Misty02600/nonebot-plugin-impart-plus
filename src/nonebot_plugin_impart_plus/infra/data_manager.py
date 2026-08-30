"""数据访问与现有状态更新流程。"""

import random
import time

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..impart.core import UserGameState, evaluate_user_state
from .database import EjaculationData, GroupData, UserData


class DataManager:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def update_challenge_status(self, userid: int) -> str:
        """根据用户的jj_length、is_challenging和challenge_completed状态更新用户的挑战状态和胜率"""
        async with self._session_factory() as session:
            result = await session.execute(
                select(UserData).where(UserData.userid == userid)
            )
            user = result.scalar()
            if not user:
                return "user_not_found"

            evaluation = evaluate_user_state(
                UserGameState(
                    length=user.jj_length,
                    win_probability=user.win_probability,
                    is_challenging=user.is_challenging,
                    challenge_completed=user.challenge_completed,
                    is_near_zero=user.is_near_zero,
                    is_zero_or_negative=user.is_zero_or_neg,
                )
            )
            state = evaluation.state
            user.jj_length = state.length
            user.win_probability = state.win_probability
            user.is_challenging = state.is_challenging
            user.challenge_completed = state.challenge_completed
            user.is_near_zero = state.is_near_zero
            user.is_zero_or_neg = state.is_zero_or_negative

            await session.commit()
            return evaluation.status

    async def is_in_table(self, userid: int) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(
                select(UserData).filter(UserData.userid == userid)
            )
            return bool(result.scalar())

    async def add_new_user(self, userid: int) -> None:
        """插入一个新用户, 默认长度是10.0"""
        async with self._session_factory() as session:
            session.add(
                UserData(
                    userid=userid,
                    jj_length=10.0,
                    last_masturbation_time=int(time.time()),
                    win_probability=0.5,
                )
            )
            await session.commit()

    async def update_activity(self, userid: int) -> None:
        """更新用户活跃时间"""
        if not await self.is_in_table(userid):
            await self.add_new_user(userid)
        async with self._session_factory() as session:
            await session.execute(
                update(UserData)
                .where(UserData.userid == userid)
                .values(last_masturbation_time=int(time.time()))
            )
            await session.commit()

    async def get_jj_length(self, userid: int) -> float:
        """传入用户id, 返还数据库中对应的jj长度"""
        async with self._session_factory() as session:
            result = await session.execute(
                select(UserData.jj_length).filter(UserData.userid == userid)
            )
            return result.scalar() or 0.0

    async def set_jj_length(self, userid: int, length: float) -> None:
        """传入一个用户id以及需要增加的长度, 在数据库内累加, 用这个函数前一定要先判断用户是否在表中"""
        async with self._session_factory() as session:
            current_length = await self.get_jj_length(userid)
            await session.execute(
                update(UserData)
                .where(UserData.userid == userid)
                .values(
                    jj_length=round(current_length + length, 3),
                    last_masturbation_time=int(time.time()),
                )
            )
            await session.commit()

    async def get_win_probability(self, userid: int) -> float:
        """传入用户id, 返还数据库中对应的获胜概率"""
        async with self._session_factory() as session:
            result = await session.execute(
                select(UserData.win_probability).filter(UserData.userid == userid)
            )
            return result.scalar() or 0.5

    async def set_win_probability(
        self,
        userid: int,
        probability_change: float,
    ) -> None:
        """传入一个用户id以及需要增加的获胜率, 在数据库内累加, 用这个函数前一定要先判断用户是否在表中"""
        async with self._session_factory() as session:
            current_probability = await self.get_win_probability(userid)
            await session.execute(
                update(UserData)
                .where(UserData.userid == userid)
                .values(
                    win_probability=round(
                        current_probability + probability_change,
                        3,
                    ),
                    last_masturbation_time=int(time.time()),
                )
            )
            await session.commit()

    async def check_group_allow(self, groupid: int) -> bool:
        """检查群是否允许, 传入群号, 类型是int"""
        async with self._session_factory() as session:
            result = await session.execute(
                select(GroupData.allow).filter(GroupData.groupid == groupid)
            )
            return result.scalar() or False

    async def set_group_allow(self, groupid: int, allow: bool) -> None:
        """设置群聊开启或者禁止银趴, 传入群号, 类型是int, 以及allow, 类型是bool"""
        async with self._session_factory() as session:
            result = await session.execute(
                select(GroupData).where(GroupData.groupid == groupid)
            )
            existing_group = result.scalar_one_or_none()
            if existing_group is None:
                session.add(GroupData(groupid=groupid, allow=allow))
            else:
                existing_group.allow = allow
            await session.commit()

    @staticmethod
    def get_today() -> str:
        """获取当前年月日格式: 2024-10-20"""
        return time.strftime("%Y-%m-%d", time.localtime())

    async def insert_ejaculation(self, userid: int, volume: float) -> None:
        """插入一条注入的记录"""
        now_date = self.get_today()
        async with self._session_factory() as session:
            result = await session.execute(
                select(EjaculationData.volume).filter(
                    EjaculationData.userid == userid,
                    EjaculationData.date == now_date,
                )
            )
            current_volume = result.scalar()
            if current_volume is not None:
                await session.execute(
                    update(EjaculationData)
                    .where(
                        EjaculationData.userid == userid,
                        EjaculationData.date == now_date,
                    )
                    .values(volume=round(current_volume + volume, 3))
                )
            else:
                session.add(
                    EjaculationData(userid=userid, date=now_date, volume=volume)
                )
            await session.commit()

    async def get_ejaculation_data(self, userid: int) -> list[dict]:
        """获取一个用户的所有注入记录"""
        async with self._session_factory() as session:
            result = await session.execute(
                select(EjaculationData).filter(EjaculationData.userid == userid)
            )
            return [
                {"date": row.date, "volume": row.volume} for row in result.scalars()
            ]

    async def get_today_ejaculation_data(self, userid: int) -> float:
        """获取用户当日的注入量"""
        async with self._session_factory() as session:
            result = await session.execute(
                select(EjaculationData.volume).filter(
                    EjaculationData.userid == userid,
                    EjaculationData.date == self.get_today(),
                )
            )
            return result.scalar() or 0.0

    async def punish_all_inactive_users(self) -> None:
        """所有不活跃的用户, 即上次打胶时间超过一天的用户, 所有jj_length大于1将受到减少0--1随机的惩罚"""
        async with self._session_factory() as session:
            result = await session.execute(
                select(UserData).filter(
                    UserData.last_masturbation_time < (time.time() - 86400),
                    UserData.jj_length > 1,
                )
            )
            for user in result.scalars():
                user.jj_length = round(user.jj_length - random.random(), 3)
            await session.commit()

    async def get_sorted(self) -> list[dict]:
        """获取所有用户的jj长度, 并且按照从大到小排序"""
        async with self._session_factory() as session:
            result = await session.execute(
                select(UserData).order_by(UserData.jj_length.desc())
            )
            return [
                {"userid": user.userid, "jj_length": user.jj_length}
                for user in result.scalars()
            ]
