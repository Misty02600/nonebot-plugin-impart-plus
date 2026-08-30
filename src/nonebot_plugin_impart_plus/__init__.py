"""插件入口"""

from re import I

from nonebot import get_driver, on_command, on_regex, require
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata

from .config import Config
from .data_sheet import init_db
from .handle import impart

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

__plugin_meta__ = PluginMetadata(
    name="nonebot_plugin_impart_plus",
    usage="使用<银趴帮助/impart help>指令获取使用说明",
    description="NoneBot2 银趴插件 Plus",
    type="application",
    homepage="https://github.com/Misty02600/nonebot_plugin_impart_plus",
    config=Config,
    supported_adapters={"~onebot.v11"},
    extra={
        "priority": 20,
    },
)

on_command(
    "pk",
    aliases={"对决"},
    rule=Config.rule,
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

on_regex(
    r"^(开始|开启|关闭|禁止)(银趴|impart)",
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER,
    flags=I,
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

on_regex(
    r"^(银趴|impart)(介绍|帮助)$",
    flags=I,
    priority=20,
    block=True,
    handlers=[impart.yinpa_introduce],
)
