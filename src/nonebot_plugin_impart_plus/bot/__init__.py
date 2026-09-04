"""插件生命周期与定时任务。"""

from nonebot import require

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

from . import handlers as handlers
from .dependencies import game_app

scheduler.add_job(
    game_app.penalties_and_resets,
    "cron",
    hour=0,
    misfire_grace_time=600,
)
