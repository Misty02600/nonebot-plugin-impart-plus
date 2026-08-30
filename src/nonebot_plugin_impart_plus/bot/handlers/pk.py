"""PK 对决命令。

采用 pipeline handler 模式：
- pk_cd_check: 共享 CD 检查
- positive_world_guard / negative_world_guard: 入口词阵营校验
- execute_general_pk / execute_positive_pk / execute_negative_pk: 执行逻辑

共享数据通过 PkCtx DI 依赖缓存（@自己 / 存在性 / 同阵营校验均在 DI 解析时完成）。
"""

import random
from dataclasses import dataclass
from typing import Annotated

from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.matcher import Matcher
from nonebot.params import Depends

from ...core.game import ChallengeStatus, get_random_num
from ...core.rules import (
    calc_normalized_win_probability,
    calc_pk_bonus,
    calc_pk_effective_win_probability,
    calc_pk_loss_amount,
    calc_win_rate_delta,
    clamp_xnn_floor,
)
from ...core.world import LengthState
from .. import CooldownDep, DataManagerDep
from ..dependencies import AtTarget, RandomNickname, pick_hole_alias, pick_jj_alias
from ..texts.duel_texts import NegPkCopy, PkCopy, pk_cd
from ..texts.interaction_texts import (
    pk_negative_only,
    pk_positive_only,
    pk_same_camp_fail,
    pk_self_target,
    xnn_enter,
    xnn_opp_enter,
    xnn_opp_exit,
    xnn_self_exit,
)
from .common import group_enabled_check

# region PK 上下文依赖


@dataclass
class _PkCtx:
    """PK 双方上下文。

    通过 DI 解析并缓存：@自己校验、双方存在性校验、同阵营校验
    均在解析阶段完成，失败时 `matcher.finish()` 短路 pipeline。
    """

    uid: int
    uid_str: str
    target_id: int
    target_str: str
    uid_length: float
    target_length: float
    uid_state: LengthState
    target_state: LengthState


async def _get_pk_ctx(
    event: GroupMessageEvent,
    matcher: Matcher,
    dm: DataManagerDep,
    at: AtTarget,
) -> _PkCtx:
    """解析 PK 双方上下文。"""
    uid = event.get_user_id()

    # @自己
    if at == uid:
        await matcher.finish(pk_self_target(), at_sender=True)

    # 存在性
    uid_exists = await dm.is_in_table(int(uid))
    at_exists = await dm.is_in_table(int(at))
    if not (uid_exists and at_exists):
        if not uid_exists:
            await dm.add_new_user(int(uid))
        if not at_exists:
            await dm.add_new_user(int(at))
        await matcher.finish(
            PkCopy(jj_name=pick_jj_alias(), jj_name2=pick_jj_alias()).create(),
            at_sender=True,
        )

    # 读取双方状态
    uid_length = await dm.get_jj_length(int(uid))
    at_length = await dm.get_jj_length(int(at))
    uid_state = LengthState(length=uid_length)
    at_state = LengthState(length=at_length)

    # 同阵营校验
    if uid_state.is_negative_world != at_state.is_negative_world:
        await matcher.finish(pk_same_camp_fail(), at_sender=True)

    return _PkCtx(
        uid=int(uid),
        uid_str=uid,
        target_id=int(at),
        target_str=at,
        uid_length=uid_length,
        target_length=at_length,
        uid_state=uid_state,
        target_state=at_state,
    )


PkCtx = Annotated[_PkCtx, Depends(_get_pk_ctx)]

# endregion

# region 前置 guard handler


async def _has_at(event: GroupMessageEvent) -> bool:
    """rule 检查：是否有 @。"""
    msg = event.get_message()
    return next(
        (msg_seg.data["qq"] != "all" for msg_seg in msg if msg_seg.type == "at"),
        False,
    )


async def pk_cd_check(
    matcher: Matcher,
    event: GroupMessageEvent,
    cd: CooldownDep,
) -> None:
    """CD 检查（所有 PK matcher 共享）。"""
    uid = event.get_user_id()
    allowed, remaining = cd.check_pk(uid)
    if not allowed:
        await matcher.finish(pk_cd(remaining=remaining), at_sender=True)


async def positive_world_guard(
    matcher: Matcher,
    ctx: PkCtx,
) -> None:
    """世界校验：击剑仅限正值玩家。"""
    if ctx.uid_state.is_negative_world:
        await matcher.finish(
            pk_positive_only(),
            at_sender=True,
        )


async def negative_world_guard(
    matcher: Matcher,
    ctx: PkCtx,
) -> None:
    """世界校验：磨豆腐/磨仅限负值玩家。"""
    if not ctx.uid_state.is_negative_world:
        await matcher.finish(
            pk_negative_only(),
            at_sender=True,
        )


# endregion

# region 执行 handler


async def execute_general_pk(
    matcher: Matcher,
    dm: DataManagerDep,
    cd: CooldownDep,
    ctx: PkCtx,
    botname: RandomNickname,
) -> None:
    """通用 PK（pk/对决）——按阵营分派到正值或负值逻辑。"""
    cd.record_pk(ctx.uid_str)
    if ctx.uid_state.is_negative_world:
        await _do_negative_pk(matcher, dm, ctx, botname)
    else:
        await _do_positive_pk(matcher, dm, ctx, botname)


async def execute_positive_pk(
    matcher: Matcher,
    dm: DataManagerDep,
    cd: CooldownDep,
    ctx: PkCtx,
    botname: RandomNickname,
) -> None:
    """正值 PK（击剑）。"""
    cd.record_pk(ctx.uid_str)
    await _do_positive_pk(matcher, dm, ctx, botname)


async def execute_negative_pk(
    matcher: Matcher,
    dm: DataManagerDep,
    cd: CooldownDep,
    ctx: PkCtx,
    botname: RandomNickname,
) -> None:
    """负值 PK（磨豆腐/磨）。"""
    cd.record_pk(ctx.uid_str)
    await _do_negative_pk(matcher, dm, ctx, botname)


# endregion

# region 正值 PK 实现


async def _do_positive_pk(
    matcher: Matcher,
    dm: DataManagerDep,
    ctx: _PkCtx,
    botname: str,
) -> None:
    """正值 PK（含归一化胜率 / 爆冷倍率 / xnn debuff / clamp / 退出通知）。"""
    from ..dependencies import plugin_config

    # 读取双方原始胜率
    uid_base_prob = await dm.get_win_probability(ctx.uid)
    target_base_prob = await dm.get_win_probability(ctx.target_id)

    # xnn debuff（归一化前应用）
    uid_eff_w = calc_pk_effective_win_probability(
        base_probability=uid_base_prob,
        attacker_state=ctx.uid_state,
    )
    target_eff_w = calc_pk_effective_win_probability(
        base_probability=target_base_prob,
        attacker_state=ctx.target_state,
    )

    # 归一化胜率
    prob = calc_normalized_win_probability(wa_eff=uid_eff_w, wb_eff=target_eff_w)
    win = random.random() < prob

    num = get_random_num()
    r = plugin_config.pk_rake_ratio
    k = plugin_config.pk_win_rate_k

    # 爆冷倍率（基于 effective W）
    winner_w_eff = uid_eff_w if win else target_eff_w
    loser_w_eff = target_eff_w if win else uid_eff_w
    bonus = calc_pk_bonus(winner_w_eff=winner_w_eff, loser_w_eff=loser_w_eff)

    length_increase = round(num * r * bonus, 3)

    # xnn 败方损失 ×1.5
    loser_state = ctx.target_state if win else ctx.uid_state
    length_decrease = calc_pk_loss_amount(base_loss=num, loser_state=loser_state)

    winner_id = ctx.uid if win else ctx.target_id
    loser_id = ctx.target_id if win else ctx.uid

    # 单边抛物线阻尼胜率变化
    winner_base = uid_base_prob if win else target_base_prob
    loser_base = target_base_prob if win else uid_base_prob
    winner_prob_delta = calc_win_rate_delta(w=winner_base, won=True, k=k)
    loser_prob_delta = calc_win_rate_delta(w=loser_base, won=False, k=k)

    winner_status, loser_status = await dm.execute_pk(
        winner_id=winner_id,
        loser_id=loser_id,
        length_gain=length_increase,
        length_loss=length_decrease,
        winner_prob_delta=winner_prob_delta,
        loser_prob_delta=loser_prob_delta,
    )

    # xnn clamp：败者下限 0.01
    loser_new_length = await dm.get_jj_length(loser_id)
    clamped_length = clamp_xnn_floor(new_length=loser_new_length, state=loser_state)
    if clamped_length != loser_new_length:
        await dm.set_jj_length_absolute(loser_id, clamped_length)

    uid_prob = await dm.get_win_probability(ctx.uid)
    jj_name = pick_jj_alias()
    pk = PkCopy(
        jj_name=jj_name,
        jj_name2=jj_name,
        botname=botname,
        inc=length_increase,
        dec=length_decrease,
        prob=uid_prob,
        bonus=bonus,
    )

    msg = pk.win() if win else pk.lose()
    uid_status = winner_status if win else loser_status
    at_status = loser_status if win else winner_status

    msg += _build_self_challenge_msg(uid_status, win, pk)
    msg += _build_opponent_challenge_msg(at_status, win, pk)
    msg += _build_xnn_notification(uid_status, at_status, win)

    await matcher.finish(f"{msg}{pk.probability()}", at_sender=True)


# endregion

# region 负值 PK 实现


async def _do_negative_pk(
    matcher: Matcher,
    dm: DataManagerDep,
    ctx: _PkCtx,
    botname: str,
) -> None:
    """负值 PK（归一化胜率 / 爆冷倍率 / 阻尼）：深度比较，胜者加深，败者变浅。"""
    from ..dependencies import plugin_config

    # 读取双方原始胜率（负值世界无 xnn debuff，effective = base）
    uid_base_prob = await dm.get_win_probability(ctx.uid)
    target_base_prob = await dm.get_win_probability(ctx.target_id)

    # 归一化胜率
    prob = calc_normalized_win_probability(
        wa_eff=uid_base_prob, wb_eff=target_base_prob
    )
    win = random.random() < prob

    num = get_random_num()
    r = plugin_config.pk_rake_ratio
    k = plugin_config.pk_win_rate_k

    # 爆冷倍率
    winner_w = uid_base_prob if win else target_base_prob
    loser_w = target_base_prob if win else uid_base_prob
    bonus = calc_pk_bonus(winner_w_eff=winner_w, loser_w_eff=loser_w)

    depth_increase = round(num * r * bonus, 3)
    depth_decrease = num

    winner_id = ctx.uid if win else ctx.target_id
    loser_id = ctx.target_id if win else ctx.uid

    # 胜率变化（阻尼）
    winner_prob_delta = calc_win_rate_delta(
        w=uid_base_prob if win else target_base_prob, won=True, k=k
    )
    loser_prob_delta = calc_win_rate_delta(
        w=target_base_prob if win else uid_base_prob, won=False, k=k
    )

    # 负值世界：胜者加深 (length 更负)，败者变浅 (length 更正)
    winner_status, loser_status = await dm.execute_pk(
        winner_id=winner_id,
        loser_id=loser_id,
        length_gain=-(depth_increase),  # 加深 → length 减小
        length_loss=-num,  # 变浅 → -(-num) = +num → length 增大
        winner_prob_delta=winner_prob_delta,
        loser_prob_delta=loser_prob_delta,
    )

    # 负值 PK 败者不得翻正：钳制到 -0.01
    loser_new_length = await dm.get_jj_length(loser_id)
    if loser_new_length > 0:
        await dm.set_jj_length_absolute(loser_id, -0.01)

    uid_prob = await dm.get_win_probability(ctx.uid)
    hole_name = pick_hole_alias()
    npk = NegPkCopy(
        hole_name=hole_name,
        hole_name2=hole_name,
        botname=botname,
        inc=depth_increase,
        dec=depth_decrease,
        prob=uid_prob,
        bonus=bonus,
    )

    msg = npk.win() if win else npk.lose()
    uid_status = winner_status if win else loser_status
    at_status = loser_status if win else winner_status

    msg += _build_neg_self_challenge_msg(uid_status, win, npk)
    msg += _build_neg_opponent_challenge_msg(at_status, win, npk)

    await matcher.finish(f"{msg}{npk.probability()}", at_sender=True)


# endregion

# region 挑战状态消息构建


def _build_self_challenge_msg(
    status: str,
    is_win: bool,
    pk: PkCopy,
) -> str:
    """构建自己的挑战状态消息（正值）。"""
    if is_win:
        if status == ChallengeStatus.CHALLENGE_STARTED_LOW_WIN:
            return pk.self_challenge_start()
        if status == ChallengeStatus.CHALLENGE_SUCCESS_HIGH_WIN:
            return pk.self_challenge_success()
    else:
        if status == ChallengeStatus.CHALLENGE_FAILED_HIGH_WIN:
            return pk.self_challenge_failed()
        if status == ChallengeStatus.CHALLENGE_COMPLETED_REDUCE:
            return pk.self_fall()
    return ""


def _build_opponent_challenge_msg(
    status: str,
    is_win: bool,
    pk: PkCopy,
) -> str:
    """构建对方的挑战状态消息（正值）。"""
    if is_win:
        if status == ChallengeStatus.CHALLENGE_FAILED_HIGH_WIN:
            return pk.opp_challenge_failed()
        if status == ChallengeStatus.CHALLENGE_COMPLETED_REDUCE:
            return pk.opp_fall()
    else:
        if status == ChallengeStatus.CHALLENGE_STARTED_LOW_WIN:
            return pk.opp_challenge_start()
        if status == ChallengeStatus.CHALLENGE_SUCCESS_HIGH_WIN:
            return pk.opp_challenge_success()
    return ""


def _build_xnn_notification(
    uid_status: str,
    at_status: str,
    is_win: bool,
) -> str:
    """构建 xnn 进入/退出通知。"""
    msg = ""
    if not is_win and uid_status == ChallengeStatus.LENGTH_NEAR_ZERO:
        msg += xnn_enter()
    if uid_status == ChallengeStatus.XNN_EXIT:
        msg += xnn_self_exit()
    if is_win and at_status == ChallengeStatus.LENGTH_NEAR_ZERO:
        msg += xnn_opp_enter()
    if at_status == ChallengeStatus.XNN_EXIT:
        msg += xnn_opp_exit()
    return msg


def _build_neg_self_challenge_msg(
    status: str,
    is_win: bool,
    npk: NegPkCopy,
) -> str:
    """构建自己的挑战状态消息（负值）。"""
    if is_win:
        if status == ChallengeStatus.CHALLENGE_STARTED_LOW_WIN:
            return npk.self_challenge_start()
        if status == ChallengeStatus.CHALLENGE_SUCCESS_HIGH_WIN:
            return npk.self_challenge_success()
    else:
        if status == ChallengeStatus.CHALLENGE_FAILED_HIGH_WIN:
            return npk.self_challenge_failed()
        if status == ChallengeStatus.CHALLENGE_COMPLETED_REDUCE:
            return npk.self_fall()
    return ""


def _build_neg_opponent_challenge_msg(
    status: str,
    is_win: bool,
    npk: NegPkCopy,
) -> str:
    """构建对方的挑战状态消息（负值）。"""
    if is_win:
        if status == ChallengeStatus.CHALLENGE_FAILED_HIGH_WIN:
            return npk.opp_challenge_failed()
        if status == ChallengeStatus.CHALLENGE_COMPLETED_REDUCE:
            return npk.opp_fall()
    else:
        if status == ChallengeStatus.CHALLENGE_STARTED_LOW_WIN:
            return npk.opp_challenge_start()
        if status == ChallengeStatus.CHALLENGE_SUCCESS_HIGH_WIN:
            return npk.opp_challenge_success()
    return ""


# endregion

# region 命令注册

pk_shared_matcher = on_command(
    "pk",
    aliases={"对决"},
    rule=_has_at,
    priority=20,
    block=False,
    handlers=[
        group_enabled_check,  # 1. 群聊启用检查
        pk_cd_check,  # 2. CD 检查
        execute_general_pk,  # 3. 解析 PkCtx（@/存在/同阵营）→ 分派正负值
    ],
)

jijian_matcher = on_command(
    "击剑",
    rule=_has_at,
    priority=20,
    block=False,
    handlers=[
        group_enabled_check,  # 1. 群聊启用检查
        pk_cd_check,  # 2. CD 检查
        positive_world_guard,  # 3. 解析 PkCtx + 正值阵营校验
        execute_positive_pk,  # 4. 正值 PK 逻辑
    ],
)

modofu_matcher = on_command(
    "磨豆腐",
    aliases={"磨"},
    rule=_has_at,
    priority=20,
    block=False,
    handlers=[
        group_enabled_check,  # 1. 群聊启用检查
        pk_cd_check,  # 2. CD 检查
        negative_world_guard,  # 3. 解析 PkCtx + 负值阵营校验
        execute_negative_pk,  # 4. 负值 PK 逻辑
    ],
)

# endregion
