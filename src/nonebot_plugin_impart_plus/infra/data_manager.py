"""数据访问与现有状态更新流程。"""

import random
import time

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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

            jj_length = user.jj_length
            is_challenging = user.is_challenging
            challenge_completed = user.challenge_completed
            is_near_zero = user.is_near_zero
            is_zero_or_neg = user.is_zero_or_neg
            response = ""

            if not is_challenging and not challenge_completed and 25 <= jj_length < 30:
                user.is_challenging = True
                user.win_probability *= 0.8
                response = "challenge_started_low_win"
            elif not is_challenging and not challenge_completed and jj_length >= 30:
                user.challenge_completed = True
                response = "challenge_completed"
            elif is_challenging and not challenge_completed and jj_length < 25:
                user.win_probability *= 1.25
                user.jj_length -= 5
                user.is_challenging = False
                response = "challenge_failed_high_win"
            elif is_challenging and not challenge_completed and jj_length >= 30:
                user.win_probability *= 1.25
                user.is_challenging = False
                user.challenge_completed = True
                response = "challenge_success_high_win"
            elif is_challenging and 25 <= jj_length < 30:
                response = "is_challenging"
            elif challenge_completed and 25 <= jj_length < 30:
                response = "challenge_completed"
            elif challenge_completed and jj_length < 25:
                user.jj_length -= 5
                user.challenge_completed = False
                response = "challenge_completed_reduce"
            elif not is_near_zero and 0 < jj_length <= 5:
                user.is_near_zero = True
                response = "length_near_zero"
            elif is_near_zero and (jj_length <= 0 or jj_length > 5):
                user.is_near_zero = False
            elif not is_zero_or_neg and jj_length <= 0:
                user.is_zero_or_neg = True
                response = "length_zero_or_negative"
            elif is_zero_or_neg and jj_length > 0:
                user.is_zero_or_neg = False

            await session.commit()
            return response

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
