"""数据访问与现有状态更新流程。"""

import random
import time
from collections.abc import Callable
from typing import Any, cast

from nonebot_plugin_uniref import SceneRef, UserRef, decode_ref, encode_ref
from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..impart.core import UserGameState, evaluate_user_state
from .database import (
    PERSISTED_NAMESPACE_MAX_LENGTH,
    PERSISTED_REF_MAX_LENGTH,
    EjaculationData,
    SceneData,
    UserData,
)

_MAX_EJACULATION_WRITE_ATTEMPTS = 32


def _validate_namespace(namespace: str) -> None:
    if len(namespace) > PERSISTED_NAMESPACE_MAX_LENGTH:
        raise ValueError(
            "namespace exceeds the persistent limit of "
            f"{PERSISTED_NAMESPACE_MAX_LENGTH} characters"
        )


def _encode_persistent_ref(ref: UserRef | SceneRef) -> str:
    _validate_namespace(ref.namespace)
    encoded = encode_ref(ref)
    if len(encoded) > PERSISTED_REF_MAX_LENGTH:
        raise ValueError(
            "encoded Ref exceeds the persistent limit of "
            f"{PERSISTED_REF_MAX_LENGTH} characters"
        )
    return encoded


def _decode_user_ref(encoded: str, expected_namespace: str) -> UserRef:
    """解码数据库用户键并核对 namespace 投影。

    Args:
        encoded: `encode_ref()` 生成的完整用户键。
        expected_namespace: 同一行保存的 namespace 投影。

    Returns:
        解码后的用户 Ref。

    Raises:
        TypeError: 编码值不是 UserRef。
        ValueError: 编码值与 namespace 投影不一致。
    """
    ref = decode_ref(encoded)
    if not isinstance(ref, UserRef):
        raise TypeError("user_data contains a non-user Ref")
    if ref.namespace != expected_namespace:
        raise ValueError("user_ref does not match user_namespace")
    return ref


class DataManager:
    def __init__(
        self,
        session_factory: Callable[[], AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def update_challenge_status(self, user_ref: UserRef) -> str:
        """根据用户当前状态更新挑战状态与胜率。"""
        encoded = _encode_persistent_ref(user_ref)
        async with self._session_factory() as session:
            result = await session.execute(
                select(UserData).where(UserData.user_ref == encoded)
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

    async def has_user(self, user_ref: UserRef) -> bool:
        encoded = _encode_persistent_ref(user_ref)
        async with self._session_factory() as session:
            result = await session.execute(
                select(UserData).filter(UserData.user_ref == encoded)
            )
            return bool(result.scalar())

    async def is_challenging(self, user_ref: UserRef) -> bool:
        encoded = _encode_persistent_ref(user_ref)
        async with self._session_factory() as session:
            result = await session.execute(
                select(UserData.is_challenging).where(UserData.user_ref == encoded)
            )
            return bool(result.scalar())

    async def add_new_user(self, user_ref: UserRef) -> None:
        """插入初始长度为 10.0 的新用户。"""
        async with self._session_factory() as session:
            session.add(
                UserData(
                    user_ref=_encode_persistent_ref(user_ref),
                    user_namespace=user_ref.namespace,
                    jj_length=10.0,
                    last_masturbation_time=int(time.time()),
                    win_probability=0.5,
                )
            )
            await session.commit()

    async def update_activity(self, user_ref: UserRef) -> None:
        """更新用户活跃时间。"""
        if not await self.has_user(user_ref):
            await self.add_new_user(user_ref)
        encoded = _encode_persistent_ref(user_ref)
        async with self._session_factory() as session:
            await session.execute(
                update(UserData)
                .where(UserData.user_ref == encoded)
                .values(last_masturbation_time=int(time.time()))
            )
            await session.commit()

    async def get_jj_length(self, user_ref: UserRef) -> float:
        """返回用户当前长度。"""
        encoded = _encode_persistent_ref(user_ref)
        async with self._session_factory() as session:
            result = await session.execute(
                select(UserData.jj_length).filter(UserData.user_ref == encoded)
            )
            return result.scalar() or 0.0

    async def set_jj_length(self, user_ref: UserRef, length: float) -> None:
        """在数据库内累加用户长度。"""
        encoded = _encode_persistent_ref(user_ref)
        async with self._session_factory() as session:
            current_length = await self.get_jj_length(user_ref)
            await session.execute(
                update(UserData)
                .where(UserData.user_ref == encoded)
                .values(
                    jj_length=round(current_length + length, 3),
                    last_masturbation_time=int(time.time()),
                )
            )
            await session.commit()

    async def get_win_probability(self, user_ref: UserRef) -> float:
        """返回用户当前胜率。"""
        encoded = _encode_persistent_ref(user_ref)
        async with self._session_factory() as session:
            result = await session.execute(
                select(UserData.win_probability).filter(UserData.user_ref == encoded)
            )
            return result.scalar() or 0.5

    async def set_win_probability(
        self,
        user_ref: UserRef,
        probability_change: float,
    ) -> None:
        """在数据库内累加用户胜率。"""
        encoded = _encode_persistent_ref(user_ref)
        async with self._session_factory() as session:
            current_probability = await self.get_win_probability(user_ref)
            await session.execute(
                update(UserData)
                .where(UserData.user_ref == encoded)
                .values(
                    win_probability=round(
                        current_probability + probability_change,
                        3,
                    ),
                    last_masturbation_time=int(time.time()),
                )
            )
            await session.commit()

    async def is_scene_enabled(self, scene_ref: SceneRef) -> bool:
        encoded = _encode_persistent_ref(scene_ref)
        async with self._session_factory() as session:
            result = await session.execute(
                select(SceneData.allow).filter(SceneData.scene_ref == encoded)
            )
            return result.scalar() or False

    async def set_scene_enabled(self, scene_ref: SceneRef, enabled: bool) -> None:
        encoded = _encode_persistent_ref(scene_ref)
        async with self._session_factory() as session:
            result = await session.execute(
                select(SceneData).where(SceneData.scene_ref == encoded)
            )
            existing_scene = result.scalar_one_or_none()
            if existing_scene is None:
                session.add(
                    SceneData(
                        scene_ref=encoded,
                        scene_namespace=scene_ref.namespace,
                        scene_type=scene_ref.type.value,
                        allow=enabled,
                    )
                )
            else:
                if (
                    existing_scene.scene_namespace != scene_ref.namespace
                    or existing_scene.scene_type != scene_ref.type.value
                ):
                    raise ValueError(
                        "scene_ref does not match scene namespace/type projections"
                    )
                existing_scene.allow = enabled
            await session.commit()

    @staticmethod
    def get_today() -> str:
        """获取当前年月日格式，例如 2024-10-20。"""
        return time.strftime("%Y-%m-%d", time.localtime())

    async def insert_ejaculation(self, user_ref: UserRef, volume: float) -> None:
        """将一次注入量原子累加到用户的当日记录。

        Args:
            user_ref: 实际获得液体的用户身份。
            volume: 本次需要累加的数量。

        Raises:
            ValueError: Ref 超出数据库的可移植长度边界。
            RuntimeError: 连续并发冲突超过重试上限。
        """
        encoded = _encode_persistent_ref(user_ref)
        now_date = self.get_today()
        for _ in range(_MAX_EJACULATION_WRITE_ATTEMPTS):
            async with self._session_factory() as read_session:
                result = await read_session.execute(
                    select(EjaculationData.volume).where(
                        EjaculationData.user_ref == encoded,
                        EjaculationData.date == now_date,
                    )
                )
                current_volume = result.scalar_one_or_none()

            if current_volume is None:
                async with self._session_factory() as insert_session:
                    insert_session.add(
                        EjaculationData(
                            user_ref=encoded,
                            date=now_date,
                            volume=volume,
                        )
                    )
                    try:
                        await insert_session.commit()
                    except IntegrityError:
                        await insert_session.rollback()
                    else:
                        return
                continue

            async with self._session_factory() as update_session:
                result = cast(
                    CursorResult[Any],
                    await update_session.execute(
                        update(EjaculationData)
                        .where(
                            EjaculationData.user_ref == encoded,
                            EjaculationData.date == now_date,
                            EjaculationData.volume == current_volume,
                        )
                        .values(volume=round(current_volume + volume, 3))
                    ),
                )
                if result.rowcount == 1:
                    await update_session.commit()
                    return
                await update_session.rollback()

        raise RuntimeError("failed to update daily volume due to concurrent writes")

    async def get_ejaculation_data(self, user_ref: UserRef) -> list[dict]:
        """获取一个用户的所有注入记录。"""
        encoded = _encode_persistent_ref(user_ref)
        async with self._session_factory() as session:
            result = await session.execute(
                select(EjaculationData).filter(EjaculationData.user_ref == encoded)
            )
            return [
                {"date": row.date, "volume": row.volume} for row in result.scalars()
            ]

    async def get_today_ejaculation_data(self, user_ref: UserRef) -> float:
        """获取用户当日注入量。"""
        encoded = _encode_persistent_ref(user_ref)
        async with self._session_factory() as session:
            result = await session.execute(
                select(EjaculationData.volume).filter(
                    EjaculationData.user_ref == encoded,
                    EjaculationData.date == self.get_today(),
                )
            )
            return result.scalar() or 0.0

    async def punish_all_inactive_users(self) -> None:
        """减少超过一天未活动且长度大于 1 的用户长度。"""
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

    async def get_ranking(self, namespace: str) -> list[tuple[UserRef, float]]:
        """返回指定用户 namespace 内按长度降序排列的榜单。"""
        _validate_namespace(namespace)
        async with self._session_factory() as session:
            result = await session.execute(
                select(UserData)
                .where(UserData.user_namespace == namespace)
                .order_by(UserData.jj_length.desc())
            )
            return [
                (
                    _decode_user_ref(user.user_ref, user.user_namespace),
                    user.jj_length,
                )
                for user in result.scalars()
            ]
