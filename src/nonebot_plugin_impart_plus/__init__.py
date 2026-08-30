"""NoneBot2 银趴插件 Plus

银趴游戏插件，支持 PK、打胶、嗦牛子、透群友等玩法。
"""

from nonebot.plugin import PluginMetadata

from .config import PluginConfig

__plugin_meta__ = PluginMetadata(
    name="nonebot_plugin_impart_plus",
    usage="使用<银趴帮助/impart help>指令获取使用说明",
    description="NoneBot2 银趴插件 Plus",
    type="application",
    homepage="https://github.com/Misty02600/nonebot_plugin_impart_plus",
    config=PluginConfig,
    supported_adapters={"~onebot.v11"},
    extra={
        "priority": 20,
    },
)

# 导入命令模块以注册所有命令处理器
from .bot.handlers import (  # noqa: F401
    control,
    dajiao,
    help,
    injection,
    pk,
    query,
    rank,
    scheduled,
    suo,
    yinpa,
)
