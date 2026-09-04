"""插件运行时依赖。"""

from nonebot import get_driver, get_plugin_config
from nonebot_plugin_orm import get_session

from ..config import Config
from ..impart.app import GameApplication
from ..infra.cooldown import CooldownManager
from ..infra.data_manager import DataManager

plugin_config = get_plugin_config(Config)
driver = get_driver()
botname = next(iter(driver.config.nickname), "BOT")

cooldown = CooldownManager(
    dj_cd_time=plugin_config.dj_cd_time,
    pk_cd_time=plugin_config.pk_cd_time,
    suo_cd_time=plugin_config.suo_cd_time,
    fuck_cd_time=plugin_config.fuck_cd_time,
)

data_manager = DataManager(get_session)

game_app = GameApplication(
    data_manager,
    cooldown,
    penalties_enabled=plugin_config.isalive,
)
