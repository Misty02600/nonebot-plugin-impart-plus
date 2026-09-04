import pytest


@pytest.mark.parametrize(
    ("message", "enabled", "subcommand", "matched"),
    [
        ("银趴帮助", None, "help", True),
        ("银趴 帮助", None, "help", True),
        ("impart介绍", None, "help", True),
        ("银趴开启", True, None, True),
        ("银趴 开始", True, None, True),
        ("银趴禁止", False, None, True),
        ("银趴 关闭", False, None, True),
        ("银趴查询", None, "query", True),
        ("银趴 查询", None, "query", True),
        ("impart状态", None, None, False),
        ("银趴长度", None, None, False),
        ("开始银趴", None, None, False),
        ("关闭impart", None, None, False),
        ("查询", None, None, False),
        ("/查询", None, None, False),
        ("银趴帮助尾巴", None, None, False),
        ("银趴开启尾巴", None, None, False),
        ("银趴查询尾巴", None, None, False),
        ("/银趴帮助", None, "help", True),
        ("/银趴查询", None, "query", True),
    ],
)
def test_impart_command_group(
    message: str,
    enabled: bool | None,
    subcommand: str | None,
    matched: bool,
):
    from nonebot_plugin_impart_plus.bot.matchers import IMPART_COMMAND

    result = IMPART_COMMAND.parse(message)
    assert result.matched is matched
    if enabled is not None:
        assert result.all_matched_args["enabled"] is enabled
    if subcommand is not None:
        assert subcommand in result.subcommands


def test_self_growth_command_maps_header_to_mode():
    from nonebot_plugin_impart_plus.bot.matchers import (
        SELF_GROW_COMMAND,
        SELF_GROW_MODES,
    )
    from nonebot_plugin_impart_plus.impart.core import GrowthMode

    expected = {
        "打胶": GrowthMode.LENGTH,
        "开导": GrowthMode.LENGTH,
        "开扣": GrowthMode.DEPTH,
        "挖矿": GrowthMode.DEPTH,
    }
    for message, mode in expected.items():
        result = SELF_GROW_COMMAND.parse(message)
        assert result.matched is True
        assert SELF_GROW_MODES[result.header_match.groups["action"]] is mode
    assert SELF_GROW_COMMAND.parse("/打胶").matched is True
    assert SELF_GROW_COMMAND.parse("打胶尾巴").matched is False


def test_target_growth_command_maps_headers_and_keeps_missing_target_parseable():
    from nonebot_plugin_alconna import At, Text, UniMessage

    from nonebot_plugin_impart_plus.bot.matchers import (
        TARGET_GROW_COMMAND,
        TARGET_GROW_MODES,
    )
    from nonebot_plugin_impart_plus.impart.core import GrowthMode

    expected = {
        "嗦": GrowthMode.LENGTH,
        "舔": GrowthMode.DEPTH,
    }
    for command, mode in expected.items():
        result = TARGET_GROW_COMMAND.parse(
            UniMessage([Text(command), At("user", "67890")])
        )
        assert result.matched is True
        assert TARGET_GROW_MODES[result.header_match.groups["action"]] is mode
        assert result.all_matched_args["targets"] == (At("user", "67890"),)

    assert TARGET_GROW_COMMAND.parse("嗦").matched is True
    assert TARGET_GROW_COMMAND.parse("舔").matched is True
    assert TARGET_GROW_COMMAND.parse("/舔").matched is True
    assert TARGET_GROW_COMMAND.parse("suo").matched is False
    assert TARGET_GROW_COMMAND.parse("tian").matched is False
    assert TARGET_GROW_COMMAND.parse("嗦牛子").matched is False
    assert TARGET_GROW_COMMAND.parse("舔小学").matched is False
    assert TARGET_GROW_COMMAND.parse("嗦尾巴").matched is False
    multiple = TARGET_GROW_COMMAND.parse(
        UniMessage(
            [
                Text("嗦 "),
                At("user", "67890"),
                Text(" "),
                At("user", "12345"),
            ]
        )
    )
    assert multiple.matched is True
    assert multiple.all_matched_args["targets"] == (
        At("user", "67890"),
        At("user", "12345"),
    )


def test_query_subcommand_extracts_typed_target():
    from nonebot_plugin_alconna import At, Text, UniMessage

    from nonebot_plugin_impart_plus.bot.matchers import (
        IMPART_COMMAND,
        query_matcher,
    )

    result = IMPART_COMMAND.parse(
        UniMessage([Text("银趴查询 "), At("user", "67890")]),
    )

    assert result.matched is True
    assert result.all_matched_args["target"].target == "67890"
    assert "query" in result.subcommands
    assert query_matcher.block is True


@pytest.mark.parametrize(
    ("command_name", "message", "matched"),
    [
        ("pk", "pk", True),
        ("pk", "/对决", True),
        ("pk", "pk尾巴", False),
        ("injection", "注入查询", True),
        ("injection", "/摄入查询 历史", True),
    ],
)
def test_target_command_trigger_ranges(
    command_name: str,
    message: str,
    matched: bool,
):
    from nonebot_plugin_impart_plus.bot.matchers import (
        INJECTION_QUERY_COMMAND,
        PK_COMMAND,
    )

    commands = {
        "pk": PK_COMMAND,
        "injection": INJECTION_QUERY_COMMAND,
    }
    assert commands[command_name].parse(message).matched is matched


@pytest.mark.parametrize("history_first", [True, False])
def test_injection_history_option_accepts_either_position(history_first: bool):
    from nonebot_plugin_alconna import At, Text, UniMessage

    from nonebot_plugin_impart_plus.bot.matchers import INJECTION_QUERY_COMMAND

    message = (
        UniMessage([Text("注入查询 历史 "), At("user", "67890")])
        if history_first
        else UniMessage([Text("注入查询 "), At("user", "67890"), Text(" 全部")])
    )
    result = INJECTION_QUERY_COMMAND.parse(message)

    assert result.matched is True
    assert result.all_matched_args["target"].target == "67890"
    assert "history" in result.options


def test_pk_rejects_at_all():
    from nonebot_plugin_alconna import AtAll, Text, UniMessage

    from nonebot_plugin_impart_plus.bot.matchers import PK_COMMAND

    message = UniMessage(
        [Text("pk "), AtAll()],
    )

    assert PK_COMMAND.parse(message).matched is False


def test_pk_accepts_multiple_targets_and_keeps_their_order():
    from nonebot_plugin_alconna import At, Text, UniMessage

    from nonebot_plugin_impart_plus.bot.matchers import PK_COMMAND

    targets = (At("user", "67890"), At("user", "12345"))
    result = PK_COMMAND.parse(
        UniMessage([Text("pk "), targets[0], Text(" "), targets[1]])
    )

    assert result.matched is True
    assert result.all_matched_args["targets"] == targets


@pytest.mark.parametrize(
    ("command_name", "message", "matched"),
    [
        ("rank", "银趴排行榜", True),
        ("rank", "IMPARTrank", True),
        ("rank", "impartRank尾巴", False),
        ("rank", "/银趴排行榜", True),
        ("rank", "jj排行榜", False),
        ("rank", "牛牛rank", False),
        ("interaction", "日群友", True),
        ("interaction", "榨群友", True),
        ("interaction", "透 群主", True),
        ("interaction", "/榨 群主", True),
        ("interaction", "透群主尾巴", False),
        ("interaction", "榨汁群友", False),
        ("interaction", "/日群友", True),
    ],
)
def test_rank_and_interaction_regex_ranges(
    command_name: str,
    message: str,
    matched: bool,
):
    from nonebot_plugin_impart_plus.bot.matchers import (
        INTERACTION_COMMAND,
        RANK_COMMAND,
    )

    commands = {
        "rank": RANK_COMMAND,
        "interaction": INTERACTION_COMMAND,
    }
    assert commands[command_name].parse(message).matched is matched


@pytest.mark.parametrize(
    ("message", "kind", "action"),
    [
        ("透群友", "群友", "INJECT"),
        ("日管理", "管理", "INJECT"),
        ("榨群主", "群主", "SQUEEZE"),
    ],
)
def test_interaction_extracts_target_kind(
    message: str,
    kind: str,
    action: str,
) -> None:
    from nonebot_plugin_impart_plus.bot.matchers import (
        INTERACTION_ACTIONS,
        INTERACTION_COMMAND,
    )
    from nonebot_plugin_impart_plus.impart.core import InteractionAction

    result = INTERACTION_COMMAND.parse(message)

    assert result.matched is True
    assert result.all_matched_args["kind"] == kind
    assert (
        INTERACTION_ACTIONS[result.header_match.groups["action"]]
        is InteractionAction[action]
    )


def test_interaction_requires_kind_and_accepts_multiple_targets() -> None:
    from nonebot_plugin_alconna import At, Text, UniMessage

    from nonebot_plugin_impart_plus.bot.matchers import INTERACTION_COMMAND

    targets = (At("user", "67890"), At("user", "12345"))
    result = INTERACTION_COMMAND.parse(
        UniMessage([Text("榨群友 "), targets[0], Text(" "), targets[1]]),
    )

    assert result.matched is True
    assert result.all_matched_args == {
        "kind": "群友",
        "targets": targets,
    }
    assert INTERACTION_COMMAND.parse("透").matched is False
