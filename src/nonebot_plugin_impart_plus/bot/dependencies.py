"""依赖注入模块

提供服务实例化和 NoneBot 依赖注入。
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Annotated

from nonebot import get_driver, get_plugin_config, logger, require
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent
from nonebot.matcher import Matcher
from nonebot.params import Depends, RegexGroup

from ..config import PluginConfig
from ..core.world import LengthState
from ..infra.chart_renderer import ChartRenderer
from ..infra.cooldown import CooldownManager
from ..infra.data_manager import DataManager
from ..infra.database import create_engine, create_session_factory, init_db
from .texts.interaction_texts import (
    no_admin_target,
    self_target_owner,
    target_not_found,
)

require("nonebot_plugin_localstore")
from nonebot_plugin_localstore import get_plugin_data_dir

plugin_config = get_plugin_config(PluginConfig)
driver = get_driver()


def pick_jj_alias() -> str:
    """从配置别名列表中随机选取一个正值世界名称。"""
    return random.choice(plugin_config.jj_aliases)


def pick_hole_alias() -> str:
    """从配置别名列表中随机选取一个负值世界名称。"""
    return random.choice(plugin_config.hole_aliases)


# region DataManager

_engine = create_engine(get_plugin_data_dir() / "impart.db")
_session_factory = create_session_factory(_engine)
_data_manager = DataManager(_session_factory)


@driver.on_startup
async def _init_database():
    """启动时初始化数据库"""
    await init_db(_engine)
    logger.info("impart 数据库初始化完成")


def get_data_manager() -> DataManager:
    """获取 DataManager 实例"""
    return _data_manager


DataManagerDep = Annotated[DataManager, Depends(get_data_manager)]

# endregion

# region CooldownManager

_cooldown = CooldownManager(
    dj_cd_time=plugin_config.dj_cd_time,
    pk_cd_time=plugin_config.pk_cd_time,
    suo_cd_time=plugin_config.suo_cd_time,
    fuck_cd_time=plugin_config.fuck_cd_time,
    superusers=frozenset(driver.config.superusers),
)


def get_cooldown() -> CooldownManager:
    """获取 CooldownManager 实例"""
    return _cooldown


CooldownDep = Annotated[CooldownManager, Depends(get_cooldown)]

# endregion

# region ChartRenderer

_chart_renderer = ChartRenderer()


def get_chart_renderer() -> ChartRenderer:
    """获取 ChartRenderer 实例"""
    return _chart_renderer


DrawChartDep = Annotated[ChartRenderer, Depends(get_chart_renderer)]

# endregion

# region 通用工具依赖


def get_random_nickname() -> str:
    """获取一个随机机器人昵称"""
    nicknames = getattr(driver.config, "nickname", set()) or {"BOT"}
    return random.choice(tuple(nicknames))


RandomNickname = Annotated[str, Depends(get_random_nickname)]


async def get_at(event: GroupMessageEvent) -> str:
    """获取 @ 目标的 QQ 号

    Returns:
        str: QQ 号字符串，不存在或 @全体 时返回 "寄"
    """
    msg = event.get_message()
    return next(
        (
            "寄" if msg_seg.data["qq"] == "all" else str(msg_seg.data["qq"])
            for msg_seg in msg
            if msg_seg.type == "at"
        ),
        "寄",
    )


AtTarget = Annotated[str, Depends(get_at)]


def get_ban_id_set() -> set[str]:
    """获取白名单 ID 集合"""
    return (
        set(plugin_config.ban_id_list.split(","))
        if plugin_config.ban_id_list
        else set()
    )


BanIdSet = Annotated[set[str], Depends(get_ban_id_set)]

# endregion

# region 银趴上下文依赖


@dataclass
class _RequesterCtx:
    """银趴发起者上下文。

    通过 DI 解析并缓存，同一次事件处理中所有 handler 共享同一实例。

    Attributes:
        uid: 用户 ID（int）。
        uid_str: 用户 ID（str）。
        card: 群名片或昵称。
        state: 长度状态。
    """

    uid: int
    uid_str: str
    card: str
    state: LengthState

    @property
    def is_negative_world(self) -> bool:
        """是否处于负值世界。"""
        return self.state.is_negative_world

    @property
    def is_xnn(self) -> bool:
        """是否处于 xnn 区间。"""
        return self.state.is_xnn


async def _get_requester_ctx(
    event: GroupMessageEvent,
    dm: DataManagerDep,
) -> _RequesterCtx:
    """解析并缓存发起者上下文。"""
    uid = event.user_id
    await dm.ensure_user(uid)
    length = await dm.get_jj_length(uid)
    return _RequesterCtx(
        uid=uid,
        uid_str=str(uid),
        card=str(event.sender.card or event.sender.nickname),
        state=LengthState(length=length),
    )


RequesterCtx = Annotated[_RequesterCtx, Depends(_get_requester_ctx)]


@dataclass
class _TargetCtx:
    """银趴目标上下文。

    通过 DI 解析并缓存，包含目标选择、目标状态等信息。
    解析过程中若目标选择失败会直接 `matcher.finish()` 终止 pipeline。

    Attributes:
        user_id: 目标用户 ID（str）。
        card: 群名片或昵称。
        sex: 性别（来自群成员信息）。
        state: 长度状态。
    """

    user_id: str
    card: str
    sex: str
    state: LengthState

    @property
    def is_xnn(self) -> bool:
        """是否处于 xnn 区间。"""
        return self.state.is_xnn


async def _get_target_ctx(
    bot: Bot,
    event: GroupMessageEvent,
    matcher: Matcher,
    dm: DataManagerDep,
    requester: RequesterCtx,
    at: AtTarget,
    ban_ids: BanIdSet,
    args: tuple = RegexGroup(),
) -> _TargetCtx:
    """解析并缓存目标上下文。

    根据触发词中的目标类型（群友/群主/管理）和 @ 信息选择目标，
    查询目标状态并返回。选择失败时 `matcher.finish()` 终止。
    """
    target_type = args[1] if args and len(args) > 1 and args[1] else "群友"
    action = args[0] if args and args[0] else "透"
    command = action + target_type

    prep_list = await bot.get_group_member_list(group_id=event.group_id)

    # 目标选择
    if "群主" in command:
        lucky_user = _select_owner(requester.uid, prep_list)
    elif "管理" in command:
        lucky_user = _select_admin(requester.uid, prep_list, ban_ids)
    else:
        lucky_user = _select_member(requester.uid, prep_list, at, ban_ids)

    if lucky_user is None:
        await matcher.finish(target_not_found(action=action), at_sender=True)
    if lucky_user == "self-target-owner":
        await matcher.finish(self_target_owner(action=action), at_sender=True)
    if lucky_user == "no-admin":
        await matcher.finish(no_admin_target(action=action), at_sender=True)

    # 查询目标信息
    card = next(
        (
            prep["card"] or prep["nickname"]
            for prep in prep_list
            if prep["user_id"] == int(lucky_user)
        ),
        "群友",
    )
    sex = next(
        (
            prep.get("sex", "unknown")
            for prep in prep_list
            if prep["user_id"] == int(lucky_user)
        ),
        "unknown",
    )

    await dm.ensure_user(int(lucky_user))
    length = await dm.get_jj_length(int(lucky_user))

    return _TargetCtx(
        user_id=lucky_user,
        card=card,
        sex=sex,
        state=LengthState(length=length),
    )


TargetCtx = Annotated[_TargetCtx, Depends(_get_target_ctx)]


def _select_owner(uid: int, prep_list: list[dict]) -> str:
    """选择群主作为目标。

    Args:
        uid: 发起者 ID。
        prep_list: 群成员列表。

    Returns:
        目标 ID，或 "self-target-owner" 哨兵值。
    """
    lucky_user = next(
        (str(prep["user_id"]) for prep in prep_list if prep["role"] == "owner"),
        str(uid),
    )
    if int(lucky_user) == uid:
        return "self-target-owner"
    return lucky_user


def _select_admin(uid: int, prep_list: list[dict], ban_ids: set[str]) -> str | None:
    """随机选择一位管理作为目标。

    Args:
        uid: 发起者 ID。
        prep_list: 群成员列表。
        ban_ids: 白名单集合。

    Returns:
        目标 ID，无可用管理时返回 "no-admin" 哨兵值。
    """
    admin_ids = [
        prep["user_id"]
        for prep in prep_list
        if prep["role"] == "admin" and str(prep["user_id"]) not in ban_ids
    ]
    if not admin_ids:
        admin_ids = [
            prep["user_id"]
            for prep in prep_list
            if prep["role"] == "admin" and str(prep["user_id"]) in ban_ids
        ]
    if uid in admin_ids:
        admin_ids.remove(uid)
    if not admin_ids:
        return "no-admin"
    return str(random.choice(admin_ids))


def _select_member(
    uid: int,
    prep_list: list[dict],
    at: str,
    ban_ids: set[str],
) -> str | None:
    """随机选择一位群友作为目标。

    Args:
        uid: 发起者 ID。
        prep_list: 群成员列表。
        at: @ 目标 ID，无 @ 时为 "寄"。
        ban_ids: 白名单集合。

    Returns:
        目标 ID，无可用目标时返回 None。
    """
    if at != "寄":
        return at
    member_ids = [prep.get("user_id", 123456) for prep in prep_list]
    filtered = [c for c in member_ids if str(c) not in ban_ids]
    if not filtered:
        filtered = [c for c in member_ids if str(c) in ban_ids]
    filtered = [c for c in filtered if c != uid]
    if not filtered:
        return None
    return str(random.choice(filtered))


# endregion
