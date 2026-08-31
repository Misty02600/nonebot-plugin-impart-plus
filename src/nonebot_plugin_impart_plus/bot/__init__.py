"""Matcher 注册与插件生命周期。"""

from nonebot import get_driver, require
from nonebot.permission import SUPERUSER
from nonebot_plugin_alconna import on_alconna
from nonebot_plugin_uninfo import ADMIN

from ..infra.database import init_db
from .commands import (
    GROW_COMMAND,
    IMPART_COMMAND,
    INJECTION_QUERY_COMMAND,
    INTERACTION_COMMAND,
    PK_COMMAND,
    QUERY_COMMAND,
    RANK_COMMAND,
    SUO_COMMAND,
)
from .context import public_scene
from .handlers import impart

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler


@get_driver().on_startup
async def init_plugin() -> None:
    await init_db()


scheduler.add_job(
    impart.penalties_and_resets,
    "cron",
    hour=0,
    misfire_grace_time=600,
)

on_alconna(
    PK_COMMAND,
    aliases={"对决"},
    rule=public_scene,
    auto_send_output=False,
    use_cmd_start=True,
    priority=20,
    block=False,
    handlers=[impart.pk],
)

on_alconna(
    GROW_COMMAND,
    aliases={"开导"},
    rule=public_scene,
    auto_send_output=False,
    use_cmd_start=False,
    priority=20,
    block=True,
    handlers=[impart.dajiao],
)

on_alconna(
    SUO_COMMAND,
    aliases={"嗦", "suo"},
    rule=public_scene,
    auto_send_output=False,
    use_cmd_start=True,
    priority=20,
    block=True,
    handlers=[impart.suo],
)

on_alconna(
    QUERY_COMMAND,
    rule=public_scene,
    auto_send_output=False,
    use_cmd_start=True,
    priority=20,
    block=False,
    handlers=[impart.queryjj],
)

on_alconna(
    RANK_COMMAND,
    rule=public_scene,
    auto_send_output=False,
    use_cmd_start=False,
    priority=20,
    block=True,
    handlers=[impart.jjrank],
)

on_alconna(
    INTERACTION_COMMAND,
    aliases={"日"},
    rule=public_scene,
    auto_send_output=False,
    use_cmd_start=False,
    priority=20,
    block=True,
    handlers=[impart.yinpa],
)

impart_matcher = on_alconna(
    IMPART_COMMAND,
    aliases={"impart"},
    rule=public_scene,
    auto_send_output=False,
    use_cmd_start=False,
    priority=1,
    block=False,
)

impart_matcher.dispatch(
    "enable",
    permission=SUPERUSER | ADMIN(),
    priority=9,
    block=True,
    handlers=[impart.open_module],
)

impart_matcher.dispatch(
    "disable",
    permission=SUPERUSER | ADMIN(),
    priority=9,
    block=True,
    handlers=[impart.open_module],
)

impart_matcher.dispatch(
    "help",
    priority=19,
    block=True,
    handlers=[impart.yinpa_introduce],
)

on_alconna(
    INJECTION_QUERY_COMMAND,
    aliases={"摄入查询", "射入查询"},
    rule=public_scene,
    auto_send_output=False,
    use_cmd_start=True,
    priority=20,
    block=True,
    handlers=[impart.query_injection],
)
