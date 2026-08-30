"""LengthState 语义模型单元测试。

覆盖：
- 正值世界 / 负值世界 / 零归负值
- xnn 区间边界（0, 0.01, 5, 5.01）
- 大正值 / 大负值
"""

import pytest

from nonebot_plugin_impart_plus.core.world import LengthState

# ── 正值世界 / 负值世界 ──────────────────────────────


class TestWorldClassification:
    """正值世界 vs 负值世界边界。"""

    @pytest.mark.parametrize(
        ("length", "positive", "negative"),
        [
            (100.0, True, False),
            (0.01, True, False),
            (5.0, True, False),
            (0.001, True, False),
            (0.0, False, True),  # 零归负值
            (-0.01, False, True),
            (-100.0, False, True),
        ],
        ids=[
            "large_positive",
            "tiny_positive",
            "five",
            "near_zero_positive",
            "zero_is_negative",
            "tiny_negative",
            "large_negative",
        ],
    )
    def test_world_classification(self, length: float, positive: bool, negative: bool):
        state = LengthState(length)
        assert state.is_positive_world is positive
        assert state.is_negative_world is negative


# ── xnn 区间 ───────────────────────────────────────


class TestXnnZone:
    """xnn 判定：0 < length <= 5。"""

    @pytest.mark.parametrize(
        ("length", "expected"),
        [
            (0.0, False),  # 零不是 xnn（零归负值）
            (0.001, True),  # 刚进入正值
            (0.01, True),  # floor 值
            (1.0, True),
            (5.0, True),  # 上界包含
            (5.001, False),  # 刚超出
            (30.0, False),
            (-1.0, False),  # 负值不可能是 xnn
            (-5.0, False),
        ],
        ids=[
            "zero",
            "epsilon_positive",
            "floor",
            "mid",
            "upper_inclusive",
            "just_above",
            "god_zone",
            "negative",
            "deep_negative",
        ],
    )
    def test_is_xnn(self, length: float, expected: bool):
        assert LengthState(length).is_xnn is expected


# ── 不变性 ──────────────────────────────────────────


class TestFrozen:
    """LengthState 是 frozen dataclass。"""

    def test_immutable(self):
        state = LengthState(10.0)
        with pytest.raises(AttributeError):
            state.length = 20.0  # type: ignore[misc]
