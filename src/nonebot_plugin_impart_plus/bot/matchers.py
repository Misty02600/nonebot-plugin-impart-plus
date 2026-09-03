"""Alconna matcher 注册与分派策略。"""

from typing import Literal

from arclet.alconna import Alconna, Args, CommandMeta, Option, Subcommand
from nonebot.permission import SUPERUSER
from nonebot_plugin_alconna import At, on_alconna
from nonebot_plugin_uninfo import ADMIN, GROUP, GUILD

from ..impart.core import GrowthMode

PK_COMMAND = Alconna("pk", Args["target", At])

SELF_GROW_COMMAND = Alconna(
    {
        "打胶": GrowthMode.LENGTH,
        "开导": GrowthMode.LENGTH,
        "开扣": GrowthMode.DEPTH,
        "挖矿": GrowthMode.DEPTH,
    }
)

SUO_COMMAND = Alconna("嗦牛子", Args["target?", At])

INJECTION_QUERY_COMMAND = Alconna(
    "注入查询",
    Args["target?", At],
    Option("历史", alias=["全部"], dest="history", compact=True),
)

RANK_COMMAND = Alconna("re:(?i:(银趴|impart)(排行榜|排名|榜单|rank))")

INTERACTION_COMMAND = Alconna(
    "透",
    Args["kind", Literal["群友", "管理", "群主"]],
    Args["target?", At],
    meta=CommandMeta(compact=True),
)

IMPART_COMMAND = Alconna(
    "银趴",
    Args[
        "enabled?",
        {
            "开启": True,
            "开始": True,
            "禁止": False,
            "关闭": False,
        },
    ],
    Subcommand(
        "查询",
        Args["target?", At],
        dest="query",
    ),
    Subcommand("帮助", alias=["介绍"], dest="help"),
    meta=CommandMeta(compact=True),
)

pk_matcher = on_alconna(
    PK_COMMAND,
    aliases={"对决"},
    rule=GROUP | GUILD,
    auto_send_output=False,
    use_cmd_start=True,
    priority=20,
    block=False,
)

self_growth_matcher = on_alconna(
    SELF_GROW_COMMAND,
    rule=GROUP | GUILD,
    auto_send_output=False,
    use_cmd_start=False,
    priority=20,
    block=True,
)

suo_matcher = on_alconna(
    SUO_COMMAND,
    aliases={"嗦", "suo"},
    rule=GROUP | GUILD,
    auto_send_output=False,
    use_cmd_start=True,
    priority=20,
    block=True,
)

rank_matcher = on_alconna(
    RANK_COMMAND,
    rule=GROUP | GUILD,
    auto_send_output=False,
    use_cmd_start=False,
    priority=20,
    block=True,
)

interaction_matcher = on_alconna(
    INTERACTION_COMMAND,
    aliases={"日"},
    rule=GROUP | GUILD,
    auto_send_output=False,
    use_cmd_start=False,
    priority=20,
    block=True,
)

impart_matcher = on_alconna(
    IMPART_COMMAND,
    aliases={"impart"},
    rule=GROUP | GUILD,
    auto_send_output=False,
    use_cmd_start=False,
    priority=1,
    block=False,
)

toggle_matcher = impart_matcher.dispatch(
    "enabled",
    permission=SUPERUSER | ADMIN(),
    priority=9,
    block=True,
)

query_matcher = impart_matcher.dispatch(
    "query",
    priority=19,
    block=True,
)

help_matcher = impart_matcher.dispatch(
    "help",
    priority=19,
    block=True,
)

injection_query_matcher = on_alconna(
    INJECTION_QUERY_COMMAND,
    aliases={"摄入查询", "射入查询"},
    rule=GROUP | GUILD,
    auto_send_output=False,
    use_cmd_start=True,
    priority=20,
    block=True,
)
