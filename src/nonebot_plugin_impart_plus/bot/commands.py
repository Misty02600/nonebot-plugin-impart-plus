"""Alconna 命令定义。"""

from arclet.alconna import Alconna, AllParam, Args, CommandMeta
from nonebot_plugin_alconna import At

PK_COMMAND = Alconna(
    "pk",
    Args["target?", At]["tail?", AllParam],
)

GROW_COMMAND = Alconna("打胶")

SUO_COMMAND = Alconna(
    "嗦牛子",
    Args["target?", At]["tail?", AllParam],
)

QUERY_COMMAND = Alconna(
    "查询",
    Args["target?", At]["tail?", AllParam],
)

INJECTION_QUERY_COMMAND = Alconna(
    "注入查询",
    Args["target?", At]["tail?", AllParam],
)

HELP_COMMAND = Alconna("re:(?i:(银趴|impart)(介绍|帮助))")

TOGGLE_COMMAND = Alconna(
    "re:(?i:(开始|开启|关闭|禁止)(银趴|impart))",
    Args["tail?", AllParam],
    meta=CommandMeta(compact=True),
)
