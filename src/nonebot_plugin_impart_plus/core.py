"""框架无关的游戏规则。"""

from dataclasses import dataclass
from enum import StrEnum


class LengthState(StrEnum):
    GOD = "god"
    NORMAL = "normal"
    XNN = "xnn"
    NEAR_GIRL = "near_girl"
    GIRL = "girl"


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
