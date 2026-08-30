"""插件配置"""

from pydantic import BaseModel, Field


class PluginConfig(BaseModel):
    """impart 插件配置

    所有配置项可通过 .env 文件设置。
    """

    usage: str = Field(
        default="""impart功能说明:
[日群友|透群友|日群主|透群主|日管理|透管理]
字面意思,使用<透群友>时可@用户
[榨群友|榨群主|榨管理]
榨取目标的精华,群友支持@用户
[pk|对决|击剑]
通过random实现pk,胜方获取败方随机数/2的牛牛长度;
初始胜率为50%,pk后胜方胜率-1%,败方胜率+1%
<牛牛长度超过25时会触发神秘任务>
[磨豆腐|磨]
深度较量PK
[打胶|开导]
增加自己长度
[开扣|挖矿]
增加自己的深度
[嗦牛子|嗦]
增加@用户长度(若未@则为自己)
[舔小学|舔]
增加@用户深度(若未@则为自己)
[查询]
查询@用户长度/深度与胜率(若未@则为自己)
[银趴排行榜|impart排行榜|银趴排名|impart排名]
输出倒数五位/前五位/自己的排名
[注入查询|摄入查询|射入查询]
查询@用户被透注入的量(后接<历史/全部>可查看总被摄入的量)(若未@则为自己)
[开启银趴|禁止银趴|开始impart|关闭impart]
由管理员|群主|SUPERUSERS开启或者关闭impart
[银趴介绍|impart介绍]
输出impart插件的命令列表
""",
        description="功能说明文本",
    )
    not_allow: str = Field(
        default='群内还未开启impart游戏, 请管理员或群主发送"开始银趴", "禁止银趴"以开启/关闭该功能',
        description="群未开启时的提示语",
    )
    dj_cd_time: int = Field(default=300, description="打胶冷却时间(秒)")
    pk_cd_time: int = Field(default=60, description="PK冷却时间(秒)")
    suo_cd_time: int = Field(default=300, description="嗦冷却时间(秒)")
    fuck_cd_time: int = Field(default=3600, description="透群友冷却时间(秒)")
    ban_id_list: str = Field(default="123456", description="白名单列表(逗号分隔)")
    isalive: bool = Field(default=False, description="是否启用不活跃惩罚")
    pk_rake_ratio: float = Field(
        default=0.5, description="PK赢家收益系数 r (赢家获得 num×r×bonus)"
    )
    pk_win_rate_k: float = Field(
        default=0.02, description="PK胜率变化基础量 K (中心处有效变化 ±K)"
    )
    jj_aliases: list[str] = Field(
        default=["牛子", "牛牛", "newnew"], description="正值世界别名列表（随机选取）"
    )
    hole_aliases: list[str] = Field(
        default=["小学", "蜜雪"], description="负值世界别名列表（随机选取）"
    )
