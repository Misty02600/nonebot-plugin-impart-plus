"""插件配置。"""

from pydantic import BaseModel


class Config(BaseModel):
    dj_cd_time: int = 600  # 打胶冷却时间
    pk_cd_time: int = 600  # pk冷却时间
    suo_cd_time: int = 600  # 嗦/舔冷却时间
    fuck_cd_time: int = 1200  # 透/榨冷却时间
    impart_font_family: str = "Noto Sans CJK SC"  # 两种图统一使用的默认字体
