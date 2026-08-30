"""银趴（透群友/群主/管理）命令。

采用 pipeline handler 模式：每个 handler 只做一件事，
通过 `handlers=[]` 组合为有序执行链。

共享数据通过 DI 依赖自动缓存：
- `RequesterCtx`：发起者上下文（uid / 群名片 / 世界状态）
- `TargetCtx`：目标上下文（目标 ID / 群名片 / 性别 / 世界状态）
"""

import asyncio
import random
from re import I

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import RegexGroup

from ...core.rules import calc_ciduo_new_length, should_trigger_ciduo
from ...core.world import LengthState
from .. import CooldownDep, DataManagerDep, RequesterCtx, TargetCtx
from ..dependencies import RandomNickname, pick_hole_alias, pick_jj_alias
from ..texts.interaction_texts import (
    CiduoEvent,
    YinpaMenuCopy,
    YinpaReport,
    ZhaMenuCopy,
    ZhaReport,
    wrong_world_use_zha,
    zha_no_male_target,
)
from .common import group_enabled_check

# region 共享前置检查 handler


async def yinpa_cd_check(
    matcher: Matcher,
    cd: CooldownDep,
    requester: RequesterCtx,
) -> None:
    """透/榨群友 CD 检查。"""
    allowed, remaining = cd.check_fuck(requester.uid_str)
    if not allowed:
        await matcher.finish(
            f"你已经榨不出来任何东西了, 请先休息{remaining}秒",
            at_sender=True,
        )


# endregion

# region 世界校验 guard


async def positive_world_guard(
    matcher: Matcher,
    requester: RequesterCtx,
) -> None:
    """世界校验：日/透仅限正值玩家。"""
    if requester.is_negative_world:
        await matcher.finish(
            wrong_world_use_zha(pick_jj_alias()),
            at_sender=True,
        )


async def negative_world_guard(
    matcher: Matcher,
    requester: RequesterCtx,
) -> None:
    """世界校验：榨仅限负值玩家。"""
    if not requester.is_negative_world:
        await matcher.finish(
            "你还不是女孩子喵，请使用「日/透群友」指令",
            at_sender=True,
        )


async def positive_target_guard(
    matcher: Matcher,
    target: TargetCtx,
) -> None:
    """目标校验：榨的目标必须是正值世界玩家。"""
    if not target.state.is_positive_world:
        await matcher.finish(zha_no_male_target(), at_sender=True)


# endregion

# region 透群友执行 handler


# TODO 没必要把群主到群友的逻辑全塞一起，适当拆分事件处理函数更优雅
async def execute_tou(
    matcher: Matcher,
    dm: DataManagerDep,
    cd: CooldownDep,
    requester: RequesterCtx,
    target: TargetCtx,
    botname: RandomNickname,
    args: tuple = RegexGroup(),
) -> None:
    """透群友主逻辑：记 CD → 发菜单 → 结算 → 雌堕判定。"""
    # 所有校验已通过（DI 解析 TargetCtx 时已完成目标选择），记录 CD
    cd.record_fuck(requester.uid_str)

    target_type = args[1] if args and len(args) > 1 and args[1] else "群友"
    command = (args[0] if args and args[0] else "透") + target_type

    menu = YinpaMenuCopy(
        botname=botname,
        user_card=requester.card,
        target_card=target.card,
    )
    if "群主" in command:
        msg = menu.reverse_owner() if requester.is_xnn else menu.owner()
    elif "管理" in command:
        msg = menu.reverse_admin() if requester.is_xnn else menu.admin()
    elif requester.is_xnn:
        msg = menu.xnn_both() if target.is_xnn else menu.reverse_member()
    else:
        msg = menu.member()
    await matcher.send(msg)

    await asyncio.sleep(2)
    await dm.update_activity(int(target.user_id))
    await dm.update_activity(requester.uid)

    ejaculation = round(random.uniform(1, 100), 3)
    action_seconds = random.randint(1, 20)
    injection_targets: set[int] = set()

    report_kwargs = {
        "req_user_card": requester.card,
        "uid": requester.uid,
        "seconds": action_seconds,
        "target_card": target.card,
        "target_id": target.user_id,
        "ejaculation": ejaculation,
    }

    if requester.is_xnn and target.is_xnn:
        # 双 xnn 互透
        reverse_ejaculation = round(random.uniform(1, 100), 3)
        await dm.insert_ejaculation(int(target.user_id), ejaculation)
        await dm.insert_ejaculation(requester.uid, reverse_ejaculation)
        injection_targets.update({int(target.user_id), requester.uid})
        self_total = await dm.get_today_ejaculation_data(requester.uid)
        target_total = await dm.get_today_ejaculation_data(int(target.user_id))
        report = YinpaReport(**report_kwargs, today_total=0)
        repo = report.xnn_both(
            reverse_ejaculation=reverse_ejaculation,
            self_total=self_total,
            target_total=target_total,
        )
    elif requester.is_xnn and target.sex == "female":
        # xnn 透女生
        await dm.insert_ejaculation(int(target.user_id), ejaculation)
        injection_targets.add(int(target.user_id))
        today_total = await dm.get_today_ejaculation_data(int(target.user_id))
        report = YinpaReport(**report_kwargs, today_total=today_total)
        repo = report.squeeze()
    elif requester.is_xnn:
        # xnn 透男生（被反透）
        await dm.insert_ejaculation(requester.uid, ejaculation)
        injection_targets.add(requester.uid)
        today_total = await dm.get_today_ejaculation_data(requester.uid)
        report = YinpaReport(**report_kwargs, today_total=today_total)
        repo = report.reversed()
    else:
        # 正常透
        await dm.insert_ejaculation(int(target.user_id), ejaculation)
        injection_targets.add(int(target.user_id))
        today_total = await dm.get_today_ejaculation_data(int(target.user_id))
        report = YinpaReport(**report_kwargs, today_total=today_total)
        repo = report.active()

    # 雌堕判定
    extra = ""
    id_to_card = {int(target.user_id): target.card, requester.uid: requester.card}
    for injected_id in injection_targets:
        ciduo_msg = await _check_ciduo(
            dm=dm,
            target_id=injected_id,
            target_card=id_to_card.get(injected_id, "群友"),
            req_user_card=requester.card,
        )
        if ciduo_msg:
            extra += ciduo_msg

    await matcher.send(
        repo
        + extra
        + MessageSegment.image(f"https://q1.qlogo.cn/g?b=qq&nk={target.user_id}&s=640"),
    )


# endregion

# region 榨群友执行 handler

# TODO 同样的，拆分事件处理函数给不同matcher用更优雅


async def execute_zha(
    matcher: Matcher,
    dm: DataManagerDep,
    cd: CooldownDep,
    requester: RequesterCtx,
    target: TargetCtx,
    args: tuple = RegexGroup(),
) -> None:
    """榨群友主逻辑：记 CD → 发菜单 → 结算。"""
    cd.record_fuck(requester.uid_str)

    target_type = args[1] if args and len(args) > 1 and args[1] else "群友"
    command = "榨" + target_type

    zha_menu = ZhaMenuCopy(user_card=requester.card)
    if "群主" in command:
        await matcher.send(zha_menu.owner())
    elif "管理" in command:
        await matcher.send(zha_menu.admin())
    else:
        await matcher.send(zha_menu.member())

    await asyncio.sleep(2)
    await dm.update_activity(int(target.user_id))
    await dm.update_activity(requester.uid)

    ejaculation = round(random.uniform(1, 100), 3)
    action_seconds = random.randint(1, 20)

    await dm.insert_ejaculation(int(target.user_id), ejaculation)
    today_total = await dm.get_today_ejaculation_data(int(target.user_id))

    zha_report = ZhaReport(
        req_user_card=requester.card,
        uid=requester.uid,
        seconds=action_seconds,
        target_card=target.card,
        target_id=target.user_id,
        ejaculation=ejaculation,
        today_total=today_total,
    )

    await matcher.send(
        zha_report.finish()
        + MessageSegment.image(f"https://q1.qlogo.cn/g?b=qq&nk={target.user_id}&s=640"),
    )


# endregion

# region 辅助函数


async def _check_ciduo(
    *,
    dm: DataManagerDep,
    target_id: int,
    target_card: str,
    req_user_card: str,
) -> str:
    """检查注入目标是否触发雌堕。

    条件：目标处于 xnn（0 < length <= 5）且当日累计注入量达到阈值。
    触发后将目标长度改为"当前长度 - 5"。

    Args:
        dm: 数据管理器。
        target_id: 被注入者 ID。
        target_card: 被注入者群名片。
        req_user_card: 发起者群名片。

    Returns:
        雌堕播报文案，未触发时返回空字符串。
    """
    target_length = await dm.get_jj_length(target_id)
    target_state = LengthState(length=target_length)
    today_injection = await dm.get_today_ejaculation_data(target_id)
    if not should_trigger_ciduo(
        target_state=target_state,
        today_injection_ml=today_injection,
    ):
        return ""

    new_length = calc_ciduo_new_length(current_length=target_length)
    delta = round(new_length - target_length, 3)
    await dm.set_jj_length(target_id, delta)

    event = CiduoEvent(
        user_card=target_card,
        uid=target_id,
        req_user_card=req_user_card,
        depth=abs(new_length),
        jj_name=pick_jj_alias(),
        hole_name=pick_hole_alias(),
    )
    return event.announce()


# endregion

# region 命令注册

# 保持兼容：`yinpa_matcher` / `zha_matcher` 仍代表“群友”命令。

# TODO 使用on_command重构，支持别名（如“透管理”）和参数（如“透群友 @用户”）

yinpa_matcher = on_regex(
    r"^(日|透)(群友)(?:\s+.*)?$",
    flags=I,
    priority=20,
    block=True,
    handlers=[
        group_enabled_check,
        yinpa_cd_check,
        positive_world_guard,
        execute_tou,
    ],
)

# TODO 群主后面没必要捕获艾特

yinpa_owner_matcher = on_regex(
    r"^(日|透)(群主)(?:\s+.*)?$",
    flags=I,
    priority=20,
    block=True,
    handlers=[
        group_enabled_check,
        yinpa_cd_check,
        positive_world_guard,
        execute_tou,
    ],
)

yinpa_admin_matcher = on_regex(
    r"^(日|透)(管理)(?:\s+.*)?$",
    flags=I,
    priority=20,
    block=True,
    handlers=[
        group_enabled_check,
        yinpa_cd_check,
        positive_world_guard,
        execute_tou,
    ],
)

zha_matcher = on_regex(
    r"^(榨)(群友)(?:\s+.*)?$",
    flags=I,
    priority=20,
    block=True,
    handlers=[
        group_enabled_check,
        yinpa_cd_check,
        negative_world_guard,
        positive_target_guard,
        execute_zha,
    ],
)

zha_owner_matcher = on_regex(
    r"^(榨)(群主)(?:\s+.*)?$",
    flags=I,
    priority=20,
    block=True,
    handlers=[
        group_enabled_check,
        yinpa_cd_check,
        negative_world_guard,
        positive_target_guard,
        execute_zha,
    ],
)

zha_admin_matcher = on_regex(
    r"^(榨)(管理)(?:\s+.*)?$",
    flags=I,
    priority=20,
    block=True,
    handlers=[
        group_enabled_check,
        yinpa_cd_check,
        negative_world_guard,
        positive_target_guard,
        execute_zha,
    ],
)

# endregion
