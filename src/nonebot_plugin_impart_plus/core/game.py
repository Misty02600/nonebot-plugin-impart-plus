"""游戏业务逻辑

纯领域逻辑，不依赖 NoneBot / 数据库。
"""

import random
from dataclasses import dataclass, field
from enum import Enum


class ChallengeStatus(str, Enum):
    """挑战状态枚举"""

    NONE = ""
    CHALLENGE_STARTED_LOW_WIN = "challenge_started_low_win"
    CHALLENGE_COMPLETED = "challenge_completed"
    CHALLENGE_FAILED_HIGH_WIN = "challenge_failed_high_win"
    CHALLENGE_SUCCESS_HIGH_WIN = "challenge_success_high_win"
    IS_CHALLENGING = "is_challenging"
    CHALLENGE_COMPLETED_REDUCE = "challenge_completed_reduce"
    LENGTH_NEAR_ZERO = "length_near_zero"
    LENGTH_ZERO_OR_NEGATIVE = "length_zero_or_negative"
    XNN_EXIT = "xnn_exit"


def get_random_num() -> float:
    """获取随机数

    0.1 的概率获取 1-2 的随机数，0.9 的概率获取 0-1 的随机数。

    Returns:
        float: 保留三位小数的随机数
    """
    rand_num = random.random()
    value = random.uniform(1, 2) if rand_num <= 0.1 else random.uniform(0, 1)
    return round(value, 3)


@dataclass
class ChallengeUpdate:
    """挑战评估的更新结果

    Attributes:
        status: 状态变化类型（ChallengeStatus 的值）
        length_delta: 长度变化量
        probability_factor: 胜率乘法因子（1.0 表示不变）
        set_challenging: 是否重置挑战中标记
        set_completed: 是否标记挑战完成
        set_near_zero: 是否重置接近零标记
        set_zero_or_neg: 是否重置零/负标记
    """

    status: str
    length_delta: float = 0.0
    probability_factor: float = 1.0
    set_challenging: bool | None = field(default=None)
    set_completed: bool | None = field(default=None)
    set_near_zero: bool | None = field(default=None)
    set_zero_or_neg: bool | None = field(default=None)


def evaluate_challenge(
    jj_length: float,
    is_challenging: bool,
    challenge_completed: bool,
    is_near_zero: bool,
    is_zero_or_neg: bool,
) -> ChallengeUpdate:
    """根据用户状态评估挑战变化

    纯函数，不涉及数据库操作。返回需要应用的更新。
    正值世界与负值世界均按量级（绝对值）比较阈值，
    负值世界的长度惩罚方向翻转（朝零方向）。

    Args:
        jj_length: 当前长度
        is_challenging: 是否在挑战中
        challenge_completed: 是否已完成挑战
        is_near_zero: 是否接近零
        is_zero_or_neg: 是否为零或负数

    Returns:
        ChallengeUpdate: 需要应用到数据库的更新操作
    """
    is_negative = jj_length <= 0
    magnitude = abs(jj_length)
    # 负值世界惩罚方向翻转：正值 -5（长度减少），负值 +5（深度减少，向零靠拢）
    penalty = 5 if is_negative else -5

    if not is_challenging and not challenge_completed and 25 <= magnitude < 30:
        update = ChallengeUpdate(ChallengeStatus.CHALLENGE_STARTED_LOW_WIN)
        update.set_challenging = True
        update.probability_factor = 0.8
        return update

    if not is_challenging and not challenge_completed and magnitude >= 30:
        update = ChallengeUpdate(ChallengeStatus.CHALLENGE_COMPLETED)
        update.set_completed = True
        return update

    if is_challenging and not challenge_completed and magnitude < 25:
        update = ChallengeUpdate(ChallengeStatus.CHALLENGE_FAILED_HIGH_WIN)
        update.probability_factor = 1.25
        update.length_delta = penalty
        update.set_challenging = False
        return update

    if is_challenging and not challenge_completed and magnitude >= 30:
        update = ChallengeUpdate(ChallengeStatus.CHALLENGE_SUCCESS_HIGH_WIN)
        update.probability_factor = 1.25
        update.set_challenging = False
        update.set_completed = True
        return update

    if is_challenging and 25 <= magnitude < 30:
        return ChallengeUpdate(ChallengeStatus.IS_CHALLENGING)

    if challenge_completed and 25 <= magnitude < 30:
        return ChallengeUpdate(ChallengeStatus.CHALLENGE_COMPLETED)

    if challenge_completed and magnitude < 25:
        update = ChallengeUpdate(ChallengeStatus.CHALLENGE_COMPLETED_REDUCE)
        update.length_delta = penalty
        update.set_completed = False
        return update

    # xnn 退出：标记残留时始终清理（玩家可能已越过零点进入负值世界）
    if is_near_zero and (jj_length <= 0 or jj_length > 5):
        update = ChallengeUpdate(ChallengeStatus.XNN_EXIT)
        update.set_near_zero = False
        return update

    # xnn 进入仅适用于正值世界
    if not is_negative and not is_near_zero and 0 < jj_length <= 5:
        update = ChallengeUpdate(ChallengeStatus.LENGTH_NEAR_ZERO)
        update.set_near_zero = True
        return update

    if not is_zero_or_neg and jj_length <= 0:
        update = ChallengeUpdate(ChallengeStatus.LENGTH_ZERO_OR_NEGATIVE)
        update.set_zero_or_neg = True
        return update

    if is_zero_or_neg and jj_length > 0:
        update = ChallengeUpdate(ChallengeStatus.NONE)
        update.set_zero_or_neg = False
        return update

    return ChallengeUpdate(ChallengeStatus.NONE)
