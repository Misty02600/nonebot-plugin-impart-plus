"""数据持久化管理器

封装所有数据库 CRUD 操作，类似 jm 插件的 DataManager。
"""

from __future__ import annotations

import random
import time

from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..core.game import ChallengeStatus, ChallengeUpdate, evaluate_challenge
from ..core.models import EjaculationData, GroupData, UserData


class DataManager:
    """插件数据管理器

    职责：
    - 用户数据增删改查
    - 群配置管理
    - 注入记录管理
    - 挑战状态更新
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    # region 用户管理

    async def is_in_table(self, userid: int) -> bool:
        """检查用户是否存在"""
        async with self._session_factory() as s:
            result = await s.execute(select(UserData).where(UserData.userid == userid))
            return result.scalar() is not None

    async def add_new_user(self, userid: int) -> None:
        """插入新用户，默认长度 10.0"""
        async with self._session_factory() as s:
            s.add(
                UserData(
                    userid=userid,
                    jj_length=10.0,
                    last_masturbation_time=int(time.time()),
                    win_probability=0.5,
                )
            )
            await s.commit()

    async def ensure_user(self, userid: int) -> bool:
        """确保用户存在，不存在则创建

        Returns:
            bool: True 表示用户已存在，False 表示新创建
        """
        if await self.is_in_table(userid):
            return True
        await self.add_new_user(userid)
        return False

    async def update_activity(self, userid: int) -> None:
        """更新用户活跃时间"""
        if not await self.is_in_table(userid):
            await self.add_new_user(userid)
        async with self._session_factory() as s:
            await s.execute(
                update(UserData)
                .where(UserData.userid == userid)
                .values(last_masturbation_time=int(time.time()))
            )
            await s.commit()

    # endregion

    # region 长度操作

    async def get_jj_length(self, userid: int) -> float:
        """获取用户的 jj 长度"""
        async with self._session_factory() as s:
            result = await s.execute(
                select(UserData.jj_length).filter(UserData.userid == userid)
            )
            return result.scalar() or 0.0

    async def set_jj_length(self, userid: int, delta: float) -> None:
        """原子累加用户的 jj 长度（结果不会为零）"""
        async with self._session_factory() as s:
            new_val = func.round(UserData.jj_length + delta, 3)
            safe_val = case((new_val == 0.0, -0.01), else_=new_val)
            await s.execute(
                update(UserData)
                .where(UserData.userid == userid)
                .values(
                    jj_length=safe_val,
                    last_masturbation_time=int(time.time()),
                )
            )
            await s.commit()

    async def set_jj_length_absolute(self, userid: int, value: float) -> None:
        """设置用户 jj 长度为精确值（非增量，结果不会为零）

        Args:
            userid: 用户 ID
            value: 目标长度值
        """
        safe_value = round(value, 3)
        if safe_value == 0.0:
            safe_value = -0.01
        async with self._session_factory() as s:
            await s.execute(
                update(UserData)
                .where(UserData.userid == userid)
                .values(
                    jj_length=safe_value,
                    last_masturbation_time=int(time.time()),
                )
            )
            await s.commit()

    # endregion

    # region 胜率操作

    async def get_win_probability(self, userid: int) -> float:
        """获取用户获胜概率"""
        async with self._session_factory() as s:
            result = await s.execute(
                select(UserData.win_probability).filter(UserData.userid == userid)
            )
            return result.scalar() or 0.5

    async def set_win_probability(self, userid: int, delta: float) -> None:
        """原子累加用户获胜概率"""
        async with self._session_factory() as s:
            await s.execute(
                update(UserData)
                .where(UserData.userid == userid)
                .values(
                    win_probability=func.round(UserData.win_probability + delta, 3),
                    last_masturbation_time=int(time.time()),
                )
            )
            await s.commit()

    # endregion

    # region 挑战状态

    async def update_challenge_status(self, userid: int) -> str:
        """评估并更新用户挑战状态

        Returns:
            str: 本次状态变化类型（ChallengeStatus 的值）
        """
        async with self._session_factory() as s:
            result = await s.execute(select(UserData).where(UserData.userid == userid))
            user = result.scalar()
            if not user:
                return ChallengeStatus.NONE

            change = evaluate_challenge(
                jj_length=user.jj_length,
                is_challenging=user.is_challenging,
                challenge_completed=user.challenge_completed,
                is_near_zero=user.is_near_zero,
                is_zero_or_neg=user.is_zero_or_neg,
            )
            self._apply_challenge_update(user, change)

            await s.commit()
            return change.status

    async def execute_pk(
        self,
        winner_id: int,
        loser_id: int,
        length_gain: float,
        length_loss: float,
        winner_prob_delta: float = -0.01,
        loser_prob_delta: float = 0.01,
    ) -> tuple[str, str]:
        """在单事务中执行一次完整的 PK 数据更新

        原子地更新双方的长度、胜率和挑战状态，避免部分提交。

        Args:
            winner_id: 赢家 ID。
            loser_id: 输家 ID。
            length_gain: 赢家长度变化量（正值 PK 为正，负值 PK 为负）。
            length_loss: 输家长度损失量（execute_pk 内部用 ``-length_loss``）。
            winner_prob_delta: 赢家胜率变化量（默认 -0.01，新系统由 calc_win_rate_delta 计算）。
            loser_prob_delta: 输家胜率变化量（默认 +0.01，新系统由 calc_win_rate_delta 计算）。

        Returns:
            tuple[str, str]: (winner_challenge_status, loser_challenge_status)
        """
        async with self._session_factory() as s:
            # 原子更新胜率（使用 CASE 确保长度不为零）
            winner_new = func.round(UserData.jj_length + length_gain, 3)
            safe_winner = case((winner_new == 0.0, -0.01), else_=winner_new)
            await s.execute(
                update(UserData)
                .where(UserData.userid == winner_id)
                .values(
                    win_probability=func.round(
                        UserData.win_probability + winner_prob_delta, 6
                    ),
                    jj_length=safe_winner,
                    last_masturbation_time=int(time.time()),
                )
            )
            loser_new = func.round(UserData.jj_length - length_loss, 3)
            safe_loser = case((loser_new == 0.0, -0.01), else_=loser_new)
            await s.execute(
                update(UserData)
                .where(UserData.userid == loser_id)
                .values(
                    win_probability=func.round(
                        UserData.win_probability + loser_prob_delta, 6
                    ),
                    jj_length=safe_loser,
                    last_masturbation_time=int(time.time()),
                )
            )

            # 评估挑战状态（在同一 session 中）
            winner_status = await self._evaluate_and_apply_challenge(s, winner_id)
            loser_status = await self._evaluate_and_apply_challenge(s, loser_id)

            await s.commit()
            return winner_status, loser_status

    async def _evaluate_and_apply_challenge(
        self, session: AsyncSession, userid: int
    ) -> str:
        """在给定 session 中评估并应用挑战状态（不提交）"""
        result = await session.execute(
            select(UserData).where(UserData.userid == userid)
        )
        user = result.scalar()
        if not user:
            return ChallengeStatus.NONE

        change = evaluate_challenge(
            jj_length=user.jj_length,
            is_challenging=user.is_challenging,
            challenge_completed=user.challenge_completed,
            is_near_zero=user.is_near_zero,
            is_zero_or_neg=user.is_zero_or_neg,
        )
        self._apply_challenge_update(user, change)

        return change.status

    @staticmethod
    def _apply_challenge_update(user: UserData, change: ChallengeUpdate) -> None:
        """将挑战评估结果应用到 ORM 实体（不提交）。"""
        if change.length_delta != 0:
            user.jj_length = round(user.jj_length + change.length_delta, 3)
            if user.jj_length == 0.0:
                user.jj_length = -0.01
        if change.probability_factor != 1.0:
            user.win_probability = round(
                user.win_probability * change.probability_factor, 3
            )
        if change.set_challenging is not None:
            user.is_challenging = change.set_challenging
        if change.set_completed is not None:
            user.challenge_completed = change.set_completed
        if change.set_near_zero is not None:
            user.is_near_zero = change.set_near_zero
        if change.set_zero_or_neg is not None:
            user.is_zero_or_neg = change.set_zero_or_neg

    # endregion

    # region 群管理

    async def check_group_allow(self, groupid: int) -> bool:
        """检查群是否允许使用"""
        async with self._session_factory() as s:
            result = await s.execute(
                select(GroupData.allow).filter(GroupData.groupid == groupid)
            )
            return result.scalar() or False

    async def set_group_allow(self, groupid: int, *, allow: bool) -> None:
        """设置群开关"""
        async with self._session_factory() as s:
            result = await s.execute(
                select(GroupData).where(GroupData.groupid == groupid)
            )
            existing = result.scalar_one_or_none()
            if existing is None:
                s.add(GroupData(groupid=groupid, allow=allow))
            else:
                existing.allow = allow
            await s.commit()

    # endregion

    # region 注入数据

    async def insert_ejaculation(self, userid: int, volume: float) -> None:
        """插入或原子累加当日注入记录"""
        now_date = time.strftime("%Y-%m-%d", time.localtime())
        async with self._session_factory() as s:
            result = await s.execute(
                select(EjaculationData).filter(
                    EjaculationData.userid == userid,
                    EjaculationData.date == now_date,
                )
            )
            existing = result.scalar()
            if existing is not None:
                await s.execute(
                    update(EjaculationData)
                    .where(
                        EjaculationData.userid == userid,
                        EjaculationData.date == now_date,
                    )
                    .values(volume=func.round(EjaculationData.volume + volume, 3))
                )
            else:
                s.add(EjaculationData(userid=userid, date=now_date, volume=volume))
            await s.commit()

    async def get_ejaculation_data(self, userid: int) -> list[dict]:
        """获取用户所有注入记录"""
        async with self._session_factory() as s:
            result = await s.execute(
                select(EjaculationData).filter(EjaculationData.userid == userid)
            )
            return [
                {"date": row.date, "volume": row.volume} for row in result.scalars()
            ]

    async def get_today_ejaculation_data(self, userid: int) -> float:
        """获取用户当日注入量"""
        now_date = time.strftime("%Y-%m-%d", time.localtime())
        async with self._session_factory() as s:
            result = await s.execute(
                select(EjaculationData.volume).filter(
                    EjaculationData.userid == userid,
                    EjaculationData.date == now_date,
                )
            )
            return result.scalar() or 0.0

    # endregion

    # region 排行与惩罚

    async def get_sorted_users(self) -> list[dict]:
        """获取所有用户 jj 长度排行（从大到小）"""
        async with self._session_factory() as s:
            result = await s.execute(
                select(UserData).order_by(UserData.jj_length.desc())
            )
            return [
                {"userid": user.userid, "jj_length": user.jj_length}
                for user in result.scalars()
            ]

    async def punish_all_inactive_users(self) -> None:
        """惩罚不活跃用户

        上次活跃时间超一天且 jj_length > 1 的用户，随机减少 0-1 长度。
        """
        async with self._session_factory() as s:
            result = await s.execute(
                select(UserData).filter(
                    UserData.last_masturbation_time < (time.time() - 86400),
                    UserData.jj_length > 1,
                )
            )
            for user in result.scalars():
                user.jj_length = round(user.jj_length - random.random(), 3)
            await s.commit()

    # endregion
