"""框架无关的游戏规则。"""

from dataclasses import dataclass, replace
from enum import StrEnum


class LengthState(StrEnum):
    GOD = "god"
    ABYSS_LORD = "abyss_lord"
    NORMAL = "normal"
    XNN = "xnn"
    NEAR_GIRL = "near_girl"
    GIRL = "girl"


class GrowthMode(StrEnum):
    LENGTH = "length"
    DEPTH = "depth"


class InteractionAction(StrEnum):
    INJECT = "透"
    SQUEEZE = "榨"


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
    is_near_zero: bool
    is_zero_or_negative: bool


@dataclass(frozen=True, slots=True)
class StateEvaluation:
    status: str
    state: UserGameState


@dataclass(frozen=True, slots=True)
class PkResolution:
    won: bool
    random_num: float
    length_increase: float
    length_decrease: float


@dataclass(frozen=True, slots=True)
class InteractionResolution:
    action: InteractionAction
    actor: InteractionParticipant
    recipient: InteractionParticipant
    fluid: InteractionFluid
    reversal: InteractionReversal


def classify_length(length: float) -> LengthState:
    if length >= 30:
        return LengthState.GOD
    if length <= -30:
        return LengthState.ABYSS_LORD
    if length > 5:
        return LengthState.NORMAL
    if length > 1:
        return LengthState.XNN
    if length > 0:
        return LengthState.NEAR_GIRL
    return LengthState.GIRL


def supports_growth_mode(length: float, mode: GrowthMode) -> bool:
    if mode is GrowthMode.LENGTH:
        return length > 0
    return length <= 0


def growth_delta(amount: float, mode: GrowthMode) -> float:
    if mode is GrowthMode.LENGTH:
        return amount
    return -amount


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
        )
    if state.is_challenging and not state.challenge_completed and magnitude < 25:
        return StateEvaluation(
            "challenge_failed_high_win",
            replace(
                state,
                length=state.length + penalty,
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
                length=state.length + penalty,
                challenge_completed=False,
            ),
        )
    if not state.is_near_zero and 0 < state.length <= 5:
        return StateEvaluation(
            "length_near_zero",
            replace(state, is_near_zero=True),
        )
    if state.is_near_zero and (state.length <= 0 or state.length > 5):
        return StateEvaluation("", replace(state, is_near_zero=False))
    if not state.is_zero_or_negative and state.length <= 0:
        return StateEvaluation(
            "length_zero_or_negative",
            replace(state, is_zero_or_negative=True),
        )
    if state.is_zero_or_negative and state.length > 0:
        return StateEvaluation("", replace(state, is_zero_or_negative=False))
    return StateEvaluation("", state)


def crossed_challenge_threshold(current_length: float, new_length: float) -> bool:
    return abs(current_length) < 25 <= abs(new_length)


def resolve_pk(
    win_probability: float,
    *,
    win_roll: float,
    random_num: float,
) -> PkResolution:
    return PkResolution(
        won=win_roll < win_probability,
        random_num=random_num,
        length_increase=round(random_num / 2, 3),
        length_decrease=random_num,
    )


def resolve_interaction(
    requested_action: InteractionAction,
    requester_length: float,
    target_length: float,
    *,
    reverse_roll: float | None,
) -> InteractionResolution:
    """将请求动作解析为最多反制一次的实际互动。

    Args:
        requested_action: 发起者请求的透或榨。
        requester_length: 发起者当前长度；正值与非正值代表两个世界。
        target_length: 目标当前长度，用于确定反制动作与榨取液体。
        reverse_roll: 透命令的 xnn 反制随机值；榨命令传入 ``None``。

    Returns:
        固定实际动作、行动者、液体接收者、液体名称和反制原因的结果。

    Raises:
        ValueError: 透命令缺少反制随机值，或榨命令错误携带该随机值。

    Note:
        动作与发起者世界不匹配时必定反制，目标不会再次触发反制。
    """
    if (requested_action is InteractionAction.INJECT) != (reverse_roll is not None):
        raise ValueError("只有透命令必须提供反制随机值")

    requester_positive = requester_length > 0
    requester_can_act = (
        requester_positive
        if requested_action is InteractionAction.INJECT
        else not requester_positive
    )
    xnn_reversal = (
        requested_action is InteractionAction.INJECT
        and requester_positive
        and requester_length <= 5
        and reverse_roll is not None
        and reverse_roll < 0.5
    )

    if not requester_can_act:
        reversal = InteractionReversal.WRONG_ACTION
    elif xnn_reversal:
        reversal = InteractionReversal.XNN
    else:
        reversal = InteractionReversal.NONE

    if reversal is InteractionReversal.NONE:
        action = requested_action
        actor = InteractionParticipant.REQUESTER
    else:
        action = (
            InteractionAction.INJECT if target_length > 0 else InteractionAction.SQUEEZE
        )
        actor = InteractionParticipant.TARGET

    if action is InteractionAction.INJECT:
        recipient = (
            InteractionParticipant.TARGET
            if actor is InteractionParticipant.REQUESTER
            else InteractionParticipant.REQUESTER
        )
        fluid = InteractionFluid.DNA
    else:
        recipient = actor
        source_length = (
            target_length
            if actor is InteractionParticipant.REQUESTER
            else requester_length
        )
        fluid = (
            InteractionFluid.DNA if source_length > 0 else InteractionFluid.GIRL_JUICE
        )

    return InteractionResolution(
        action=action,
        actor=actor,
        recipient=recipient,
        fluid=fluid,
        reversal=reversal,
    )
