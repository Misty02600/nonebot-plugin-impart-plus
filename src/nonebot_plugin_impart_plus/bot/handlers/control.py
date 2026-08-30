"""开关控制命令"""

from re import I

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.matcher import Matcher
from nonebot.params import RegexGroup
from nonebot.permission import SUPERUSER

from .. import DataManagerDep

# region 事件处理函数


async def control_handler(
    matcher: Matcher,
    event: GroupMessageEvent,
    dm: DataManagerDep,
    args: tuple = RegexGroup(),
) -> None:
    """开启/关闭银趴"""
    gid = event.group_id
    command = args[0]

    if "开启" in command or "开始" in command:
        await dm.set_group_allow(gid, allow=True)
        await matcher.finish("功能已开启喵")
    elif "禁止" in command or "关闭" in command:
        await dm.set_group_allow(gid, allow=False)
        await matcher.finish("功能已禁用喵")


# endregion

# region 命令注册

control_matcher = on_regex(
    r"^(开始|开启|关闭|禁止)(银趴|impart)",
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER,
    flags=I,
    priority=10,
    block=True,
    handlers=[control_handler],
)

# endregion
