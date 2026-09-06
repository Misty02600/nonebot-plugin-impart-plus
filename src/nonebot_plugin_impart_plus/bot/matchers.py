"""Alconna matcher 注册与分派策略。"""

from typing import Literal

from arclet.alconna import Alconna, Args, CommandMeta, MultiVar, Subcommand
from nonebot.permission import SUPERUSER
from nonebot_plugin_alconna import At, on_alconna
from nonebot_plugin_uninfo import ADMIN, GROUP, GUILD

from ..impart.core import GrowthMode, InteractionAction

PK_COMMAND = Alconna("pk", Args["targets?", MultiVar(At)])
POSSESSION_COMMAND = Alconna("夺舍", Args["targets?", MultiVar(At)])

SELF_GROW_MODES = {
    "打胶": GrowthMode.LENGTH,
    "开导": GrowthMode.LENGTH,
    "开扣": GrowthMode.DEPTH,
    "挖矿": GrowthMode.DEPTH,
}
SELF_GROW_COMMAND = Alconna(f"{{action:{'|'.join(SELF_GROW_MODES)}}}")

TARGET_GROW_MODES = {
    "嗦": GrowthMode.LENGTH,
    "舔": GrowthMode.DEPTH,
}
TARGET_GROW_COMMAND = Alconna(
    f"{{action:{'|'.join(TARGET_GROW_MODES)}}}",
    Args["targets?", MultiVar(At)],
)

RANK_COMMAND = Alconna("re:(?i:(银趴|impart|jj)(排行榜|排名|榜单|rank))")

INTERACTION_ACTIONS = {
    "透": InteractionAction.INJECT,
    "日": InteractionAction.INJECT,
    "榨": InteractionAction.SQUEEZE,
}
INTERACTION_COMMAND = Alconna(
    f"{{action:{'|'.join(INTERACTION_ACTIONS)}}}",
    Args["kind", Literal["群友", "管理", "群主"]],
    Args["targets?", MultiVar(At)],
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
        "查询历史",
        Args["target?", At],
        alias=["查询全部"],
        dest="history_query",
    ),
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
    permission=GROUP | GUILD,
    use_cmd_start=True,
    priority=20,
    block=False,
)

possession_matcher = on_alconna(
    POSSESSION_COMMAND,
    permission=GROUP | GUILD,
    use_cmd_start=True,
    priority=20,
    block=True,
)

self_growth_matcher = on_alconna(
    SELF_GROW_COMMAND,
    permission=GROUP | GUILD,
    use_cmd_start=True,
    priority=20,
    block=True,
)

target_growth_matcher = on_alconna(
    TARGET_GROW_COMMAND,
    permission=GROUP | GUILD,
    use_cmd_start=True,
    priority=20,
    block=True,
)

rank_matcher = on_alconna(
    RANK_COMMAND,
    permission=GROUP | GUILD,
    use_cmd_start=True,
    priority=20,
    block=True,
)

interaction_matcher = on_alconna(
    INTERACTION_COMMAND,
    permission=GROUP | GUILD,
    use_cmd_start=True,
    priority=20,
    block=True,
)

impart_matcher = on_alconna(
    IMPART_COMMAND,
    aliases={"impart"},
    permission=GROUP | GUILD,
    use_cmd_start=True,
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

history_query_matcher = impart_matcher.dispatch(
    "history_query",
    priority=19,
    block=True,
)

help_matcher = impart_matcher.dispatch(
    "help",
    priority=19,
    block=True,
)
