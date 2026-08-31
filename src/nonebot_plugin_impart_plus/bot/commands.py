"""Alconna 命令定义。"""

from arclet.alconna import Alconna, AllParam, Args, CommandMeta

HELP_COMMAND = Alconna("re:(?i:(银趴|impart)(介绍|帮助))")

TOGGLE_COMMAND = Alconna(
    "re:(?i:(开始|开启|关闭|禁止)(银趴|impart))",
    Args["tail?", AllParam],
    meta=CommandMeta(compact=True),
)
