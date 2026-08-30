"""插件配置。"""

from pydantic import BaseModel


class Config(BaseModel):
    usage: str = """impart功能说明:
[日群友|透群友|日群主|透群主|日管理|透管理]
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
[jj排行榜|jj排名|jj榜单|jjrank]
输出倒数五位/前五位/自己的排名
[注入查询|摄入查询|射入查询]
查询@用户被透注入的量(后接<历史/全部>可查看总被摄入的量)(若未@则为自己)
[开启银趴|禁止银趴|开始impart|关闭impart]
由管理员|群主|SUPERUSERS开启或者关闭impart
[银趴介绍|impart介绍]
输出impart插件的命令列表
"""
    not_allow: str = '群内还未开启impart游戏, 请管理员或群主发送"开始银趴", "禁止银趴"以开启/关闭该功能'
    jj_variable: list[str] = ["牛子", "牛牛", "newnew"]
    dj_cd_time: int = 300  # 打胶冷却时间
    pk_cd_time: int = 60  # pk冷却时间
    suo_cd_time: int = 300  # 嗦冷却时间
    fuck_cd_time: int = 3600  # 透群友冷却时间
    ban_id_list: str = "123456"  # 白名单列表
    isalive: bool = False  # 不活跃惩罚
    nickname: set[str] = {""}
