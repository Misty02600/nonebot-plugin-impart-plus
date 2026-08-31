"""按功能加载 Handler 并触发装饰器注册。"""

from . import control as control
from . import game as game
from . import interaction as interaction
from . import records as records

__all__ = ["control", "game", "interaction", "records"]
