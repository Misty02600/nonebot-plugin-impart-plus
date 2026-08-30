"""插件运行时依赖。"""

from nonebot import get_driver, get_plugin_config

from ..app import GameApplication
from ..config import Config
from ..infra.cooldown import CooldownManager

plugin_config = get_plugin_config(Config)

cooldown = CooldownManager(
    dj_cd_time=plugin_config.dj_cd_time,
    pk_cd_time=plugin_config.pk_cd_time,
    suo_cd_time=plugin_config.suo_cd_time,
    fuck_cd_time=plugin_config.fuck_cd_time,
    superusers=frozenset(get_driver().config.superusers),
)

game_app = GameApplication(
    cooldown,
    penalties_enabled=plugin_config.isalive,
)
