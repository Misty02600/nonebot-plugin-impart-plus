"""插件入口。"""

from nonebot.plugin import PluginMetadata

from .config import Config

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

from . import bot as bot
