"""框架无关的游戏规则。"""

from dataclasses import dataclass, replace
from enum import StrEnum


class LengthState(StrEnum):
    GOD = "god"
    ABYSS_LORD = "abyss_lord"
    NORMAL = "normal"
    XNN = "xnn"
    GIRL = "girl"


class GrowthMode(StrEnum):
    LENGTH = "length"
    DEPTH = "depth"


class InteractionAction(StrEnum):
    INJECT = "透"
    SQUEEZE = "榨"
    CUDDLE = "贴贴"


class InteractionParticipant(StrEnum):
    REQUESTER = "requester"
    TARGET = "target"


class InteractionFluid(StrEnum):
    DNA = "脱氧核糖核酸"
    GIRL_JUICE = "妹汁"


class InteractionReversal(StrEnum):
    NONE = "none"
    WRONG_ACTION = "wrong_action"
    XNN = "xnn"


@dataclass(frozen=True, slots=True)
class ChallengeTier:
    tier: int
    entry: float
    target: float
    win_multiplier: float
    recovery_multiplier: float
    penalty: float


CHALLENGE_TIERS = (
    ChallengeTier(
        tier=1,
        entry=25,
        target=30,
        win_multiplier=0.9,
        recovery_multiplier=10 / 9,
        penalty=5,
    ),
    ChallengeTier(2, 300, 320, 0.8, 1.25, 20),
    ChallengeTier(3, 1000, 1050, 0.7, 10 / 7, 50),
)


@dataclass(frozen=True, slots=True)
class UserGameState:
    length: float
    win_probability: float
    challenge_tier: int = 0


@dataclass(frozen=True, slots=True)
class StateEvaluation:
    status: str
    state: UserGameState
    challenge: ChallengeTier | None = None


class PossessionStatus(StrEnum):
    DISABLED = "disabled"
    MISSING_TARGET = "missing_target"
    USERS_CREATED = "users_created"
    LOCKED = "locked"
    WRONG_TARGET = "wrong_target"
    TARGET_CHALLENGING = "target_challenging"
    TARGET_TOO_LONG = "target_too_long"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class PossessionSettlement:
    half: float
    actor: UserGameState
    target: UserGameState
    target_challenge: ChallengeTier | None = None


@dataclass(frozen=True, slots=True)
class PkParticipantSettlement:
    before: UserGameState
    base: UserGameState
    final: UserGameState
    status: str
    challenge: ChallengeTier | None = None

    @property
    def length_change(self) -> float:
        return round(abs(self.base.length) - abs(self.before.length), 3)


@dataclass(frozen=True, slots=True)
class PkSettlement:
    mode: GrowthMode
    won: bool
    attacker: PkParticipantSettlement
    defenders: tuple[PkParticipantSettlement, ...]


@dataclass(frozen=True, slots=True)
class GrowthSettlement:
    amount: float
    final: UserGameState
    status: str
    challenge: ChallengeTier | None = None


@dataclass(frozen=True, slots=True)
class InteractionTransfer:
    source: InteractionParticipant
    recipient: InteractionParticipant
    fluid: InteractionFluid
    max_volume: float


@dataclass(frozen=True, slots=True)
class InteractionResolution:
    action: InteractionAction
    reversal: InteractionReversal
    transfers: tuple[InteractionTransfer, ...]


FEMINIZATION_WARNING_VOLUME = 200.0
FEMINIZATION_CERTAIN_VOLUME = 1000.0
FEMINIZATION_LENGTH_LOSS = 5.0


@dataclass(frozen=True, slots=True)
class InteractionVolumeSettlement:
    total: float
    length: float
    risk_warning: bool
    feminized: bool


def is_xnn(length: float) -> bool:
    return 0 < length < 5


def classify_length(length: float, *, challenge_tier: int = 0) -> LengthState:
    if challenge_tier > 0:
        return LengthState.GOD if length > 0 else LengthState.ABYSS_LORD
    if length >= 5:
        return LengthState.NORMAL
    if is_xnn(length):
        return LengthState.XNN
    return LengthState.GIRL


def supports_growth_mode(length: float, mode: GrowthMode) -> bool:
    if mode is GrowthMode.LENGTH:
        return length > 0
    return length <= 0


def growth_delta(amount: float, mode: GrowthMode) -> float:
    if mode is GrowthMode.LENGTH:
        return amount
    return -amount


def apply_world_locked_delta(length: float, delta: float) -> float:
    """应用三位小数增量，并阻止普通玩法跨过零点。"""
    candidate = round(length + delta, 3)
    if length > 0 and candidate <= 0:
        return 0.001
    if length < 0 and candidate >= 0:
        return -0.001
    return candidate


def challenge_tier_rule(
    tier: int,
    tiers: tuple[ChallengeTier, ...] = CHALLENGE_TIERS,
) -> ChallengeTier | None:
    return next((rule for rule in tiers if rule.tier == tier), None)


def active_challenge(
    state: UserGameState,
    tiers: tuple[ChallengeTier, ...] = CHALLENGE_TIERS,
) -> ChallengeTier | None:
    rule = challenge_tier_rule(state.challenge_tier + 1, tiers)
    if rule and rule.entry <= abs(state.length) < rule.target:
        return rule
    return None


def tier_for_magnitude(
    magnitude: float,
    tiers: tuple[ChallengeTier, ...] = CHALLENGE_TIERS,
) -> int:
    return max((rule.tier for rule in tiers if magnitude >= rule.entry), default=0)


def personal_length_multiplier(state: UserGameState) -> float:
    return 0.5 if is_xnn(state.length) else float(state.challenge_tier + 1)


def effective_pk_probability(length: float, win_probability: float) -> float:
    return win_probability * 0.5 if is_xnn(length) else win_probability


def pk_target_limit(state: UserGameState) -> int:
    return state.challenge_tier + 1


def evaluate_state_transition(
    before: UserGameState,
    base: UserGameState,
    tiers: tuple[ChallengeTier, ...] = CHALLENGE_TIERS,
) -> StateEvaluation:
    """从一次基础数值变化的前后状态计算挑战事件和最终状态。"""
    if before.challenge_tier != base.challenge_tier:
        raise ValueError("base state must preserve challenge tier")

    before_challenge = active_challenge(before, tiers)
    magnitude = abs(base.length)
    if before_challenge:
        if magnitude >= before_challenge.target:
            return StateEvaluation(
                "challenge_success_high_win",
                replace(
                    base,
                    challenge_tier=before_challenge.tier,
                    win_probability=(
                        base.win_probability * before_challenge.recovery_multiplier
                    ),
                ),
                challenge=before_challenge,
            )
        if magnitude < before_challenge.entry:
            penalty = (
                before_challenge.penalty
                if base.length < 0
                else -before_challenge.penalty
            )
            return StateEvaluation(
                "challenge_failed_high_win",
                replace(
                    base,
                    length=apply_world_locked_delta(base.length, penalty),
                    win_probability=(
                        base.win_probability * before_challenge.recovery_multiplier
                    ),
                ),
                challenge=before_challenge,
            )
        return StateEvaluation("is_challenging", base)

    held_rule = challenge_tier_rule(before.challenge_tier, tiers)
    if held_rule and magnitude < held_rule.entry:
        penalty = held_rule.penalty if base.length < 0 else -held_rule.penalty
        length = apply_world_locked_delta(base.length, penalty)
        return StateEvaluation(
            "challenge_completed_reduce",
            replace(
                base,
                length=length,
                challenge_tier=tier_for_magnitude(abs(length), tiers),
            ),
            challenge=held_rule,
        )

    next_rule = challenge_tier_rule(before.challenge_tier + 1, tiers)
    if next_rule and magnitude >= next_rule.target:
        return StateEvaluation(
            "challenge_completed",
            replace(base, challenge_tier=next_rule.tier),
            challenge=next_rule,
        )
    if next_rule and magnitude >= next_rule.entry:
        return StateEvaluation(
            "challenge_started_low_win",
            replace(
                base,
                win_probability=base.win_probability * next_rule.win_multiplier,
            ),
            challenge=next_rule,
        )
    return StateEvaluation("", base)


def resolve_growth_settlement(
    state: UserGameState,
    mode: GrowthMode,
    random_num: float,
    tiers: tuple[ChallengeTier, ...] = CHALLENGE_TIERS,
) -> GrowthSettlement:
    if not supports_growth_mode(state.length, mode):
        raise ValueError("growth mode does not match user world")
    amount = random_num * personal_length_multiplier(state)
    base = replace(
        state,
        length=apply_world_locked_delta(state.length, growth_delta(amount, mode)),
    )
    evaluation = evaluate_state_transition(state, base, tiers)
    return GrowthSettlement(
        amount=round(abs(base.length) - abs(state.length), 3),
        final=evaluation.state,
        status=evaluation.status,
        challenge=evaluation.challenge,
    )


def resolve_possession(
    actor: UserGameState,
    target: UserGameState,
    tiers: tuple[ChallengeTier, ...] = CHALLENGE_TIERS,
) -> PossessionSettlement | PossessionStatus:
    """检查夺舍资格并平分目标长度，只有目标承担既有称号惩罚。

    Returns:
        拒绝原因，或含双方最终状态的结算；发起者直接按半长决定持有阶级。
    """
    if actor.length >= 0 or actor.challenge_tier < 1:
        return PossessionStatus.LOCKED
    if target.length <= 0:
        return PossessionStatus.WRONG_TARGET
    if active_challenge(target, tiers):
        return PossessionStatus.TARGET_CHALLENGING
    if target.length >= abs(actor.length):
        return PossessionStatus.TARGET_TOO_LONG

    half = ((round(target.length * 1000) + 1) // 2) / 1000
    actor_probability = actor.win_probability
    if actor_challenge := active_challenge(actor, tiers):
        actor_probability *= actor_challenge.recovery_multiplier
    new_actor = replace(
        actor,
        length=half,
        win_probability=actor_probability,
        challenge_tier=tier_for_magnitude(half, tiers),
    )
    target_tier = tier_for_magnitude(half, tiers)
    new_target = replace(target, length=half, challenge_tier=target_tier)
    target_challenge = None
    if target_tier < target.challenge_tier:
        held_rule = challenge_tier_rule(target.challenge_tier, tiers)
        if held_rule is None:
            raise ValueError("target challenge tier has no rule")
        length = apply_world_locked_delta(half, -held_rule.penalty)
        new_target = replace(
            new_target,
            length=length,
            challenge_tier=tier_for_magnitude(abs(length), tiers),
        )
        target_challenge = held_rule
    return PossessionSettlement(
        half=half,
        actor=new_actor,
        target=new_target,
        target_challenge=target_challenge,
    )


def _settle_pk_participant(
    state: UserGameState,
    progress_delta: float,
    probability_delta: float,
    tiers: tuple[ChallengeTier, ...],
) -> PkParticipantSettlement:
    progress_delta *= personal_length_multiplier(state)
    direction = 1 if state.length > 0 else -1
    base = replace(
        state,
        length=apply_world_locked_delta(
            state.length,
            direction * progress_delta,
        ),
        win_probability=round(state.win_probability + probability_delta, 3),
    )
    evaluation = evaluate_state_transition(state, base, tiers)
    status = evaluation.status
    if not status and not is_xnn(state.length) and is_xnn(evaluation.state.length):
        status = "length_near_zero"
    return PkParticipantSettlement(
        state, base, evaluation.state, status, evaluation.challenge
    )


def feminization_probability(total: float) -> float:
    return min(
        1.0,
        max(
            0.0,
            (total - FEMINIZATION_WARNING_VOLUME)
            / (FEMINIZATION_CERTAIN_VOLUME - FEMINIZATION_WARNING_VOLUME),
        ),
    )


def resolve_interaction_volume(
    current_length: float,
    previous_total: float,
    amount: float,
    *,
    feminization_roll: float | None,
) -> InteractionVolumeSettlement:
    """累计一次收到的互动量，并计算当前 XNN 是否雌堕。"""
    total = round(previous_total + amount, 3)
    if feminization_roll is not None and is_xnn(current_length):
        feminized = feminization_roll < feminization_probability(total)
        risk_warning = (
            not feminized and previous_total <= FEMINIZATION_WARNING_VOLUME < total
        )
    else:
        feminized = False
        risk_warning = False
    length = (
        round(current_length - FEMINIZATION_LENGTH_LOSS, 3)
        if feminized
        else current_length
    )
    return InteractionVolumeSettlement(
        total=total,
        length=length,
        risk_warning=risk_warning,
        feminized=feminized,
    )


def resolve_pk_settlement(
    attacker: UserGameState,
    defenders: tuple[UserGameState, ...],
    *,
    win_roll: float,
    random_num: float,
    tiers: tuple[ChallengeTier, ...] = CHALLENGE_TIERS,
) -> PkSettlement:
    """用一次胜负与基础量结算发起者和本局选定的所有目标。

    Args:
        attacker: 发起者结算前的完整游戏状态。
        defenders: 按At顺序排列的目标结算前状态。
        win_roll: 已由应用层生成的胜负随机值。
        random_num: 已由应用层生成的长度变化随机值。

    Returns:
        包含所有参与者基础变化、挑战处理后状态和状态事件的纯结算结果。

    Raises:
        ValueError: 没有目标，或参与者不属于同一个正负世界。
    """
    if not defenders:
        raise ValueError("PK requires at least one defender")
    mode = GrowthMode.LENGTH if attacker.length > 0 else GrowthMode.DEPTH
    if any(not supports_growth_mode(defender.length, mode) for defender in defenders):
        raise ValueError("PK participants must belong to the same world")

    won = win_roll < effective_pk_probability(attacker.length, attacker.win_probability)
    attacker_probability_delta = -0.01 if won else 0.01
    attacker_progress = (
        random_num / 2 * len(defenders) if won else -random_num * len(defenders)
    )
    defender_progress = -random_num if won else random_num / 2
    return PkSettlement(
        mode=mode,
        won=won,
        attacker=_settle_pk_participant(
            attacker,
            attacker_progress,
            attacker_probability_delta,
            tiers,
        ),
        defenders=tuple(
            _settle_pk_participant(
                defender,
                defender_progress,
                -attacker_probability_delta,
                tiers,
            )
            for defender in defenders
        ),
    )


def _preferred_interaction(
    actor_length: float, other_length: float
) -> InteractionAction:
    if actor_length >= 5 or (is_xnn(actor_length) and other_length <= 0):
        return InteractionAction.INJECT
    return InteractionAction.SQUEEZE


def resolve_interaction(
    requested_action: InteractionAction,
    requester_length: float,
    target_length: float,
) -> InteractionResolution:
    """按双方开始时的状态固定动作、流向与数量档位。

    Note:
        双 XNN 优先贴贴；其他错误动作由目标反制一次。透由行动者输出，
        榨由另一方输出；贴贴依次为发起者向目标、目标向发起者。

    Raises:
        ValueError: 将仅由状态触发的贴贴作为主动命令。
    """
    if requested_action is InteractionAction.CUDDLE:
        raise ValueError("贴贴只能由双方 XNN 状态触发")
    requester = InteractionParticipant.REQUESTER
    target = InteractionParticipant.TARGET
    if is_xnn(requester_length) and is_xnn(target_length):
        return InteractionResolution(
            InteractionAction.CUDDLE,
            InteractionReversal.NONE,
            (
                InteractionTransfer(requester, target, InteractionFluid.DNA, 10),
                InteractionTransfer(target, requester, InteractionFluid.DNA, 10),
            ),
        )

    if requested_action is _preferred_interaction(requester_length, target_length):
        action = requested_action
        actor, other = requester, target
        actor_length, other_length = requester_length, target_length
        reversal = InteractionReversal.NONE
    else:
        action = _preferred_interaction(target_length, requester_length)
        actor, other = target, requester
        actor_length, other_length = target_length, requester_length
        reversal = (
            InteractionReversal.XNN
            if is_xnn(requester_length)
            else InteractionReversal.WRONG_ACTION
        )

    if action is InteractionAction.INJECT:
        transfer = InteractionTransfer(
            actor, other, InteractionFluid.DNA, 10 if is_xnn(actor_length) else 100
        )
    else:
        transfer = InteractionTransfer(
            other,
            actor,
            InteractionFluid.DNA if other_length > 0 else InteractionFluid.GIRL_JUICE,
            100,
        )
    return InteractionResolution(action, reversal, (transfer,))
