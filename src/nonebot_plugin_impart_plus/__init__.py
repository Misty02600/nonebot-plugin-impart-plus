"""插件入口。"""

from nonebot import require
from nonebot.plugin import PluginMetadata

from .config import Config

require("nonebot_plugin_alconna")
require("nonebot_plugin_uninfo")

__plugin_meta__ = PluginMetadata(
    name="nonebot_plugin_impart_plus",
    usage="""impart功能说明:
[透|日][群友|群主|管理]
字面意思,使用<透群友>时可@用户
[pk|对决]
通过random实现pk,胜方获取败方随机数/2的牛牛长度;
初始战力为50%,pk后胜方战力-1%,败方战力+1%
<牛牛长度超过25时会触发神秘任务>
[打胶|开导]
增加自己长度
[嗦牛子|嗦]
增加@用户长度(若未@则为自己)
[查询]
查询@用户长度(若未@则为自己)
[银趴|impart][排行榜|排名|榜单|rank]
输出倒数五位/前五位/自己的排名
[注入查询|摄入查询|射入查询]
查询@用户被透注入的量(后接<历史/全部>可查看总被摄入的量)(若未@则为自己)
[银趴|impart][开启|禁止|帮助]
由管理员|群主|SUPERUSERS开启或者关闭impart
子命令前的空格可以省略，例如<银趴开启>, <银趴 帮助>
""",
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
