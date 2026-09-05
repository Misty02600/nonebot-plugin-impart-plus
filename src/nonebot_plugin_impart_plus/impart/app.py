"""游戏用例编排。"""

import asyncio
import random
import time
from dataclasses import dataclass, field
from enum import StrEnum

from nonebot_plugin_uniref import SceneRef, UserRef

from ..infra.cooldown import CooldownManager
from ..infra.data_manager import DataManager
from .core import (
    CHALLENGE_TIERS,
    ChallengeTier,
    GrowthMode,
    InteractionAction,
    InteractionParticipant,
    InteractionResolution,
    InteractionVolumeSettlement,
    LengthState,
    PossessionStatus,
    active_challenge,
    classify_length,
    is_xnn,
    pk_target_limit,
    resolve_interaction,
    supports_growth_mode,
)


class PkOutcomeType(StrEnum):
    DISABLED = "disabled"
    MISSING_TARGET = "missing_target"
    COOLING_DOWN = "cooling_down"
    SELF_TARGET = "self_target"
    USERS_CREATED = "users_created"
    WORLD_MISMATCH = "world_mismatch"
    MULTI_TARGET_UNAVAILABLE = "multi_target_unavailable"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class PkPreparation:
    enabled: bool
    max_targets: int = 1


@dataclass(frozen=True, slots=True)
class PkTargetOutcome:
    length_change: float
    status: str = ""
    challenge: ChallengeTier | None = None


@dataclass(frozen=True, slots=True)
class PkOutcome:
    type: PkOutcomeType
    mode: GrowthMode = GrowthMode.LENGTH
    remaining: float = 0
    created_users: tuple[UserRef, ...] = ()
    won: bool = False
    attacker_change: float = 0
    attacker_status: str = ""
    attacker_challenge: ChallengeTier | None = None
    targets: tuple[PkTargetOutcome, ...] = ()
    attacker_probability: float = 0.5
    unlocked_users: dict[UserRef, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PossessionOutcome:
    type: PossessionStatus
    created_users: tuple[UserRef, ...] = ()
    half: float = 0
    target_challenge: ChallengeTier | None = None


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
    amount: float = 0
    new_length: float = 0
    challenge: ChallengeTier | None = None
    unlocked_users: dict[UserRef, int] = field(default_factory=dict)


class QueryOutcomeType(StrEnum):
    DISABLED = "disabled"
    USER_CREATED = "user_created"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class QueryOutcome:
    type: QueryOutcomeType
    created_users: tuple[UserRef, ...] = ()
    length: float = 0
    challenge_tier: int = 0
    state: LengthState = LengthState.NORMAL
    today_total: float = 0
    history_total: float | None = None
    history: dict[str, float] = field(default_factory=dict)


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
class InteractionReceipt:
    volume: float
    settlement: InteractionVolumeSettlement


@dataclass(frozen=True, slots=True)
class InteractionResult:
    resolution: InteractionResolution
    seconds: int
    receipts: dict[InteractionParticipant, InteractionReceipt]


def get_random_num() -> float:
    rand_num = random.random()
    rand_num = random.uniform(0, 1) if rand_num > 0.1 else random.uniform(1, 2)
    return round(rand_num, 3)


class GameApplication:
    def __init__(
        self,
        data_manager: DataManager,
        cooldown: CooldownManager,
    ) -> None:
        self._data = data_manager
        self._cooldown = cooldown
        self._state_lock = asyncio.Lock()

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

    async def execute_possession(
        self,
        scene_ref: SceneRef,
        actor_ref: UserRef,
        target_ref: UserRef | None,
    ) -> PossessionOutcome:
        if not await self._data.is_scene_enabled(scene_ref):
            return PossessionOutcome(PossessionStatus.DISABLED)
        if target_ref is None:
            return PossessionOutcome(PossessionStatus.MISSING_TARGET)
        async with self._state_lock:
            created_users = await self._create_missing_users(actor_ref, target_ref)
            if created_users:
                return PossessionOutcome(
                    PossessionStatus.USERS_CREATED, created_users=created_users
                )
            result = await self._data.settle_possession(actor_ref, target_ref)
            if isinstance(result, PossessionStatus):
                return PossessionOutcome(result)
            return PossessionOutcome(
                PossessionStatus.COMPLETED,
                half=result.half,
                target_challenge=result.target_challenge,
            )

    async def prepare_pk(
        self,
        scene_ref: SceneRef,
        attacker_ref: UserRef,
    ) -> PkPreparation:
        if not await self._data.is_scene_enabled(scene_ref):
            return PkPreparation(False)
        async with self._state_lock:
            if not await self._data.has_user(attacker_ref):
                return PkPreparation(True)
            state = (await self._data.get_user_states(attacker_ref))[attacker_ref]
            return PkPreparation(True, pk_target_limit(state))

    async def execute_pk(
        self,
        scene_ref: SceneRef,
        attacker_ref: UserRef,
        defender_refs: tuple[UserRef, ...],
    ) -> PkOutcome:
        if not await self._data.is_scene_enabled(scene_ref):
            return PkOutcome(PkOutcomeType.DISABLED)

        if not defender_refs:
            return PkOutcome(PkOutcomeType.MISSING_TARGET)

        if attacker_ref in defender_refs:
            return PkOutcome(PkOutcomeType.SELF_TARGET)
        if len(defender_refs) > CHALLENGE_TIERS[-1].tier + 1 or len(
            set(defender_refs)
        ) != len(defender_refs):
            raise ValueError(
                "PK targets must be unique and within the configured tier limit"
            )

        async with self._state_lock:
            return await self._execute_pk(attacker_ref, defender_refs)

    async def _execute_pk(
        self,
        attacker_ref: UserRef,
        defender_refs: tuple[UserRef, ...],
    ) -> PkOutcome:
        if len(defender_refs) > 1 and await self._data.has_user(attacker_ref):
            attacker_state = (await self._data.get_user_states(attacker_ref))[
                attacker_ref
            ]
            if len(defender_refs) > pk_target_limit(attacker_state):
                return PkOutcome(PkOutcomeType.MULTI_TARGET_UNAVAILABLE)

        created_users = await self._create_missing_users(
            attacker_ref,
            *defender_refs,
        )
        if created_users:
            return PkOutcome(
                PkOutcomeType.USERS_CREATED,
                created_users=created_users,
            )

        states = await self._data.get_user_states(attacker_ref, *defender_refs)
        attacker_state = states[attacker_ref]
        mode = GrowthMode.LENGTH if attacker_state.length > 0 else GrowthMode.DEPTH
        if any(
            not supports_growth_mode(states[defender].length, mode)
            for defender in defender_refs
        ):
            return PkOutcome(PkOutcomeType.WORLD_MISMATCH, mode=mode)

        if not await self._cooldown.pkcd_check(attacker_ref):
            remaining = round(
                self._cooldown.pk_cd_time
                - (time.time() - self._cooldown.pk_cd_data[attacker_ref]),
                3,
            )
            return PkOutcome(PkOutcomeType.COOLING_DOWN, remaining=remaining)

        self._cooldown.pk_cd_data.update({attacker_ref: time.time()})
        win_roll = random.random()
        random_num = get_random_num()
        settlement = await self._data.settle_pk(
            attacker_ref,
            defender_refs,
            win_roll=win_roll,
            random_num=random_num,
        )
        return PkOutcome(
            PkOutcomeType.COMPLETED,
            mode=settlement.mode,
            won=settlement.won,
            attacker_change=settlement.attacker.length_change,
            attacker_status=settlement.attacker.status,
            attacker_challenge=settlement.attacker.challenge,
            targets=tuple(
                PkTargetOutcome(
                    length_change=participant.length_change,
                    status=participant.status,
                    challenge=participant.challenge,
                )
                for participant in settlement.defenders
            ),
            attacker_probability=settlement.attacker.final.win_probability,
            unlocked_users={
                user: participant.final.challenge_tier
                for user, participant in (
                    (attacker_ref, settlement.attacker),
                    *zip(defender_refs, settlement.defenders, strict=True),
                )
                if participant.final.challenge_tier > participant.before.challenge_tier
            },
        )

    async def grow_self(
        self,
        scene_ref: SceneRef,
        user_ref: UserRef,
        mode: GrowthMode,
    ) -> GrowthOutcome:
        if not await self._data.is_scene_enabled(scene_ref):
            return GrowthOutcome(GrowthOutcomeType.DISABLED)

        async with self._state_lock:
            return await self._grow_self(user_ref, mode)

    async def _grow_self(
        self,
        user_ref: UserRef,
        mode: GrowthMode,
    ) -> GrowthOutcome:
        created_users = await self._create_missing_users(user_ref)
        if created_users:
            return GrowthOutcome(
                GrowthOutcomeType.USER_CREATED,
                created_users=created_users,
            )

        state = (await self._data.get_user_states(user_ref))[user_ref]
        if not supports_growth_mode(state.length, mode):
            return GrowthOutcome(GrowthOutcomeType.WRONG_STATE)

        if active_challenge(state):
            return GrowthOutcome(GrowthOutcomeType.ACTOR_CHALLENGING)

        if not await self._cooldown.cd_check(user_ref):
            remaining = round(
                self._cooldown.dj_cd_time
                - (time.time() - self._cooldown.cd_data[user_ref]),
                3,
            )
            return GrowthOutcome(
                GrowthOutcomeType.COOLING_DOWN,
                remaining=remaining,
            )

        self._cooldown.cd_data[user_ref] = time.time()
        random_num = get_random_num()
        settlement = await self._data.settle_growth(
            user_ref,
            mode,
            random_num=random_num,
        )
        return GrowthOutcome(
            GrowthOutcomeType.COMPLETED,
            amount=settlement.amount,
            new_length=settlement.final.length,
            challenge=settlement.challenge
            if settlement.status == "challenge_started_low_win"
            else None,
            unlocked_users={user_ref: settlement.final.challenge_tier}
            if settlement.final.challenge_tier > state.challenge_tier
            else {},
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

        async with self._state_lock:
            return await self._grow_target(user_ref, target_ref, mode)

    async def _grow_target(
        self,
        user_ref: UserRef,
        target_ref: UserRef,
        mode: GrowthMode,
    ) -> GrowthOutcome:
        created_users = await self._create_missing_users(user_ref, target_ref)
        if created_users:
            return GrowthOutcome(
                GrowthOutcomeType.USER_CREATED,
                created_users=created_users,
            )

        states = await self._data.get_user_states(user_ref, target_ref)
        actor_state = states[user_ref]
        target_state = states[target_ref]
        if not supports_growth_mode(target_state.length, mode):
            return GrowthOutcome(GrowthOutcomeType.WRONG_STATE)

        if supports_growth_mode(actor_state.length, mode) and active_challenge(
            actor_state
        ):
            return GrowthOutcome(GrowthOutcomeType.ACTOR_CHALLENGING)
        if active_challenge(target_state):
            return GrowthOutcome(GrowthOutcomeType.TARGET_CHALLENGING)

        if not await self._cooldown.suo_cd_check(user_ref):
            remaining = round(
                self._cooldown.suo_cd_time
                - (time.time() - self._cooldown.suo_cd_data[user_ref]),
                3,
            )
            return GrowthOutcome(
                GrowthOutcomeType.COOLING_DOWN,
                remaining=remaining,
            )

        self._cooldown.suo_cd_data[user_ref] = time.time()
        random_num = get_random_num()
        settlement = await self._data.settle_growth(
            target_ref,
            mode,
            random_num=random_num,
        )
        return GrowthOutcome(
            GrowthOutcomeType.COMPLETED,
            amount=settlement.amount,
            new_length=settlement.final.length,
            challenge=settlement.challenge
            if settlement.status == "challenge_started_low_win"
            else None,
            unlocked_users={target_ref: settlement.final.challenge_tier}
            if settlement.final.challenge_tier > target_state.challenge_tier
            else {},
        )

    async def query_user(
        self,
        scene_ref: SceneRef,
        requester_ref: UserRef,
        target_ref: UserRef,
        *,
        history: bool = False,
    ) -> QueryOutcome:
        if not await self._data.is_scene_enabled(scene_ref):
            return QueryOutcome(QueryOutcomeType.DISABLED)

        async with self._state_lock:
            created_users = await self._create_missing_users(requester_ref, target_ref)
        if created_users:
            return QueryOutcome(
                QueryOutcomeType.USER_CREATED,
                created_users=created_users,
            )

        data = await self._data.get_user_query_data(target_ref, history=history)
        if data is None:
            raise LookupError("query target does not exist")
        return QueryOutcome(
            QueryOutcomeType.COMPLETED,
            length=data.length,
            challenge_tier=data.challenge_tier,
            state=classify_length(data.length, challenge_tier=data.challenge_tier),
            today_total=data.today_total,
            history_total=round(sum(data.records.values()), 3) if history else None,
            history=data.records if history else {},
        )

    async def query_ranking(
        self,
        scene_ref: SceneRef,
        user_ref: UserRef,
    ) -> RankingOutcome:
        if not await self._data.is_scene_enabled(scene_ref):
            return RankingOutcome(RankingOutcomeType.DISABLED)
        async with self._state_lock:
            ranking = [
                RankingEntry(user=user, length=length)
                for user, length in await self._data.get_ranking(user_ref.namespace)
            ]
            if len(ranking) < 5:
                return RankingOutcome(RankingOutcomeType.TOO_FEW)
            indexes = [
                index for index, item in enumerate(ranking) if item.user == user_ref
            ]
            if not indexes:
                await self._data.add_new_user(user_ref)
                return RankingOutcome(RankingOutcomeType.USER_CREATED)
        return RankingOutcome(
            RankingOutcomeType.COMPLETED,
            ranking=ranking,
            index=indexes[0],
        )

    async def _check_interaction_cooldown(self, user_ref: UserRef) -> InteractionGuard:
        if not await self._cooldown.fuck_cd_check(user_ref):
            remaining = round(
                self._cooldown.fuck_cd_time
                - (time.time() - self._cooldown.ejaculation_cd[user_ref]),
                3,
            )
            return InteractionGuard(
                InteractionGuardType.COOLING_DOWN, remaining=remaining
            )
        return InteractionGuard(InteractionGuardType.ALLOWED)

    async def prepare_interaction(
        self, scene_ref: SceneRef, user_ref: UserRef
    ) -> InteractionGuard:
        if not await self._data.is_scene_enabled(scene_ref):
            return InteractionGuard(InteractionGuardType.DISABLED)
        async with self._state_lock:
            created_users = await self._create_missing_users(user_ref)
            if created_users:
                return InteractionGuard(
                    InteractionGuardType.USER_CREATED, created_users=created_users
                )
            return await self._check_interaction_cooldown(user_ref)

    async def begin_interaction(
        self,
        user_ref: UserRef,
        target_ref: UserRef,
        requested_action: InteractionAction,
    ) -> InteractionResolution | InteractionGuard:
        """在选定目标后复核冷却，固定本次动作与数量档位。

        Returns:
            已开始的互动，或被并发请求占用冷却后的拒绝结果。

        Raises:
            ValueError: 目标与发起者相同。
        """
        if target_ref == user_ref:
            raise ValueError("互动目标不能是发起者")
        async with self._state_lock:
            guard = await self._check_interaction_cooldown(user_ref)
            if guard.type is not InteractionGuardType.ALLOWED:
                return guard
            await self._create_missing_users(target_ref)
            states = await self._data.get_user_states(user_ref, target_ref)
            resolution = resolve_interaction(
                requested_action, states[user_ref].length, states[target_ref].length
            )
            self._cooldown.record_interaction(user_ref)
            return resolution

    async def complete_interaction(
        self,
        user_ref: UserRef,
        lucky_user_ref: UserRef,
        resolution: InteractionResolution,
    ) -> InteractionResult:
        volumes = {
            transfer.recipient: round(random.uniform(1, transfer.max_volume), 3)
            for transfer in resolution.transfers
        }
        seconds = random.randint(1, 20)
        participants = {
            InteractionParticipant.REQUESTER: user_ref,
            InteractionParticipant.TARGET: lucky_user_ref,
        }
        recipients = [part for part in participants if part in volumes]
        async with self._state_lock:
            states = await self._data.get_user_states(
                *(participants[part] for part in recipients)
            )
            entries = {
                participants[part]: (
                    volumes[part],
                    random.random()
                    if is_xnn(states[participants[part]].length)
                    else None,
                )
                for part in recipients
            }
            settlements = await self._data.settle_interaction_volumes(entries)
        return InteractionResult(
            resolution=resolution,
            seconds=seconds,
            receipts={
                part: InteractionReceipt(volumes[part], settlements[participants[part]])
                for part in recipients
            },
        )

    async def set_scene_enabled(
        self,
        scene_ref: SceneRef,
        enabled: bool,
    ) -> None:
        await self._data.set_scene_enabled(scene_ref, enabled)
