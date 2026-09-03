"""插件入口。"""

from nonebot import require
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

from .config import Config

require("nonebot_plugin_alconna")
require("nonebot_plugin_uninfo")
require("nonebot_plugin_uniref")

__plugin_meta__ = PluginMetadata(
    name="nonebot_plugin_impart_plus",
    usage="""impart功能说明:
所有指令均遵循NoneBot的COMMAND_START配置
[透|日][群友|管理|群主]
群友可随机或@指定目标
[pk|对决] @用户
胜方长度增加/深度加深随机数/2,
败方长度减小/深度变浅随机数;
初始胜率为50%,pk后胜方胜率-1%,败方胜率+1%
必须@其他用户, 多个@只取第一个
<牛牛长度超过25时会触发神秘任务>
[打胶|开导]
增加自己长度
[开扣|挖矿]
增加自己深度
[嗦] @用户
增加其他正值用户长度
[舔] @用户
增加其他非正值用户深度
[银趴|impart][查询]
查询@用户长度或深度(若未@则为自己)
[银趴|impart][排行榜|排名|榜单|rank]
输出倒数五位/前五位/自己的排名
[注入查询|摄入查询|射入查询]
查询@用户被透注入的量(后接<历史/全部>可查看总被摄入的量)(若未@则为自己)
[银趴|impart][开启|禁止|帮助]
由管理员|群主|SUPERUSERS开启或者关闭impart
子命令前的空格可以省略，例如<银趴开启>, <银趴 查询>
""",
    description="NoneBot2 银趴插件 Plus",
    type="application",
    homepage="https://github.com/Misty02600/nonebot_plugin_impart_plus",
    config=Config,
    supported_adapters=inherit_supported_adapters(
        "nonebot_plugin_alconna",
        "nonebot_plugin_uninfo",
        "nonebot_plugin_uniref",
    ),
    extra={
        "priority": 20,
    },
)

from . import bot as bot
