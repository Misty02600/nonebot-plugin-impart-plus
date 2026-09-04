"""插件生命周期。"""

from nonebot import get_driver, logger
from nonebot_plugin_orm import get_session

from ..infra.legacy_import import import_legacy_data
from . import handlers as handlers


@get_driver().on_startup
async def import_upstream_data() -> None:
    if await import_legacy_data(get_session):
        logger.info("已从 nonebot_plugin_impart 导入旧数据")
