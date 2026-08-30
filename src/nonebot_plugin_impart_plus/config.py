"""插件配置。"""

from pydantic import BaseModel


class Config(BaseModel):
    not_allow: str = '群内还未开启impart游戏, 请管理员或群主发送"开始银趴", "禁止银趴"以开启/关闭该功能'
    jj_variable: list[str] = ["牛子", "牛牛", "newnew"]
    dj_cd_time: int = 300  # 打胶冷却时间
    pk_cd_time: int = 60  # pk冷却时间
    suo_cd_time: int = 300  # 嗦冷却时间
    fuck_cd_time: int = 3600  # 透群友冷却时间
    ban_id_list: str = "123456"  # 白名单列表
    isalive: bool = False  # 不活跃惩罚
    nickname: set[str] = {""}
