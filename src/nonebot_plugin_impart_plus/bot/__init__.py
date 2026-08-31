"""插件生命周期与定时任务。"""

from nonebot import get_driver, require

from ..infra.database import init_db

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

from . import handlers as handlers
from .dependencies import game_app


@get_driver().on_startup
async def init_plugin() -> None:
    await init_db()


scheduler.add_job(
    game_app.penalties_and_resets,
    "cron",
    hour=0,
    misfire_grace_time=600,
)
