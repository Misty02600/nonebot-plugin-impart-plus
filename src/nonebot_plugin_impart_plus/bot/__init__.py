"""插件生命周期与定时任务。"""

from nonebot import get_driver, logger, require
from nonebot_plugin_orm import get_session

from ..infra.legacy_import import import_legacy_data
from . import handlers as handlers
from .dependencies import game_app


@get_driver().on_startup
async def import_upstream_data() -> None:
    if await import_legacy_data(get_session):
        logger.info("已从 nonebot_plugin_impart 导入旧数据")


require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

scheduler.add_job(
    game_app.penalties_and_resets,
    "cron",
    hour=0,
    misfire_grace_time=600,
)
