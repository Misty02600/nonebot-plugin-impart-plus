"""插件配置。"""

from pydantic import BaseModel


class Config(BaseModel):
    dj_cd_time: int = 300  # 打胶冷却时间
    pk_cd_time: int = 60  # pk冷却时间
    suo_cd_time: int = 300  # 嗦冷却时间
    fuck_cd_time: int = 3600  # 透群友冷却时间
    isalive: bool = False  # 不活跃惩罚
