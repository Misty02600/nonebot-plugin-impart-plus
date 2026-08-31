"""Alconna 命令定义。"""

from typing import Literal

from arclet.alconna import Alconna, Args, CommandMeta, Option, Subcommand
from nonebot_plugin_alconna import At

PK_COMMAND = Alconna(
    "pk",
    Args["target", At],
)

GROW_COMMAND = Alconna("打胶")

SUO_COMMAND = Alconna(
    "嗦牛子",
    Args["target?", At],
)

QUERY_COMMAND = Alconna(
    "查询",
    Args["target?", At],
)

INJECTION_QUERY_COMMAND = Alconna(
    "注入查询",
    Args["target?", At],
    Option("历史", alias=["全部"], dest="history"),
)

RANK_COMMAND = Alconna("re:(?i:(jj|牛牛)(排行榜|排名|榜单|rank))")

INTERACTION_COMMAND = Alconna(
    "透",
    Args["kind", Literal["群友", "管理", "群主"]]["target?", At],
    meta=CommandMeta(compact=True),
)

IMPART_COMMAND = Alconna(
    "银趴",
    Subcommand("开启", alias=["开始"], dest="enable"),
    Subcommand("禁止", alias=["关闭"], dest="disable"),
    Subcommand("帮助", alias=["介绍"], dest="help"),
    meta=CommandMeta(compact=True),
)
