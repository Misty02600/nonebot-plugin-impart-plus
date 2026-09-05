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
class UserGameState:
    length: float
    win_probability: float
    is_challenging: bool
    challenge_completed: bool


@dataclass(frozen=True, slots=True)
class StateEvaluation:
    status: str
    state: UserGameState
    possession_unlocked: bool = False


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
    target_status: str


@dataclass(frozen=True, slots=True)
class PkResolution:
    won: bool
    length_increase: float
    length_decrease: float


@dataclass(frozen=True, slots=True)
class PkParticipantSettlement:
    before: UserGameState
    base: UserGameState
    final: UserGameState
    status: str


@dataclass(frozen=True, slots=True)
class PkSettlement:
    mode: GrowthMode
    resolution: PkResolution
    attacker: PkParticipantSettlement
    defender: PkParticipantSettlement


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


def classify_length(length: float, *, challenge_completed: bool = False) -> LengthState:
    if length >= 30 or (challenge_completed and length >= 25):
        return LengthState.GOD
    if length <= -30 or (challenge_completed and length <= -25):
        return LengthState.ABYSS_LORD
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


def evaluate_user_state(state: UserGameState) -> StateEvaluation:
    magnitude = abs(state.length)
    penalty = 5 if state.length <= 0 else -5
    if (
        not state.is_challenging
        and not state.challenge_completed
        and 25 <= magnitude < 30
    ):
        return StateEvaluation(
            "challenge_started_low_win",
            replace(
                state,
                is_challenging=True,
                win_probability=state.win_probability * 0.8,
            ),
        )
    if not state.is_challenging and not state.challenge_completed and magnitude >= 30:
        return StateEvaluation(
            "challenge_completed",
            replace(state, challenge_completed=True),
            possession_unlocked=state.length < 0,
        )
    if state.is_challenging and not state.challenge_completed and magnitude < 25:
        return StateEvaluation(
            "challenge_failed_high_win",
            replace(
                state,
                length=apply_world_locked_delta(state.length, penalty),
                win_probability=state.win_probability * 1.25,
                is_challenging=False,
            ),
        )
    if state.is_challenging and not state.challenge_completed and magnitude >= 30:
        return StateEvaluation(
            "challenge_success_high_win",
            replace(
                state,
                win_probability=state.win_probability * 1.25,
                is_challenging=False,
                challenge_completed=True,
            ),
            possession_unlocked=state.length < 0,
        )
    if state.is_challenging and 25 <= magnitude < 30:
        return StateEvaluation("is_challenging", state)
    if state.challenge_completed and 25 <= magnitude < 30:
        return StateEvaluation("challenge_completed", state)
    if state.challenge_completed and magnitude < 25:
        return StateEvaluation(
            "challenge_completed_reduce",
            replace(
                state,
                length=apply_world_locked_delta(state.length, penalty),
                challenge_completed=False,
            ),
        )
    return StateEvaluation("", state)


def crossed_challenge_threshold(current_length: float, new_length: float) -> bool:
    return abs(current_length) < 25 <= abs(new_length)


def resolve_possession(
    actor: UserGameState, target: UserGameState
) -> PossessionSettlement | PossessionStatus:
    """检查夺舍资格并平分目标长度，只有目标承担既有称号惩罚。

    Returns:
        拒绝原因，或含双方最终状态的结算；发起者直接按半长决定完成标记。
    """
    if actor.length >= 0 or not actor.challenge_completed:
        return PossessionStatus.LOCKED
    if target.length <= 0:
        return PossessionStatus.WRONG_TARGET
    if target.is_challenging:
        return PossessionStatus.TARGET_CHALLENGING
    if target.length >= abs(actor.length):
        return PossessionStatus.TARGET_TOO_LONG

    half = ((round(target.length * 1000) + 1) // 2) / 1000
    new_actor = replace(
        actor,
        length=half,
        is_challenging=False,
        challenge_completed=half >= 25,
    )
    new_target = replace(target, length=half)
    if half >= 25:
        new_target = replace(new_target, challenge_completed=True)
    target_evaluation = evaluate_user_state(new_target)
    return PossessionSettlement(
        half=half,
        actor=new_actor,
        target=target_evaluation.state,
        target_status=target_evaluation.status,
    )


def _apply_pk_delta(
    state: UserGameState,
    length_delta: float,
    probability_delta: float,
) -> tuple[UserGameState, bool]:
    unlocked_length = round(state.length + length_delta, 3)
    length = apply_world_locked_delta(state.length, length_delta)
    return replace(
        state,
        length=length,
        win_probability=round(state.win_probability + probability_delta, 3),
    ), length != unlocked_length


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
    defender: UserGameState,
    *,
    win_roll: float,
    random_num: float,
) -> PkSettlement:
    """按现有规则一次计算 PK 双方的完整最终状态。

    Args:
        attacker: 发起者结算前的完整游戏状态。
        defender: 目标结算前的完整游戏状态。
        win_roll: 已由应用层生成的胜负随机值。
        random_num: 已由应用层生成的长度变化随机值。

    Returns:
        包含双方基础变化、挑战处理后状态和状态事件的纯结算结果。

    Raises:
        ValueError: 双方不属于同一个正负世界。
    """
    mode = GrowthMode.LENGTH if attacker.length > 0 else GrowthMode.DEPTH
    if not supports_growth_mode(defender.length, mode):
        raise ValueError("PK participants must belong to the same world")

    resolution = PkResolution(
        won=win_roll < attacker.win_probability,
        length_increase=round(random_num / 2, 3),
        length_decrease=random_num,
    )
    direction = 1 if mode is GrowthMode.LENGTH else -1
    attacker_probability_delta = -0.01 if resolution.won else 0.01
    attacker_length_delta = direction * (
        random_num / 2 if resolution.won else -random_num
    )
    defender_length_delta = direction * (
        -random_num if resolution.won else random_num / 2
    )
    attacker_base, attacker_locked = _apply_pk_delta(
        attacker,
        attacker_length_delta,
        attacker_probability_delta,
    )
    defender_base, defender_locked = _apply_pk_delta(
        defender,
        defender_length_delta,
        -attacker_probability_delta,
    )
    attacker_evaluation = evaluate_user_state(attacker_base)
    defender_evaluation = evaluate_user_state(defender_base)
    loser_before = defender if resolution.won else attacker
    loser_base = defender_base if resolution.won else attacker_base
    loser_locked = defender_locked if resolution.won else attacker_locked
    if loser_locked:
        resolution = replace(
            resolution,
            length_decrease=round(abs(loser_before.length - loser_base.length), 3),
        )
    attacker_status = attacker_evaluation.status
    if (
        not attacker_status
        and not is_xnn(attacker.length)
        and is_xnn(attacker_evaluation.state.length)
    ):
        attacker_status = "length_near_zero"
    defender_status = defender_evaluation.status
    if (
        not defender_status
        and not is_xnn(defender.length)
        and is_xnn(defender_evaluation.state.length)
    ):
        defender_status = "length_near_zero"
    return PkSettlement(
        mode=mode,
        resolution=resolution,
        attacker=PkParticipantSettlement(
            before=attacker,
            base=attacker_base,
            final=attacker_evaluation.state,
            status=attacker_status,
        ),
        defender=PkParticipantSettlement(
            before=defender,
            base=defender_base,
            final=defender_evaluation.state,
            status=defender_status,
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
