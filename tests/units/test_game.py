"""evaluate_challenge 挑战状态机全覆盖测试。

基于 game-design.md §1.3 的 11 条状态转移规则，逐条验证。
正值世界与负值世界对称测试（abs 阈值统一，惩罚方向翻转）。
"""

import pytest

from nonebot_plugin_impart_plus.core.game import (
    ChallengeStatus,
    ChallengeUpdate,
    evaluate_challenge,
    get_random_num,
)

# ═══════════════════════════════════════════════════════
#  辅助
# ═══════════════════════════════════════════════════════


def _call(
    jj_length: float,
    *,
    challenging: bool = False,
    completed: bool = False,
    near_zero: bool = False,
    zero_or_neg: bool = False,
) -> ChallengeUpdate:
    """evaluate_challenge 的短别名。"""
    return evaluate_challenge(
        jj_length=jj_length,
        is_challenging=challenging,
        challenge_completed=completed,
        is_near_zero=near_zero,
        is_zero_or_neg=zero_or_neg,
    )


# ═══════════════════════════════════════════════════════
#  get_random_num 基础行为
# ═══════════════════════════════════════════════════════


class TestGetRandomNum:
    """基础随机数属性测试。"""

    def test_range(self):
        """值总在 [0, 2] 且 3 位小数。"""
        for _ in range(500):
            val = get_random_num()
            assert 0.0 <= val <= 2.0
            # 最多 3 位小数
            assert round(val, 3) == val

    def test_returns_float(self):
        assert isinstance(get_random_num(), float)


# ═══════════════════════════════════════════════════════
#  正值世界状态转移
# ═══════════════════════════════════════════════════════


class TestPositiveWorldChallenge:
    """正值世界挑战状态机，对应 game-design §1.3 表格。"""

    # ── 规则 1: 非挑战、未完成、25 <= |L| < 30 ──────
    @pytest.mark.parametrize("length", [25.0, 27.5, 29.999])
    def test_challenge_started_low_win(self, length: float):
        u = _call(length)
        assert u.status == ChallengeStatus.CHALLENGE_STARTED_LOW_WIN
        assert u.set_challenging is True
        assert u.probability_factor == 0.8

    # ── 规则 2: 非挑战、未完成、|L| >= 30 ───────────
    @pytest.mark.parametrize("length", [30.0, 50.0, 100.0])
    def test_challenge_completed_direct(self, length: float):
        u = _call(length)
        assert u.status == ChallengeStatus.CHALLENGE_COMPLETED
        assert u.set_completed is True

    # ── 规则 3: 挑战中、未完成、|L| < 25 → 失败 ────
    @pytest.mark.parametrize("length", [0.01, 10.0, 24.999])
    def test_challenge_failed_high_win(self, length: float):
        u = _call(length, challenging=True)
        assert u.status == ChallengeStatus.CHALLENGE_FAILED_HIGH_WIN
        assert u.probability_factor == 1.25
        assert u.length_delta == -5  # 正值惩罚方向
        assert u.set_challenging is False

    # ── 规则 4: 挑战中、未完成、|L| >= 30 → 成功 ────
    @pytest.mark.parametrize("length", [30.0, 35.0])
    def test_challenge_success_high_win(self, length: float):
        u = _call(length, challenging=True)
        assert u.status == ChallengeStatus.CHALLENGE_SUCCESS_HIGH_WIN
        assert u.probability_factor == 1.25
        assert u.set_challenging is False
        assert u.set_completed is True

    # ── 规则 5: 挑战中、25 <= |L| < 30 → 保持 ──────
    @pytest.mark.parametrize("length", [25.0, 27.0, 29.999])
    def test_is_challenging(self, length: float):
        u = _call(length, challenging=True)
        assert u.status == ChallengeStatus.IS_CHALLENGING

    # ── 规则 6: 已完成、25 <= |L| < 30 → 保持 ──────
    def test_challenge_completed_hold(self):
        u = _call(28.0, completed=True)
        assert u.status == ChallengeStatus.CHALLENGE_COMPLETED

    # ── 规则 7: 已完成、|L| < 25 → 降级 ────────────
    @pytest.mark.parametrize("length", [24.999, 10.0, 1.0])
    def test_challenge_completed_reduce(self, length: float):
        u = _call(length, completed=True)
        assert u.status == ChallengeStatus.CHALLENGE_COMPLETED_REDUCE
        assert u.length_delta == -5  # 正值惩罚
        assert u.set_completed is False


# ═══════════════════════════════════════════════════════
#  负值世界状态转移（惩罚方向翻转）
# ═══════════════════════════════════════════════════════


class TestNegativeWorldChallenge:
    """负值世界：阈值基于 abs(length)，惩罚方向 +5（向零靠拢）。"""

    @pytest.mark.parametrize("length", [-25.0, -27.5, -29.999])
    def test_challenge_started_low_win(self, length: float):
        u = _call(length)
        assert u.status == ChallengeStatus.CHALLENGE_STARTED_LOW_WIN
        assert u.set_challenging is True
        assert u.probability_factor == 0.8

    @pytest.mark.parametrize("length", [-30.0, -50.0])
    def test_challenge_completed_direct(self, length: float):
        u = _call(length)
        assert u.status == ChallengeStatus.CHALLENGE_COMPLETED
        assert u.set_completed is True

    @pytest.mark.parametrize("length", [-10.0, -24.999])
    def test_challenge_failed_penalty_flipped(self, length: float):
        u = _call(length, challenging=True)
        assert u.status == ChallengeStatus.CHALLENGE_FAILED_HIGH_WIN
        assert u.length_delta == +5  # 负值罚分方向 = +5

    @pytest.mark.parametrize("length", [-30.0, -35.0])
    def test_challenge_success(self, length: float):
        u = _call(length, challenging=True)
        assert u.status == ChallengeStatus.CHALLENGE_SUCCESS_HIGH_WIN

    @pytest.mark.parametrize("length", [-25.0, -29.0])
    def test_is_challenging(self, length: float):
        u = _call(length, challenging=True)
        assert u.status == ChallengeStatus.IS_CHALLENGING

    @pytest.mark.parametrize("length", [-24.999, -10.0])
    def test_challenge_completed_reduce_flipped(self, length: float):
        u = _call(length, completed=True)
        assert u.status == ChallengeStatus.CHALLENGE_COMPLETED_REDUCE
        assert u.length_delta == +5  # 负值罚分方向翻转


# ═══════════════════════════════════════════════════════
#  xnn 区间进入/退出
# ═══════════════════════════════════════════════════════


class TestXnnTransitions:
    """xnn near-zero 标记的进入和退出。"""

    # 进入 xnn：非负值、未标记、0 < L <= 5
    @pytest.mark.parametrize("length", [0.01, 1.0, 5.0])
    def test_enter_xnn(self, length: float):
        u = _call(length, near_zero=False)
        assert u.status == ChallengeStatus.LENGTH_NEAR_ZERO
        assert u.set_near_zero is True

    # 退出 xnn：标记残留 + L <= 0
    def test_exit_xnn_crossed_to_negative(self):
        u = _call(-1.0, near_zero=True)
        assert u.status == ChallengeStatus.XNN_EXIT
        assert u.set_near_zero is False

    # 退出 xnn：标记残留 + L > 5
    def test_exit_xnn_grew_past_five(self):
        u = _call(6.0, near_zero=True)
        assert u.status == ChallengeStatus.XNN_EXIT
        assert u.set_near_zero is False

    # 退出 xnn：标记残留 + L == 0（零归负值）
    def test_exit_xnn_at_zero(self):
        u = _call(0.0, near_zero=True)
        assert u.status == ChallengeStatus.XNN_EXIT
        assert u.set_near_zero is False

    # 已在 xnn 且仍在区间 → 不重复设置
    @pytest.mark.parametrize("length", [0.5, 3.0, 5.0])
    def test_stay_in_xnn(self, length: float):
        u = _call(length, near_zero=True)
        assert u.status == ChallengeStatus.NONE
        assert u.set_near_zero is None  # 不改动

    # 负值世界不触发 xnn 进入
    def test_negative_never_enters_xnn(self):
        u = _call(-3.0, near_zero=False, zero_or_neg=True)
        assert u.status == ChallengeStatus.NONE


# ═══════════════════════════════════════════════════════
#  零/负值标记
# ═══════════════════════════════════════════════════════


class TestZeroOrNeg:
    """LENGTH_ZERO_OR_NEGATIVE 和回正清除。"""

    # 首次 <= 0：设置标记（|L| 需 < 25 避免触发挑战规则优先匹配）
    @pytest.mark.parametrize("length", [0.0, -0.01, -10.0])
    def test_enter_zero_or_neg(self, length: float):
        u = _call(length, zero_or_neg=False)
        assert u.status == ChallengeStatus.LENGTH_ZERO_OR_NEGATIVE
        assert u.set_zero_or_neg is True

    # 回正：清除标记（length 需 > 5 避免 xnn 进入规则优先匹配）
    @pytest.mark.parametrize("length", [6.0, 10.0])
    def test_exit_zero_or_neg(self, length: float):
        u = _call(length, zero_or_neg=True)
        assert u.set_zero_or_neg is False


# ═══════════════════════════════════════════════════════
#  默认 / fallback
# ═══════════════════════════════════════════════════════


class TestFallback:
    """不匹配任何规则时返回 NONE。"""

    def test_normal_positive_no_flags(self):
        u = _call(10.0)
        assert u.status == ChallengeStatus.NONE

    def test_normal_large_positive_completed(self):
        """已完成、|L| >= 30 → 仍返回 CHALLENGE_COMPLETED（规则 6 扩展域）。"""
        u = _call(35.0, completed=True)
        # 35 >= 30 and completed=True → 不匹配 reduce（需 <25），
        # 也不匹配 hold（需 25<=x<30）→ 落入 fallback
        assert u.status == ChallengeStatus.NONE


# ═══════════════════════════════════════════════════════
#  ChallengeUpdate dataclass 默认值
# ═══════════════════════════════════════════════════════


class TestChallengeUpdateDefaults:
    """ChallengeUpdate 字段默认值。"""

    def test_defaults(self):
        u = ChallengeUpdate(ChallengeStatus.NONE)
        assert u.length_delta == 0.0
        assert u.probability_factor == 1.0
        assert u.set_challenging is None
        assert u.set_completed is None
        assert u.set_near_zero is None
        assert u.set_zero_or_neg is None
