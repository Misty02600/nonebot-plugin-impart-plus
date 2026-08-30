"""长度语义模型。

规则：length > 0 属于正值世界，length <= 0 属于负值世界（零归负值）。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LengthState:
    """基于长度值的语义状态。

    Args:
        length (float): 当前长度值。
    """

    length: float

    @property
    def is_xnn(self) -> bool:
        """是否处于 xnn 区间（$0 < length \\le 5$）。"""
        return 0 < self.length <= 5

    @property
    def is_positive_world(self) -> bool:
        """是否处于正值世界（length > 0）。"""
        return self.length > 0

    @property
    def is_negative_world(self) -> bool:
        """是否处于负值世界（length <= 0，零归负值）。"""
        return self.length <= 0
