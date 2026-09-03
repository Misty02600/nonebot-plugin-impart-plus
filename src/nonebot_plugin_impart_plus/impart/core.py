"""框架无关的游戏规则。"""

from dataclasses import dataclass, replace
from enum import StrEnum


class LengthState(StrEnum):
    GOD = "god"
    NORMAL = "normal"
    XNN = "xnn"
    NEAR_GIRL = "near_girl"
    GIRL = "girl"


class GrowthMode(StrEnum):
    LENGTH = "length"
    DEPTH = "depth"


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


def classify_length(length: float) -> LengthState:
    if length >= 30:
        return LengthState.GOD
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
    if (
        not state.is_challenging
        and not state.challenge_completed
        and 25 <= state.length < 30
    ):
        return StateEvaluation(
            "challenge_started_low_win",
            replace(
                state,
                is_challenging=True,
                win_probability=state.win_probability * 0.8,
            ),
        )
    if (
        not state.is_challenging
        and not state.challenge_completed
        and state.length >= 30
    ):
        return StateEvaluation(
            "challenge_completed",
            replace(state, challenge_completed=True),
        )
    if state.is_challenging and not state.challenge_completed and state.length < 25:
        return StateEvaluation(
            "challenge_failed_high_win",
            replace(
                state,
                length=state.length - 5,
                win_probability=state.win_probability * 1.25,
                is_challenging=False,
            ),
        )
    if state.is_challenging and not state.challenge_completed and state.length >= 30:
        return StateEvaluation(
            "challenge_success_high_win",
            replace(
                state,
                win_probability=state.win_probability * 1.25,
                is_challenging=False,
                challenge_completed=True,
            ),
        )
    if state.is_challenging and 25 <= state.length < 30:
        return StateEvaluation("is_challenging", state)
    if state.challenge_completed and 25 <= state.length < 30:
        return StateEvaluation("challenge_completed", state)
    if state.challenge_completed and state.length < 25:
        return StateEvaluation(
            "challenge_completed_reduce",
            replace(
                state,
                length=state.length - 5,
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
    return current_length < 25 <= new_length


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


def should_reverse_injection(length: float, roll: float) -> bool:
    return length <= 0 or (5 >= length > 0 and roll < 0.5)
