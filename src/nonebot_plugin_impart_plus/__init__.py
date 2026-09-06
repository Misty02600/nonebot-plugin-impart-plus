"""插件入口。"""

from nonebot import require
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

from .config import Config

require("nonebot_plugin_orm")
require("nonebot_plugin_alconna")
require("nonebot_plugin_uninfo")
require("nonebot_plugin_uniref")
require("nonebot_plugin_localstore")
require("nonebot_plugin_htmlkit")

__plugin_meta__ = PluginMetadata(
    name="nonebot-plugin-impart-plus",
    usage="""impart功能说明:
[透|日|榨][群友|管理|群主]
群友可随机或@指定目标，可能触发特殊事件
[pk|对决] @用户
胜方长度增加/深度加深随机数/2,
败方长度减小/深度变浅随机数;
初始胜率为50%,pk后胜方胜率-1%,败方胜率+1%
必须@其他用户, 完成一阶试炼后最多可同时指定两个目标
<长度或深度达到25时会触发试炼>
[打胶|开导]
增加自己长度
[开扣|挖矿]
增加自己深度
[嗦] @用户
增加其他正值用户长度
[舔] @用户
增加其他非正值用户深度
[夺舍] @用户
一次性指令❗完成深渊试炼后的禁忌之术
[银趴|impart][查询|查询历史|查询全部]
查询@用户长度或深度及当日注入量(若未@则为自己)，查询历史/全部可查看累计记录
[银趴|impart|jj][排行榜|排名|榜单|rank]
输出前五位/后五位/自己的排名，本人在中段时同时显示左右相邻用户
[银趴|impart][开启|禁止|帮助]
由管理员|群主|SUPERUSERS开启或者关闭impart
子命令前的空格可以省略，例如<银趴开启>, <银趴 查询>
""",
    description="NoneBot2 银趴插件 Plus",
    type="application",
    homepage="https://github.com/Misty02600/nonebot-plugin-impart-plus",
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
