"""游戏用例编排。"""

import random
import time
from dataclasses import dataclass, field
from enum import StrEnum

from nonebot_plugin_uniref import SceneRef, UserRef

from ..infra.cooldown import CooldownManager
from ..infra.data_manager import DataManager
from .core import (
    GrowthMode,
    InteractionAction,
    InteractionParticipant,
    InteractionResolution,
    LengthState,
    PkResolution,
    classify_length,
    crossed_challenge_threshold,
    growth_delta,
    resolve_interaction,
    resolve_pk,
    supports_growth_mode,
)


class PkOutcomeType(StrEnum):
    DISABLED = "disabled"
    MISSING_TARGET = "missing_target"
    COOLING_DOWN = "cooling_down"
    SELF_TARGET = "self_target"
    USERS_CREATED = "users_created"
    WORLD_MISMATCH = "world_mismatch"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class PkOutcome:
    type: PkOutcomeType
    mode: GrowthMode = GrowthMode.LENGTH
    remaining: float = 0
    created_users: tuple[UserRef, ...] = ()
    resolution: PkResolution | None = None
    attacker_status: str = ""
    defender_status: str = ""
    attacker_probability: float = 0.5


class GrowthOutcomeType(StrEnum):
    DISABLED = "disabled"
    MISSING_TARGET = "missing_target"
    SELF_TARGET = "self_target"
    COOLING_DOWN = "cooling_down"
    USER_CREATED = "user_created"
    WRONG_STATE = "wrong_state"
    ACTOR_CHALLENGING = "actor_challenging"
    TARGET_CHALLENGING = "target_challenging"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class GrowthOutcome:
    type: GrowthOutcomeType
    remaining: float = 0
    created_users: tuple[UserRef, ...] = ()
    random_num: float = 0
    new_length: float = 0
    challenge_started: bool = False


class QueryOutcomeType(StrEnum):
    DISABLED = "disabled"
    USER_CREATED = "user_created"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class QueryOutcome:
    type: QueryOutcomeType
    created_users: tuple[UserRef, ...] = ()
    length: float = 0
    state: LengthState = LengthState.NORMAL


class RankingOutcomeType(StrEnum):
    DISABLED = "disabled"
    TOO_FEW = "too_few"
    USER_CREATED = "user_created"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class RankingEntry:
    user: UserRef
    length: float


@dataclass(frozen=True, slots=True)
class RankingOutcome:
    type: RankingOutcomeType
    ranking: list[RankingEntry] = field(default_factory=list)
    index: int = 0


class InteractionGuardType(StrEnum):
    DISABLED = "disabled"
    USER_CREATED = "user_created"
    COOLING_DOWN = "cooling_down"
    ALLOWED = "allowed"


@dataclass(frozen=True, slots=True)
class InteractionGuard:
    type: InteractionGuardType
    remaining: float = 0
    created_users: tuple[UserRef, ...] = ()


@dataclass(frozen=True, slots=True)
class InteractionResult:
    resolution: InteractionResolution
    ejaculation: float
    today_total: float
    seconds: int


class InjectionQueryType(StrEnum):
    DISABLED = "disabled"
    DAILY = "daily"
    HISTORY_TEXT = "history_text"
    HISTORY_CHART = "history_chart"


@dataclass(frozen=True, slots=True)
class InjectionQueryResult:
    type: InjectionQueryType
    total: float = 0
    history: dict[str, float] = field(default_factory=dict)


def get_random_num() -> float:
    rand_num = random.random()
    rand_num = random.uniform(0, 1) if rand_num > 0.1 else random.uniform(1, 2)
    return round(rand_num, 3)


def _growth_is_blocked(status: str) -> bool:
    return status in {"challenge_started_low_win", "is_challenging"}


class GameApplication:
    def __init__(
        self,
        data_manager: DataManager,
        cooldown: CooldownManager,
        *,
        penalties_enabled: bool,
    ) -> None:
        self._data = data_manager
        self._cooldown = cooldown
        self._penalties_enabled = penalties_enabled

    async def penalties_and_resets(self) -> None:
        if self._penalties_enabled:
            await self._data.punish_all_inactive_users()

    async def _create_missing_users(
        self,
        *user_refs: UserRef,
    ) -> tuple[UserRef, ...]:
        created_users: list[UserRef] = []
        for user_ref in dict.fromkeys(user_refs):
            if not await self._data.has_user(user_ref):
                await self._data.add_new_user(user_ref)
                created_users.append(user_ref)
        return tuple(created_users)

    async def _active_challenge_blocks_growth(self, user_ref: UserRef) -> bool:
        if not await self._data.is_challenging(user_ref):
            return False
        return _growth_is_blocked(await self._data.update_challenge_status(user_ref))

    async def execute_pk(
        self,
        scene_ref: SceneRef,
        attacker_ref: UserRef,
        defender_ref: UserRef | None,
    ) -> PkOutcome:
        if not await self._data.is_scene_enabled(scene_ref):
            return PkOutcome(PkOutcomeType.DISABLED)

        if defender_ref is None:
            return PkOutcome(PkOutcomeType.MISSING_TARGET)

        if defender_ref == attacker_ref:
            return PkOutcome(PkOutcomeType.SELF_TARGET)

        created_users = await self._create_missing_users(attacker_ref, defender_ref)
        if created_users:
            return PkOutcome(
                PkOutcomeType.USERS_CREATED,
                created_users=created_users,
            )

        attacker_length = await self._data.get_jj_length(attacker_ref)
        defender_length = await self._data.get_jj_length(defender_ref)
        mode = GrowthMode.LENGTH if attacker_length > 0 else GrowthMode.DEPTH
        if not supports_growth_mode(defender_length, mode):
            return PkOutcome(PkOutcomeType.WORLD_MISMATCH, mode=mode)

        await self.penalties_and_resets()
        if not await self._cooldown.pkcd_check(attacker_ref):
            remaining = round(
                self._cooldown.pk_cd_time
                - (time.time() - self._cooldown.pk_cd_data[attacker_ref]),
                3,
            )
            return PkOutcome(PkOutcomeType.COOLING_DOWN, remaining=remaining)

        self._cooldown.pk_cd_data.update({attacker_ref: time.time()})
        win_roll = random.random()
        win_probability = await self._data.get_win_probability(attacker_ref)
        resolution = resolve_pk(
            win_probability,
            win_roll=win_roll,
            random_num=get_random_num(),
        )
        direction = 1 if mode is GrowthMode.LENGTH else -1
        if resolution.won:
            await self._data.set_win_probability(attacker_ref, -0.01)
            await self._data.set_win_probability(defender_ref, 0.01)
            await self._data.set_jj_length(
                attacker_ref,
                direction * resolution.random_num / 2,
            )
            await self._data.set_jj_length(
                defender_ref,
                -direction * resolution.random_num,
            )
        else:
            await self._data.set_win_probability(attacker_ref, 0.01)
            await self._data.set_win_probability(defender_ref, -0.01)
            await self._data.set_jj_length(
                attacker_ref,
                -direction * resolution.random_num,
            )
            await self._data.set_jj_length(
                defender_ref,
                direction * resolution.random_num / 2,
            )

        attacker_status = await self._data.update_challenge_status(attacker_ref)
        defender_status = await self._data.update_challenge_status(defender_ref)
        probability = await self._data.get_win_probability(attacker_ref)
        return PkOutcome(
            PkOutcomeType.COMPLETED,
            mode=mode,
            resolution=resolution,
            attacker_status=attacker_status,
            defender_status=defender_status,
            attacker_probability=probability,
        )

    async def grow_self(
        self,
        scene_ref: SceneRef,
        user_ref: UserRef,
        mode: GrowthMode,
    ) -> GrowthOutcome:
        if not await self._data.is_scene_enabled(scene_ref):
            return GrowthOutcome(GrowthOutcomeType.DISABLED)

        created_users = await self._create_missing_users(user_ref)
        if created_users:
            return GrowthOutcome(
                GrowthOutcomeType.USER_CREATED,
                created_users=created_users,
            )

        await self.penalties_and_resets()
        current_length = await self._data.get_jj_length(user_ref)
        if not supports_growth_mode(current_length, mode):
            return GrowthOutcome(GrowthOutcomeType.WRONG_STATE)

        status = await self._data.update_challenge_status(user_ref)
        if _growth_is_blocked(status):
            return GrowthOutcome(GrowthOutcomeType.ACTOR_CHALLENGING)

        if not await self._cooldown.cd_check(user_ref):
            remaining = round(
                self._cooldown.dj_cd_time
                - (time.time() - self._cooldown.cd_data[user_ref]),
                3,
            )
            return GrowthOutcome(GrowthOutcomeType.COOLING_DOWN, remaining=remaining)

        self._cooldown.cd_data[user_ref] = time.time()
        random_num = get_random_num()
        await self._data.set_jj_length(user_ref, growth_delta(random_num, mode))
        new_length = await self._data.get_jj_length(user_ref)
        challenge_started = crossed_challenge_threshold(current_length, new_length)
        if challenge_started:
            await self._data.update_challenge_status(user_ref)
        else:
            new_length = await self._data.get_jj_length(user_ref)
        return GrowthOutcome(
            GrowthOutcomeType.COMPLETED,
            random_num=random_num,
            new_length=new_length,
            challenge_started=challenge_started,
        )

    async def grow_target(
        self,
        scene_ref: SceneRef,
        user_ref: UserRef,
        target_ref: UserRef | None,
        mode: GrowthMode,
    ) -> GrowthOutcome:
        if not await self._data.is_scene_enabled(scene_ref):
            return GrowthOutcome(GrowthOutcomeType.DISABLED)

        if target_ref is None:
            return GrowthOutcome(GrowthOutcomeType.MISSING_TARGET)

        if target_ref == user_ref:
            return GrowthOutcome(GrowthOutcomeType.SELF_TARGET)

        created_users = await self._create_missing_users(user_ref, target_ref)
        if created_users:
            return GrowthOutcome(
                GrowthOutcomeType.USER_CREATED,
                created_users=created_users,
            )

        await self.penalties_and_resets()
        current_length = await self._data.get_jj_length(target_ref)
        if not supports_growth_mode(current_length, mode):
            return GrowthOutcome(GrowthOutcomeType.WRONG_STATE)

        actor_length = await self._data.get_jj_length(user_ref)
        actor_uses_mode = supports_growth_mode(actor_length, mode)
        if actor_uses_mode and await self._active_challenge_blocks_growth(user_ref):
            return GrowthOutcome(GrowthOutcomeType.ACTOR_CHALLENGING)

        target_status = await self._data.update_challenge_status(target_ref)
        if _growth_is_blocked(target_status):
            return GrowthOutcome(GrowthOutcomeType.TARGET_CHALLENGING)

        if not await self._cooldown.suo_cd_check(user_ref):
            remaining = round(
                self._cooldown.suo_cd_time
                - (time.time() - self._cooldown.suo_cd_data[user_ref]),
                3,
            )
            return GrowthOutcome(GrowthOutcomeType.COOLING_DOWN, remaining=remaining)

        self._cooldown.suo_cd_data[user_ref] = time.time()
        random_num = get_random_num()
        await self._data.set_jj_length(target_ref, growth_delta(random_num, mode))
        new_length = await self._data.get_jj_length(target_ref)
        challenge_started = crossed_challenge_threshold(current_length, new_length)
        if challenge_started:
            await self._data.update_challenge_status(target_ref)
        return GrowthOutcome(
            GrowthOutcomeType.COMPLETED,
            random_num=random_num,
            new_length=new_length,
            challenge_started=challenge_started,
        )

    async def query_user(
        self,
        scene_ref: SceneRef,
        requester_ref: UserRef,
        target_ref: UserRef,
    ) -> QueryOutcome:
        if not await self._data.is_scene_enabled(scene_ref):
            return QueryOutcome(QueryOutcomeType.DISABLED)

        created_users = await self._create_missing_users(requester_ref, target_ref)
        if created_users:
            return QueryOutcome(
                QueryOutcomeType.USER_CREATED,
                created_users=created_users,
            )

        await self.penalties_and_resets()
        length = await self._data.get_jj_length(target_ref)
        return QueryOutcome(
            QueryOutcomeType.COMPLETED,
            length=length,
            state=classify_length(length),
        )

    async def query_ranking(
        self,
        scene_ref: SceneRef,
        user_ref: UserRef,
    ) -> RankingOutcome:
        if not await self._data.is_scene_enabled(scene_ref):
            return RankingOutcome(RankingOutcomeType.DISABLED)
        ranking = [
            RankingEntry(user=user, length=length)
            for user, length in await self._data.get_ranking(user_ref.namespace)
        ]
        if len(ranking) < 5:
            return RankingOutcome(RankingOutcomeType.TOO_FEW)
        indexes = [index for index, item in enumerate(ranking) if item.user == user_ref]
        if not indexes:
            await self._data.add_new_user(user_ref)
            return RankingOutcome(RankingOutcomeType.USER_CREATED)
        return RankingOutcome(
            RankingOutcomeType.COMPLETED,
            ranking=ranking,
            index=indexes[0],
        )

    async def prepare_interaction(
        self,
        scene_ref: SceneRef,
        user_ref: UserRef,
    ) -> InteractionGuard:
        if not await self._data.is_scene_enabled(scene_ref):
            return InteractionGuard(InteractionGuardType.DISABLED)

        created_users = await self._create_missing_users(user_ref)
        if created_users:
            return InteractionGuard(
                InteractionGuardType.USER_CREATED,
                created_users=created_users,
            )

        await self.penalties_and_resets()
        if not await self._data.is_scene_enabled(scene_ref):
            return InteractionGuard(InteractionGuardType.DISABLED)
        if not await self._cooldown.fuck_cd_check(user_ref):
            remaining = round(
                self._cooldown.fuck_cd_time
                - (time.time() - self._cooldown.ejaculation_cd[user_ref]),
                3,
            )
            return InteractionGuard(
                InteractionGuardType.COOLING_DOWN,
                remaining=remaining,
            )
        return InteractionGuard(InteractionGuardType.ALLOWED)

    @staticmethod
    def roll_interaction() -> float:
        return random.uniform(0, 1)

    async def begin_interaction(
        self,
        user_ref: UserRef,
        target_ref: UserRef,
        requested_action: InteractionAction,
        reverse_roll: float | None,
    ) -> InteractionResolution:
        """初始化互动目标、固定结算结果并开始计算冷却。

        Args:
            user_ref: 命令发起者。
            target_ref: 已由接入层选定的有效目标。
            requested_action: 发起者请求的互动动作。
            reverse_roll: 透命令已生成的反制随机值；榨命令传入 ``None``。

        Returns:
            供选择提示和最终结算共同使用的领域结果。

        Raises:
            ValueError: 目标与发起者相同。
        """
        if target_ref == user_ref:
            raise ValueError("互动目标不能是发起者")

        await self._create_missing_users(target_ref)
        requester_length = await self._data.get_jj_length(user_ref)
        target_length = await self._data.get_jj_length(target_ref)
        resolution = resolve_interaction(
            requested_action,
            requester_length,
            target_length,
            reverse_roll=reverse_roll,
        )
        self._cooldown.record_interaction(user_ref)
        return resolution

    async def complete_interaction(
        self,
        user_ref: UserRef,
        lucky_user_ref: UserRef,
        resolution: InteractionResolution,
    ) -> InteractionResult:
        await self._data.update_activity(lucky_user_ref)
        await self._data.update_activity(user_ref)
        ejaculation = round(random.uniform(1, 100), 3)
        recipient = (
            user_ref
            if resolution.recipient is InteractionParticipant.REQUESTER
            else lucky_user_ref
        )
        await self._data.insert_ejaculation(recipient, ejaculation)
        seconds = random.randint(1, 20)
        today_total = await self._data.get_today_ejaculation_data(recipient)
        return InteractionResult(
            resolution=resolution,
            ejaculation=ejaculation,
            today_total=today_total,
            seconds=seconds,
        )

    async def set_scene_enabled(
        self,
        scene_ref: SceneRef,
        enabled: bool,
    ) -> None:
        await self._data.set_scene_enabled(scene_ref, enabled)

    async def query_injection(
        self,
        scene_ref: SceneRef,
        user_ref: UserRef,
        *,
        history: bool,
    ) -> InjectionQueryResult:
        await self.penalties_and_resets()
        if not await self._data.is_scene_enabled(scene_ref):
            return InjectionQueryResult(InjectionQueryType.DISABLED)
        data = await self._data.get_ejaculation_data(user_ref)
        if history:
            if not data:
                return InjectionQueryResult(InjectionQueryType.HISTORY_TEXT)
            total = 0.0
            values: dict[str, float] = {}
            for item in data:
                value = item["volume"]
                total += value
                values[item["date"]] = value
            if len(values) < 2:
                return InjectionQueryResult(
                    InjectionQueryType.HISTORY_TEXT,
                    total=total,
                )
            return InjectionQueryResult(
                InjectionQueryType.HISTORY_CHART,
                total=total,
                history=values,
            )
        total = await self._data.get_today_ejaculation_data(user_ref)
        return InjectionQueryResult(InjectionQueryType.DAILY, total=total)
