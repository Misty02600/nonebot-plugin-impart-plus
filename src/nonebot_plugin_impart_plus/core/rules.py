"""核心规则常量与规则函数。"""

from __future__ import annotations

from .world import LengthState

# 雌堕：当日累计被注入量阈值（毫升）
CIDUO_THRESHOLD_ML: float = 500.0

# 雌堕后长度变化量：基于当前长度直接 -5
CIDUO_LENGTH_DELTA: float = -5.0

# xnn 对决规则
XNN_WIN_RATE_FACTOR: float = 0.5
XNN_LOSS_FACTOR: float = 1.5
XNN_LENGTH_FLOOR: float = 0.01


def should_trigger_ciduo(
    *, target_state: LengthState, today_injection_ml: float
) -> bool:
    """判断是否触发雌堕。

    Args:
            target_state (LengthState): 目标当前语义状态。
            today_injection_ml (float): 目标当日累计注入量（毫升）。

    Returns:
            bool: 当目标处于 xnn 且累计注入量达到阈值时返回 True。
    """
    return target_state.is_xnn and today_injection_ml >= CIDUO_THRESHOLD_ML


def calc_ciduo_new_length(*, current_length: float) -> float:
    """计算雌堕后的新长度。

    规则：基于当前长度直接减去 5，即 $new = current - 5$。

    Args:
            current_length (float): 触发雌堕前的长度。

    Returns:
            float: 雌堕后的新长度。
    """
    result = round(current_length + CIDUO_LENGTH_DELTA, 3)
    # 长度不允许恰好为零（零归负值，使用 -0.01 替代）
    return -0.01 if result == 0.0 else result


def calc_pk_effective_win_probability(
    *, base_probability: float, attacker_state: LengthState
) -> float:
    """计算 PK 生效胜率。

    Args:
            base_probability (float): 基础胜率。
            attacker_state (LengthState): 发起方语义状态。

    Returns:
            float: 应用于本次判定的胜率。
    """
    if attacker_state.is_xnn:
        return base_probability * XNN_WIN_RATE_FACTOR
    return base_probability


def calc_pk_loss_amount(*, base_loss: float, loser_state: LengthState) -> float:
    """计算败方实际损失值。

    Args:
            base_loss (float): 基础损失。
            loser_state (LengthState): 败方语义状态。

    Returns:
            float: 本次应扣减的实际损失。
    """
    if loser_state.is_xnn:
        return round(base_loss * XNN_LOSS_FACTOR, 3)
    return base_loss


def clamp_xnn_floor(*, new_length: float, state: LengthState) -> float:
    """按 xnn 规则应用长度下限。

    Args:
            new_length (float): 变更后的长度。
            state (LengthState): 参与判定的语义状态（通常为变更前状态）。

    Returns:
            float: 应用下限后的长度。
    """
    if state.is_xnn and new_length < XNN_LENGTH_FLOOR:
        return XNN_LENGTH_FLOOR
    return new_length


# ── TASK002: PK 胜率机制重设计 ──────────────────────


def calc_normalized_win_probability(
    *,
    wa_eff: float,
    wb_eff: float,
) -> float:
    """归一化胜率：$P(A) = W_A / (W_A + W_B)$。

    双方 effective W 均已包含 buff/debuff（如 xnn 减半）。

    Args:
            wa_eff: A 方 effective 胜率。
            wb_eff: B 方 effective 胜率。

    Returns:
            A 方获胜概率 (0, 1)。若双方均为 0 则返回 0.5。
    """
    total = wa_eff + wb_eff
    if total <= 0:
        return 0.5
    return wa_eff / total


def calc_pk_bonus(
    *,
    winner_w_eff: float,
    loser_w_eff: float,
) -> float:
    """计算爆冷倍率：$bonus = max(1, W_{loser} / W_{winner})$。

    只有弱方获胜时 bonus > 1。强方获胜时 bonus = 1。

    Args:
            winner_w_eff: 赢家 effective 胜率（含 debuff）。
            loser_w_eff: 输家 effective 胜率（含 debuff）。

    Returns:
            爆冷倍率 (>=1.0)。若赢家 W <= 0 则返回 1.0。
    """
    if winner_w_eff <= 0:
        return 1.0
    return max(1.0, loser_w_eff / winner_w_eff)


def calc_win_rate_delta(
    *,
    w: float,
    won: bool,
    k: float = 0.02,
) -> float:
    """单边抛物线阻尼胜率变化。

    往边界方向走时应用阻尼 $f(W)=4W(1-W)$，往中心方向走时全速。

    Args:
            w: 当前胜率 (0, 1)。
            won: 本局是否获胜。
            k: 基础变化量（默认 0.02）。

    Returns:
            胜率变化量（正表示升高，负表示降低）。
    """
    raw = -k if won else k  # 赢了降胜率，输了升胜率
    # 判断方向：raw<0 且 w<0.5 = 往 0 走；raw>0 且 w>0.5 = 往 1 走
    toward_boundary = (raw < 0 and w < 0.5) or (raw > 0 and w > 0.5)
    if toward_boundary:
        damping = 4.0 * w * (1.0 - w)
        return round(raw * damping, 6)
    return round(raw, 6)
