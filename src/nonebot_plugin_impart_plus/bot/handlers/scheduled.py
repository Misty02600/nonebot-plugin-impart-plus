"""定时任务"""

from nonebot import require

from ..dependencies import get_data_manager, plugin_config

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler


async def _penalties_and_resets() -> None:
    """每日零点执行：惩罚不活跃用户"""
    if plugin_config.isalive:
        dm = get_data_manager()
        await dm.punish_all_inactive_users()


scheduler.add_job(_penalties_and_resets, "cron", hour=0, misfire_grace_time=600)
