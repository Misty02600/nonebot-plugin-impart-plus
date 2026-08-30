"""游戏用例编排。"""

import random
import time
from dataclasses import dataclass, field
from enum import StrEnum

from ..infra.cooldown import CooldownManager
from ..infra.data_manager import (
    add_new_user,
    check_group_allow,
    get_ejaculation_data,
    get_jj_length,
    get_sorted,
    get_today_ejaculation_data,
    get_win_probability,
    insert_ejaculation,
    is_in_table,
    punish_all_inactive_users,
    set_group_allow,
    set_jj_length,
    set_win_probability,
    update_activity,
    update_challenge_status,
)
from .core import (
    LengthState,
    PkResolution,
    classify_length,
    crossed_challenge_threshold,
    resolve_pk,
    should_reverse_injection,
)


class PkOutcomeType(StrEnum):
    DISABLED = "disabled"
    COOLING_DOWN = "cooling_down"
    SELF_TARGET = "self_target"
    USERS_CREATED = "users_created"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class PkOutcome:
    type: PkOutcomeType
    remaining: float = 0
    resolution: PkResolution | None = None
    attacker_status: str = ""
    defender_status: str = ""
    attacker_probability: float = 0.5


class GrowthOutcomeType(StrEnum):
    DISABLED = "disabled"
    COOLING_DOWN = "cooling_down"
    USER_CREATED = "user_created"
    CHALLENGING = "challenging"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class GrowthOutcome:
    type: GrowthOutcomeType
    remaining: float = 0
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
    length: float = 0
    state: LengthState = LengthState.NORMAL


class RankingOutcomeType(StrEnum):
    DISABLED = "disabled"
    TOO_FEW = "too_few"
    USER_CREATED = "user_created"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class RankingOutcome:
    type: RankingOutcomeType
    ranking: list[dict] = field(default_factory=list)
    index: int = 0


class InteractionGuardType(StrEnum):
    DISABLED = "disabled"
    COOLING_DOWN = "cooling_down"
    ALLOWED = "allowed"


@dataclass(frozen=True, slots=True)
class InteractionGuard:
    type: InteractionGuardType
    remaining: float = 0


@dataclass(frozen=True, slots=True)
class InteractionResult:
    reversed: bool
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


class GameApplication:
    def __init__(
        self,
        cooldown: CooldownManager,
        *,
        penalties_enabled: bool,
    ) -> None:
        self._cooldown = cooldown
        self._penalties_enabled = penalties_enabled

    async def penalties_and_resets(self) -> None:
        if self._penalties_enabled:
            await punish_all_inactive_users()

    async def execute_pk(
        self,
        group_id: int,
        attacker_id: str,
        defender_id: str,
    ) -> PkOutcome:
        await self.penalties_and_resets()
        if not await check_group_allow(group_id):
            return PkOutcome(PkOutcomeType.DISABLED)

        if not await self._cooldown.pkcd_check(attacker_id):
            remaining = round(
                self._cooldown.pk_cd_time
                - (time.time() - self._cooldown.pk_cd_data[attacker_id]),
                3,
            )
            return PkOutcome(PkOutcomeType.COOLING_DOWN, remaining=remaining)

        self._cooldown.pk_cd_data.update({attacker_id: time.time()})
        if defender_id == attacker_id:
            return PkOutcome(PkOutcomeType.SELF_TARGET)

        attacker = int(attacker_id)
        defender = int(defender_id)
        if await is_in_table(attacker) and await is_in_table(defender):
            win_roll = random.random()
            win_probability = await get_win_probability(attacker)
            resolution = resolve_pk(
                win_probability,
                win_roll=win_roll,
                random_num=get_random_num(),
            )
            if resolution.won:
                await set_win_probability(attacker, -0.01)
                await set_win_probability(defender, 0.01)
                await set_jj_length(attacker, resolution.random_num / 2)
                await set_jj_length(defender, -resolution.random_num)
            else:
                await set_win_probability(attacker, 0.01)
                await set_win_probability(defender, -0.01)
                await set_jj_length(attacker, -resolution.random_num)
                await set_jj_length(defender, resolution.random_num / 2)

            attacker_status = await update_challenge_status(attacker)
            defender_status = await update_challenge_status(defender)
            probability = await get_win_probability(attacker)
            return PkOutcome(
                PkOutcomeType.COMPLETED,
                resolution=resolution,
                attacker_status=attacker_status,
                defender_status=defender_status,
                attacker_probability=probability,
            )

        if not await is_in_table(attacker):
            await add_new_user(attacker)
        if not await is_in_table(defender):
            await add_new_user(defender)
        del self._cooldown.pk_cd_data[attacker_id]
        return PkOutcome(PkOutcomeType.USERS_CREATED)

    async def grow_self(self, group_id: int, user_id: str) -> GrowthOutcome:
        await self.penalties_and_resets()
        if not await check_group_allow(group_id):
            return GrowthOutcome(GrowthOutcomeType.DISABLED)

        if not await self._cooldown.cd_check(user_id):
            remaining = round(
                self._cooldown.dj_cd_time
                - (time.time() - self._cooldown.cd_data[user_id]),
                3,
            )
            return GrowthOutcome(GrowthOutcomeType.COOLING_DOWN, remaining=remaining)

        self._cooldown.cd_data[user_id] = time.time()
        uid = int(user_id)
        if not await is_in_table(uid):
            await add_new_user(uid)
            return GrowthOutcome(GrowthOutcomeType.USER_CREATED)

        current_length = await get_jj_length(uid)
        random_num = get_random_num()
        status = await update_challenge_status(uid)
        if "is_challenging" in status:
            return GrowthOutcome(
                GrowthOutcomeType.CHALLENGING,
                random_num=random_num,
            )

        await set_jj_length(uid, random_num)
        new_length = await get_jj_length(uid)
        challenge_started = crossed_challenge_threshold(current_length, new_length)
        if challenge_started:
            await update_challenge_status(uid)
        else:
            new_length = await get_jj_length(uid)
        return GrowthOutcome(
            GrowthOutcomeType.COMPLETED,
            random_num=random_num,
            new_length=new_length,
            challenge_started=challenge_started,
        )

    async def grow_target(
        self,
        group_id: int,
        user_id: str,
        target_id: int,
    ) -> GrowthOutcome:
        await self.penalties_and_resets()
        if not await check_group_allow(group_id):
            return GrowthOutcome(GrowthOutcomeType.DISABLED)

        if not await self._cooldown.suo_cd_check(user_id):
            remaining = round(
                self._cooldown.suo_cd_time
                - (time.time() - self._cooldown.suo_cd_data[user_id]),
                3,
            )
            return GrowthOutcome(GrowthOutcomeType.COOLING_DOWN, remaining=remaining)

        self._cooldown.suo_cd_data[user_id] = time.time()
        if not await is_in_table(target_id):
            await add_new_user(target_id)
            del self._cooldown.suo_cd_data[user_id]
            return GrowthOutcome(GrowthOutcomeType.USER_CREATED)

        current_length = await get_jj_length(target_id)
        random_num = get_random_num()
        status = await update_challenge_status(target_id)
        if "is_challenging" in status:
            return GrowthOutcome(
                GrowthOutcomeType.CHALLENGING,
                random_num=random_num,
            )

        await set_jj_length(target_id, random_num)
        new_length = await get_jj_length(target_id)
        challenge_started = crossed_challenge_threshold(current_length, new_length)
        if challenge_started:
            await update_challenge_status(target_id)
        return GrowthOutcome(
            GrowthOutcomeType.COMPLETED,
            random_num=random_num,
            new_length=new_length,
            challenge_started=challenge_started,
        )

    async def query_user(self, group_id: int, user_id: int) -> QueryOutcome:
        await self.penalties_and_resets()
        if not await check_group_allow(group_id):
            return QueryOutcome(QueryOutcomeType.DISABLED)
        if not await is_in_table(user_id):
            await add_new_user(user_id)
            return QueryOutcome(QueryOutcomeType.USER_CREATED)
        length = await get_jj_length(user_id)
        return QueryOutcome(
            QueryOutcomeType.COMPLETED,
            length=length,
            state=classify_length(length),
        )

    async def query_ranking(self, group_id: int, user_id: int) -> RankingOutcome:
        if not await check_group_allow(group_id):
            return RankingOutcome(RankingOutcomeType.DISABLED)
        ranking = await get_sorted()
        if len(ranking) < 5:
            return RankingOutcome(RankingOutcomeType.TOO_FEW)
        indexes = [
            index for index, item in enumerate(ranking) if item["userid"] == user_id
        ]
        if not indexes:
            await add_new_user(user_id)
            return RankingOutcome(RankingOutcomeType.USER_CREATED)
        return RankingOutcome(
            RankingOutcomeType.COMPLETED,
            ranking=ranking,
            index=indexes[0],
        )

    async def prepare_interaction(
        self,
        group_id: int,
        user_id: int,
    ) -> InteractionGuard:
        if not await check_group_allow(group_id):
            return InteractionGuard(InteractionGuardType.DISABLED)
        await self.penalties_and_resets()
        if not await check_group_allow(group_id):
            return InteractionGuard(InteractionGuardType.DISABLED)
        uid = str(user_id)
        if not await self._cooldown.fuck_cd_check(uid):
            remaining = round(
                self._cooldown.fuck_cd_time
                - (time.time() - self._cooldown.ejaculation_cd[uid]),
                3,
            )
            return InteractionGuard(
                InteractionGuardType.COOLING_DOWN,
                remaining=remaining,
            )
        self._cooldown.ejaculation_cd.update({uid: time.time()})
        return InteractionGuard(InteractionGuardType.ALLOWED)

    def release_interaction_cooldown(self, user_id: int) -> None:
        del self._cooldown.ejaculation_cd[str(user_id)]

    @staticmethod
    def roll_interaction() -> float:
        return random.uniform(0, 1)

    @staticmethod
    async def get_length(user_id: int) -> float:
        return await get_jj_length(user_id)

    async def complete_interaction(
        self,
        user_id: int,
        lucky_user: int,
        random_nn: float,
    ) -> InteractionResult:
        await update_activity(lucky_user)
        await update_activity(user_id)
        length = await get_jj_length(user_id)
        reversed_interaction = should_reverse_injection(length, random_nn)
        ejaculation = round(random.uniform(1, 100), 3)
        recipient = user_id if reversed_interaction else lucky_user
        await insert_ejaculation(recipient, ejaculation)
        seconds = random.randint(1, 20)
        today_total = await get_today_ejaculation_data(recipient)
        return InteractionResult(
            reversed=reversed_interaction,
            ejaculation=ejaculation,
            today_total=today_total,
            seconds=seconds,
        )

    @staticmethod
    async def set_group_enabled(group_id: int, enabled: bool) -> None:
        await set_group_allow(group_id, enabled)

    async def query_injection(
        self,
        group_id: int,
        user_id: int,
        *,
        history: bool,
    ) -> InjectionQueryResult:
        await self.penalties_and_resets()
        if not await check_group_allow(group_id):
            return InjectionQueryResult(InjectionQueryType.DISABLED)
        data = await get_ejaculation_data(user_id)
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
        total = await get_today_ejaculation_data(user_id)
        return InjectionQueryResult(InjectionQueryType.DAILY, total=total)
