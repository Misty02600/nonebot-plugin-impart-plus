"""数据访问与现有状态更新流程。"""

import time
from collections.abc import Callable
from dataclasses import dataclass

from nonebot_plugin_uniref import SceneRef, UserRef, decode_ref, encode_ref
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..impart.core import (
    InteractionVolumeSettlement,
    PkSettlement,
    PossessionSettlement,
    PossessionStatus,
    StateEvaluation,
    UserGameState,
    evaluate_user_state,
    resolve_interaction_volume,
    resolve_pk_settlement,
    resolve_possession,
)
from .database import (
    PERSISTED_NAMESPACE_MAX_LENGTH,
    PERSISTED_REF_MAX_LENGTH,
    EjaculationData,
    SceneData,
    UserData,
)


@dataclass(frozen=True, slots=True)
class UserQueryData:
    length: float
    challenge_completed: bool
    today_total: float
    records: dict[str, float]


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


def _to_game_state(user: UserData) -> UserGameState:
    return UserGameState(
        length=user.jj_length,
        win_probability=user.win_probability,
        is_challenging=user.is_challenging,
        challenge_completed=user.challenge_completed,
    )


def _apply_game_state(user: UserData, state: UserGameState) -> None:
    user.jj_length = state.length
    user.win_probability = state.win_probability
    user.is_challenging = state.is_challenging
    user.challenge_completed = state.challenge_completed


class DataManager:
    def __init__(
        self,
        session_factory: Callable[[], AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def update_challenge_status(self, user_ref: UserRef) -> StateEvaluation:
        """根据用户当前状态更新挑战状态与胜率。"""
        encoded = _encode_persistent_ref(user_ref)
        async with self._session_factory() as session:
            result = await session.execute(
                select(UserData).where(UserData.user_ref == encoded)
            )
            user = result.scalar()
            if not user:
                raise LookupError("challenge user does not exist")

            evaluation = evaluate_user_state(_to_game_state(user))
            _apply_game_state(user, evaluation.state)

            await session.commit()
            return evaluation

    async def settle_pk(
        self,
        attacker_ref: UserRef,
        defender_ref: UserRef,
        *,
        win_roll: float,
        random_num: float,
    ) -> PkSettlement:
        """在一个数据库事务中结算并保存 PK 双方状态。

        Args:
            attacker_ref: 发起者持久身份。
            defender_ref: 目标持久身份。
            win_roll: 本局固定的胜负随机值。
            random_num: 本局固定的长度变化随机值。

        Returns:
            已成功提交的完整纯结算结果。

        Raises:
            LookupError: 任一参与者在事务中不存在。
            ValueError: 双方在事务中不属于同一个正负世界。
        """
        attacker_key = _encode_persistent_ref(attacker_ref)
        defender_key = _encode_persistent_ref(defender_ref)
        async with self._session_factory() as session, session.begin():
            result = await session.execute(
                select(UserData).where(
                    UserData.user_ref.in_((attacker_key, defender_key))
                )
            )
            users = {user.user_ref: user for user in result.scalars()}
            attacker = users.get(attacker_key)
            defender = users.get(defender_key)
            if attacker is None or defender is None:
                raise LookupError("PK participant does not exist")

            settlement = resolve_pk_settlement(
                _to_game_state(attacker),
                _to_game_state(defender),
                win_roll=win_roll,
                random_num=random_num,
            )
            _apply_game_state(attacker, settlement.attacker.final)
            _apply_game_state(defender, settlement.defender.final)
            await session.flush()
        return settlement

    async def settle_possession(
        self, actor_ref: UserRef, target_ref: UserRef
    ) -> PossessionSettlement | PossessionStatus:
        """在一个事务中检查夺舍并写回双方；拒绝时不修改任何状态。"""
        actor_key = _encode_persistent_ref(actor_ref)
        target_key = _encode_persistent_ref(target_ref)
        async with self._session_factory() as session, session.begin():
            result = await session.execute(
                select(UserData).where(UserData.user_ref.in_((actor_key, target_key)))
            )
            users = {user.user_ref: user for user in result.scalars()}
            actor = users.get(actor_key)
            target = users.get(target_key)
            if actor is None or target is None:
                raise LookupError("possession participant does not exist")
            settlement = resolve_possession(
                _to_game_state(actor), _to_game_state(target)
            )
            if isinstance(settlement, PossessionStatus):
                return settlement
            _apply_game_state(actor, settlement.actor)
            _apply_game_state(target, settlement.target)
            await session.flush()
        return settlement

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
                    win_probability=0.5,
                )
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
                .values(jj_length=round(current_length + length, 3))
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

    async def settle_interaction_volume(
        self,
        user_ref: UserRef,
        volume: float,
        *,
        feminization_roll: float | None,
    ) -> InteractionVolumeSettlement:
        """在一个事务中累计当日互动量，并按需完成雌堕。"""
        encoded = _encode_persistent_ref(user_ref)
        today = self.get_today()
        async with self._session_factory() as session, session.begin():
            user = (
                await session.execute(
                    select(UserData).where(UserData.user_ref == encoded)
                )
            ).scalar_one_or_none()
            if user is None:
                raise LookupError("interaction recipient does not exist")

            daily = (
                await session.execute(
                    select(EjaculationData).where(
                        EjaculationData.user_ref == encoded,
                        EjaculationData.date == today,
                    )
                )
            ).scalar_one_or_none()
            settlement = resolve_interaction_volume(
                user.jj_length,
                daily.volume if daily else 0.0,
                volume,
                feminization_roll=feminization_roll,
            )
            if daily is None:
                session.add(
                    EjaculationData(
                        user_ref=encoded,
                        date=today,
                        volume=settlement.total,
                    )
                )
            else:
                daily.volume = settlement.total
            if settlement.feminized:
                user.jj_length = settlement.length
            await session.flush()
        return settlement

    async def get_user_query_data(
        self,
        user_ref: UserRef,
        *,
        history: bool,
    ) -> UserQueryData | None:
        """用一条查询取得用户长度和所需范围内的互动记录。"""
        encoded = _encode_persistent_ref(user_ref)
        today = self.get_today()
        join_condition = EjaculationData.user_ref == UserData.user_ref
        if not history:
            join_condition &= EjaculationData.date == today
        statement = (
            select(
                UserData.jj_length,
                UserData.challenge_completed,
                EjaculationData.date,
                EjaculationData.volume,
            )
            .select_from(UserData)
            .outerjoin(EjaculationData, join_condition)
            .where(UserData.user_ref == encoded)
        )
        if history:
            statement = statement.order_by(EjaculationData.date.asc())
        async with self._session_factory() as session:
            rows = (await session.execute(statement)).all()
        if not rows:
            return None
        records = {
            row.date: row.volume
            for row in rows
            if row.date is not None and row.volume is not None
        }
        return UserQueryData(
            length=rows[0].jj_length,
            challenge_completed=rows[0].challenge_completed,
            today_total=records.get(today, 0.0),
            records=records,
        )

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
