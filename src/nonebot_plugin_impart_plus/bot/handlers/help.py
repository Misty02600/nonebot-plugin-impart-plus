"""帮助命令"""

from re import I

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.matcher import Matcher

from ..dependencies import plugin_config

# region 事件处理函数


async def help_handler(matcher: Matcher) -> None:
    """输出功能说明"""
    await matcher.send(MessageSegment.text(plugin_config.usage))


# endregion

# region 命令注册

help_matcher = on_regex(
    r"^(银趴|impart)(介绍|帮助)$",
    flags=I,
    priority=20,
    block=True,
    handlers=[help_handler],
)

# endregion
