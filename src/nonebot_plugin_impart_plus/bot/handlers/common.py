"""公共前置检查

提供可复用的前置检查 handler。
"""

from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.matcher import Matcher

from .. import DataManagerDep
from ..dependencies import plugin_config


async def group_enabled_check(
    event: GroupMessageEvent, matcher: Matcher, dm: DataManagerDep
):
    """群启用检查：群未开启时终止"""
    if not await dm.check_group_allow(event.group_id):
        await matcher.finish(plugin_config.not_allow, at_sender=True)
