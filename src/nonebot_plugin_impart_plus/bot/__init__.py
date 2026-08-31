"""Matcher 注册与插件生命周期。"""

from re import I

from nonebot import get_driver, on_command, on_regex, require
from nonebot.permission import SUPERUSER
from nonebot_plugin_alconna import on_alconna
from nonebot_plugin_uninfo import ADMIN

from ..infra.database import init_db
from .commands import HELP_COMMAND, TOGGLE_COMMAND
from .context import public_scene
from .handlers import has_at, impart

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

on_command(
    "pk",
    aliases={"对决"},
    rule=has_at,
    priority=20,
    block=False,
    handlers=[impart.pk],
)

on_regex("^(打胶|开导)$", priority=20, block=True, handlers=[impart.dajiao])

on_command(
    "嗦牛子", aliases={"嗦", "suo"}, priority=20, block=True, handlers=[impart.suo]
)

on_command("查询", priority=20, block=False, handlers=[impart.queryjj])

on_regex(
    r"^(jj|牛牛)(排行榜|排名|榜单|rank)",
    flags=I,
    priority=20,
    block=True,
    handlers=[impart.jjrank],
)

on_regex(
    r"^(日群友|日群主|日管理|透群友|透群主|透管理)",
    flags=I,
    priority=20,
    block=True,
    handlers=[impart.yinpa],
)

on_alconna(
    TOGGLE_COMMAND,
    rule=public_scene,
    auto_send_output=False,
    use_cmd_start=False,
    permission=SUPERUSER | ADMIN(),
    priority=10,
    block=True,
    handlers=[impart.open_module],
)

on_command(
    "注入查询",
    aliases={"摄入查询", "射入查询"},
    priority=20,
    block=True,
    handlers=[impart.query_injection],
)

on_alconna(
    HELP_COMMAND,
    rule=public_scene,
    auto_send_output=False,
    use_cmd_start=False,
    priority=20,
    block=True,
    handlers=[impart.yinpa_introduce],
)
