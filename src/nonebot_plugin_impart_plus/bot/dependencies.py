"""插件运行时依赖。"""

from nonebot import get_driver, get_plugin_config

from ..config import Config
from ..impart.app import GameApplication
from ..infra.cooldown import CooldownManager

plugin_config = get_plugin_config(Config)
driver = get_driver()
botname = next(iter(driver.config.nickname), "BOT")

cooldown = CooldownManager(
    dj_cd_time=plugin_config.dj_cd_time,
    pk_cd_time=plugin_config.pk_cd_time,
    suo_cd_time=plugin_config.suo_cd_time,
    fuck_cd_time=plugin_config.fuck_cd_time,
    superusers=frozenset(driver.config.superusers),
)

game_app = GameApplication(
    cooldown,
    penalties_enabled=plugin_config.isalive,
)
