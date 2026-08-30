"""rules.py 规则函数单元测试。

覆盖：
- should_trigger_ciduo: xnn 边界 + 注入量阈值
- calc_ciduo_new_length: 含零值保护
- calc_pk_effective_win_probability: xnn debuff
- calc_pk_loss_amount: xnn 加重
- clamp_xnn_floor: 下限保护
"""

import pytest

from nonebot_plugin_impart_plus.core.rules import (
    CIDUO_LENGTH_DELTA,
    CIDUO_THRESHOLD_ML,
    XNN_LENGTH_FLOOR,
    XNN_LOSS_FACTOR,
    XNN_WIN_RATE_FACTOR,
    calc_ciduo_new_length,
    calc_normalized_win_probability,
    calc_pk_bonus,
    calc_pk_effective_win_probability,
    calc_pk_loss_amount,
    calc_win_rate_delta,
    clamp_xnn_floor,
    should_trigger_ciduo,
)
from nonebot_plugin_impart_plus.core.world import LengthState

# ═══════════════════════════════════════════════════════
#  常量验证
# ═══════════════════════════════════════════════════════


class TestConstants:
    """确保常量与 game-design 一致。"""

    def test_ciduo_threshold(self):
        assert CIDUO_THRESHOLD_ML == 500.0

    def test_ciduo_delta(self):
        assert CIDUO_LENGTH_DELTA == -5.0

    def test_xnn_win_rate_factor(self):
        assert XNN_WIN_RATE_FACTOR == 0.5

    def test_xnn_loss_factor(self):
        assert XNN_LOSS_FACTOR == 1.5

    def test_xnn_floor(self):
        assert XNN_LENGTH_FLOOR == 0.01


# ═══════════════════════════════════════════════════════
#  should_trigger_ciduo
# ═══════════════════════════════════════════════════════


class TestShouldTriggerCiduo:
    """雌堕触发 = xnn 且当日注入 >= 500。"""

    # xnn + 达到阈值 → True
    def test_xnn_at_threshold(self):
        assert (
            should_trigger_ciduo(
                target_state=LengthState(3.0), today_injection_ml=500.0
            )
            is True
        )

    # xnn + 超过阈值 → True
    def test_xnn_above_threshold(self):
        assert (
            should_trigger_ciduo(
                target_state=LengthState(0.01), today_injection_ml=999.0
            )
            is True
        )

    # xnn + 未达阈值 → False
    def test_xnn_below_threshold(self):
        assert (
            should_trigger_ciduo(
                target_state=LengthState(3.0), today_injection_ml=499.99
            )
            is False
        )

    # 非 xnn（正值大于 5）+ 达到阈值 → False
    def test_not_xnn_large_positive(self):
        assert (
            should_trigger_ciduo(
                target_state=LengthState(10.0), today_injection_ml=600.0
            )
            is False
        )

    # 非 xnn（负值）+ 达到阈值 → False
    def test_negative_world(self):
        assert (
            should_trigger_ciduo(
                target_state=LengthState(-5.0), today_injection_ml=600.0
            )
            is False
        )

    # 非 xnn（零值）+ 达到阈值 → False
    def test_zero_not_xnn(self):
        assert (
            should_trigger_ciduo(
                target_state=LengthState(0.0), today_injection_ml=600.0
            )
            is False
        )

    # xnn 上界（5.0）+ 达到阈值 → True
    def test_xnn_upper_boundary(self):
        assert (
            should_trigger_ciduo(
                target_state=LengthState(5.0), today_injection_ml=500.0
            )
            is True
        )

    # xnn 刚超出（5.001）+ 达到阈值 → False
    def test_just_above_xnn(self):
        assert (
            should_trigger_ciduo(
                target_state=LengthState(5.001), today_injection_ml=500.0
            )
            is False
        )

    # 注入量恰好 0 → False
    def test_zero_injection(self):
        assert (
            should_trigger_ciduo(target_state=LengthState(3.0), today_injection_ml=0.0)
            is False
        )


# ═══════════════════════════════════════════════════════
#  calc_ciduo_new_length
# ═══════════════════════════════════════════════════════


class TestCalcCiduoNewLength:
    """current - 5，含零值保护。"""

    def test_normal_case(self):
        # 3.0 - 5 = -2.0
        assert calc_ciduo_new_length(current_length=3.0) == -2.0

    def test_exact_five(self):
        # 5.0 - 5 = 0.0 → 零值保护 → -0.01
        assert calc_ciduo_new_length(current_length=5.0) == -0.01

    def test_above_five(self):
        # 10.0 - 5 = 5.0
        assert calc_ciduo_new_length(current_length=10.0) == 5.0

    def test_at_one(self):
        # 1.0 - 5 = -4.0
        assert calc_ciduo_new_length(current_length=1.0) == -4.0

    def test_small_positive(self):
        # 0.01 - 5 = -4.99
        assert calc_ciduo_new_length(current_length=0.01) == -4.99

    def test_rounding(self):
        # 5.001 - 5 = 0.001 → 不为零
        result = calc_ciduo_new_length(current_length=5.001)
        assert result == 0.001

    def test_zero_value_protection(self):
        """5.0 - 5 恰好为零时，保护为 -0.01。"""
        assert calc_ciduo_new_length(current_length=5.0) == -0.01


# ═══════════════════════════════════════════════════════
#  calc_pk_effective_win_probability
# ═══════════════════════════════════════════════════════


class TestCalcPkEffectiveWinProbability:
    """xnn 时胜率减半。"""

    def test_non_xnn_unchanged(self):
        assert (
            calc_pk_effective_win_probability(
                base_probability=0.5, attacker_state=LengthState(10.0)
            )
            == 0.5
        )

    def test_xnn_halved(self):
        assert calc_pk_effective_win_probability(
            base_probability=0.6, attacker_state=LengthState(3.0)
        ) == pytest.approx(0.3)

    def test_xnn_boundary_five(self):
        """5.0 在 xnn 区间内。"""
        assert calc_pk_effective_win_probability(
            base_probability=0.8, attacker_state=LengthState(5.0)
        ) == pytest.approx(0.4)

    def test_xnn_boundary_just_above(self):
        """5.001 不在 xnn 区间。"""
        assert (
            calc_pk_effective_win_probability(
                base_probability=0.8, attacker_state=LengthState(5.001)
            )
            == 0.8
        )

    def test_negative_world(self):
        """负值世界不受 xnn debuff。"""
        assert (
            calc_pk_effective_win_probability(
                base_probability=0.5, attacker_state=LengthState(-10.0)
            )
            == 0.5
        )

    def test_zero_base(self):
        """基础胜率 0 乘 0.5 仍是 0。"""
        assert (
            calc_pk_effective_win_probability(
                base_probability=0.0, attacker_state=LengthState(3.0)
            )
            == 0.0
        )


# ═══════════════════════════════════════════════════════
#  calc_pk_loss_amount
# ═══════════════════════════════════════════════════════


class TestCalcPkLossAmount:
    """败方 xnn 时损失 ×1.5。"""

    def test_non_xnn(self):
        assert calc_pk_loss_amount(base_loss=1.0, loser_state=LengthState(10.0)) == 1.0

    def test_xnn_amplified(self):
        assert calc_pk_loss_amount(base_loss=1.0, loser_state=LengthState(3.0)) == 1.5

    def test_xnn_rounding(self):
        result = calc_pk_loss_amount(base_loss=0.777, loser_state=LengthState(2.0))
        assert result == round(0.777 * 1.5, 3)

    def test_zero_loss(self):
        assert calc_pk_loss_amount(base_loss=0.0, loser_state=LengthState(3.0)) == 0.0


# ═══════════════════════════════════════════════════════
#  clamp_xnn_floor
# ═══════════════════════════════════════════════════════


class TestClampXnnFloor:
    """xnn 下限保护 = 0.01。"""

    def test_xnn_below_floor(self):
        assert clamp_xnn_floor(new_length=0.005, state=LengthState(3.0)) == 0.01

    def test_xnn_at_floor(self):
        assert clamp_xnn_floor(new_length=0.01, state=LengthState(3.0)) == 0.01

    def test_xnn_above_floor(self):
        assert clamp_xnn_floor(new_length=0.5, state=LengthState(3.0)) == 0.5

    def test_xnn_negative_clamped(self):
        """变更后为负值，但 xnn 保护钳到 0.01。"""
        assert clamp_xnn_floor(new_length=-1.0, state=LengthState(3.0)) == 0.01

    def test_non_xnn_no_clamp(self):
        """非 xnn 不做钳制，可以为任意值。"""
        assert clamp_xnn_floor(new_length=-1.0, state=LengthState(10.0)) == -1.0

    def test_non_xnn_zero(self):
        assert clamp_xnn_floor(new_length=0.0, state=LengthState(10.0)) == 0.0

    def test_xnn_zero_clamped(self):
        """xnn 且值为 0 → 钳到 0.01。"""
        assert clamp_xnn_floor(new_length=0.0, state=LengthState(1.0)) == 0.01


# ═══════════════════════════════════════════════════════
#  TASK002: calc_normalized_win_probability
# ═══════════════════════════════════════════════════════


class TestCalcNormalizedWinProbability:
    """归一化胜率 P(A) = Wa / (Wa + Wb)。"""

    def test_equal_rates(self):
        """相同胜率 → 50%。"""
        assert calc_normalized_win_probability(wa_eff=0.5, wb_eff=0.5) == pytest.approx(
            0.5
        )

    def test_a_stronger(self):
        """A 胜率更高 → P(A) > 0.5。"""
        p = calc_normalized_win_probability(wa_eff=0.7, wb_eff=0.3)
        assert p == pytest.approx(0.7)

    def test_b_stronger(self):
        """B 胜率更高 → P(A) < 0.5。"""
        p = calc_normalized_win_probability(wa_eff=0.3, wb_eff=0.7)
        assert p == pytest.approx(0.3)

    def test_both_zero_fallback(self):
        """双方均 0 → 回退 0.5。"""
        assert calc_normalized_win_probability(wa_eff=0.0, wb_eff=0.0) == 0.5

    def test_one_zero(self):
        """一方为 0 → 另一方 100%。"""
        assert calc_normalized_win_probability(wa_eff=0.0, wb_eff=0.5) == 0.0
        assert calc_normalized_win_probability(wa_eff=0.5, wb_eff=0.0) == 1.0

    def test_xnn_debuff_scenario(self):
        """模拟 xnn debuff: A 原始 0.6×0.5=0.3, B 原始 0.5。"""
        p = calc_normalized_win_probability(wa_eff=0.3, wb_eff=0.5)
        assert p == pytest.approx(0.375)

    def test_extreme_asymmetry(self):
        """极端不对称。"""
        p = calc_normalized_win_probability(wa_eff=0.99, wb_eff=0.01)
        assert p == pytest.approx(0.99)

    def test_negative_total_fallback(self):
        """负值总和 → 回退 0.5。"""
        assert calc_normalized_win_probability(wa_eff=-0.1, wb_eff=0.0) == 0.5


# ═══════════════════════════════════════════════════════
#  TASK002: calc_pk_bonus
# ═══════════════════════════════════════════════════════


class TestCalcPkBonus:
    """爆冷倍率 = max(1, W_loser / W_winner)。"""

    def test_strong_wins_no_bonus(self):
        """强方获胜 → bonus = 1。"""
        assert calc_pk_bonus(winner_w_eff=0.7, loser_w_eff=0.3) == 1.0

    def test_weak_wins_bonus(self):
        """弱方获胜 → bonus > 1。"""
        b = calc_pk_bonus(winner_w_eff=0.3, loser_w_eff=0.7)
        assert b == pytest.approx(0.7 / 0.3)

    def test_equal_rates(self):
        """相同胜率 → bonus = 1。"""
        assert calc_pk_bonus(winner_w_eff=0.5, loser_w_eff=0.5) == 1.0

    def test_winner_zero_fallback(self):
        """赢家 W = 0 → bonus = 1。"""
        assert calc_pk_bonus(winner_w_eff=0.0, loser_w_eff=0.5) == 1.0

    def test_loser_zero(self):
        """输家 W = 0 → bonus = max(1, 0) = 1。"""
        assert calc_pk_bonus(winner_w_eff=0.5, loser_w_eff=0.0) == 1.0

    def test_both_zero(self):
        """双方均 0 → 1.0。"""
        assert calc_pk_bonus(winner_w_eff=0.0, loser_w_eff=0.0) == 1.0

    def test_extreme_upset(self):
        """极端爆冷：0.1 赢 0.9 → bonus = 9。"""
        b = calc_pk_bonus(winner_w_eff=0.1, loser_w_eff=0.9)
        assert b == pytest.approx(9.0)

    def test_winner_negative_fallback(self):
        """赢家 W < 0 → 1.0。"""
        assert calc_pk_bonus(winner_w_eff=-0.1, loser_w_eff=0.5) == 1.0


# ═══════════════════════════════════════════════════════
#  TASK002: calc_win_rate_delta
# ═══════════════════════════════════════════════════════


class TestCalcWinRateDelta:
    """单边抛物线阻尼胜率变化。"""

    def test_win_at_center(self):
        """赢在 W=0.5 → 满速阻尼: delta = -k * 4*0.5*0.5 = -k。"""
        d = calc_win_rate_delta(w=0.5, won=True, k=0.02)
        # toward_boundary: raw<0 且 w=0.5 → NOT (w<0.5) → toward center
        # 实际: w=0.5 不算 <0.5，所以 (raw<0 and w<0.5) = False
        # (raw>0 and w>0.5) = False → toward_boundary = False → 全速
        assert d == pytest.approx(-0.02, abs=1e-6)

    def test_lose_at_center(self):
        """输在 W=0.5 → 全速: delta = +k。"""
        d = calc_win_rate_delta(w=0.5, won=False, k=0.02)
        assert d == pytest.approx(0.02, abs=1e-6)

    def test_win_at_low_toward_boundary(self):
        """赢在 W=0.2 → 往 0 走 (boundary) → 阻尼。"""
        d = calc_win_rate_delta(w=0.2, won=True, k=0.02)
        damping = 4.0 * 0.2 * 0.8  # = 0.64
        assert d == pytest.approx(-0.02 * damping, abs=1e-6)

    def test_lose_at_high_toward_boundary(self):
        """输在 W=0.8 → 往 1 走 (boundary) → 阻尼。"""
        d = calc_win_rate_delta(w=0.8, won=False, k=0.02)
        damping = 4.0 * 0.8 * 0.2  # = 0.64
        assert d == pytest.approx(0.02 * damping, abs=1e-6)

    def test_win_at_high_toward_center(self):
        """赢在 W=0.8 → 往 0.5 走 (center) → 全速。"""
        d = calc_win_rate_delta(w=0.8, won=True, k=0.02)
        assert d == pytest.approx(-0.02, abs=1e-6)

    def test_lose_at_low_toward_center(self):
        """输在 W=0.2 → 往 0.5 走 (center) → 全速。"""
        d = calc_win_rate_delta(w=0.2, won=False, k=0.02)
        assert d == pytest.approx(0.02, abs=1e-6)

    def test_extreme_low(self):
        """W=0.01 赢 → 往 0 走，极大阻尼。"""
        d = calc_win_rate_delta(w=0.01, won=True, k=0.02)
        damping = 4.0 * 0.01 * 0.99  # ≈ 0.0396
        assert d == pytest.approx(-0.02 * damping, abs=1e-6)

    def test_extreme_high(self):
        """W=0.99 输 → 往 1 走，极大阻尼。"""
        d = calc_win_rate_delta(w=0.99, won=False, k=0.02)
        damping = 4.0 * 0.99 * 0.01  # ≈ 0.0396
        assert d == pytest.approx(0.02 * damping, abs=1e-6)

    def test_at_zero(self):
        """W=0 赢 → 阻尼 = 0。"""
        d = calc_win_rate_delta(w=0.0, won=True, k=0.02)
        # toward_boundary: raw<0 and w<0.5 → True → damping = 4*0*1 = 0
        assert d == pytest.approx(0.0, abs=1e-6)

    def test_at_one(self):
        """W=1 输 → 阻尼 = 0。"""
        d = calc_win_rate_delta(w=1.0, won=False, k=0.02)
        # toward_boundary: raw>0 and w>0.5 → True → damping = 4*1*0 = 0
        assert d == pytest.approx(0.0, abs=1e-6)

    def test_custom_k(self):
        """自定义 k 值。"""
        d = calc_win_rate_delta(w=0.5, won=True, k=0.05)
        assert d == pytest.approx(-0.05, abs=1e-6)

    def test_symmetry_at_center(self):
        """中心点赢和输绝对值相同。"""
        d_win = calc_win_rate_delta(w=0.5, won=True, k=0.02)
        d_lose = calc_win_rate_delta(w=0.5, won=False, k=0.02)
        assert abs(d_win) == pytest.approx(abs(d_lose), abs=1e-6)

    def test_rounding_precision(self):
        """结果应当有 6 位小数精度。"""
        d = calc_win_rate_delta(w=0.123, won=True, k=0.02)
        # 往 0 走 → 阻尼 = 4 * 0.123 * (1 - 0.123)
        damping = 4.0 * 0.123 * (1.0 - 0.123)
        assert d == pytest.approx(round(-0.02 * damping, 6), abs=1e-6)
