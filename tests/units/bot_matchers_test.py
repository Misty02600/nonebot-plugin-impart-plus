import pytest

from .bot_test_utils import make_session


@pytest.mark.parametrize(
    ("message", "subcommand", "matched"),
    [
        ("银趴帮助", "help", True),
        ("银趴 帮助", "help", True),
        ("impart介绍", "help", True),
        ("银趴开启", "enable", True),
        ("银趴 禁止", "disable", True),
        ("开始银趴", "", False),
        ("关闭impart", "", False),
        ("银趴帮助尾巴", "", False),
        ("/银趴帮助", "", False),
    ],
)
def test_impart_command_group(
    message: str,
    subcommand: str,
    matched: bool,
):
    from nonebot_plugin_impart_plus.bot.matchers import IMPART_COMMAND

    result = IMPART_COMMAND.parse(message)
    assert result.matched is matched
    if matched:
        assert subcommand in result.subcommands


@pytest.mark.parametrize(
    ("message", "matched"),
    [
        ("打胶", True),
        ("开导", True),
        ("/打胶", False),
        ("打胶尾巴", False),
    ],
)
def test_growth_command_preserves_full_match(message: str, matched: bool):
    from nonebot_plugin_impart_plus.bot.matchers import GROW_COMMAND

    assert GROW_COMMAND.parse(message).matched is matched


@pytest.mark.parametrize(
    ("message", "matched"),
    [
        ("查询", True),
        ("/查询", True),
        ("查询尾巴", False),
        ("/查询 尾巴", False),
    ],
)
def test_query_command_uses_command_start(message: str, matched: bool):
    from nonebot_plugin_impart_plus.bot.matchers import QUERY_COMMAND

    assert QUERY_COMMAND.parse(message).matched is matched


@pytest.mark.parametrize(
    ("scene_type", "expected"),
    [
        (0, False),
        (1, True),
        (2, True),
        (3, True),
    ],
)
def test_public_scene_scope(scene_type: int, expected: bool):
    from nonebot_plugin_impart_plus.bot.context import public_scene

    assert public_scene(make_session(scene_type)) is expected


@pytest.mark.parametrize(
    ("command_name", "message", "matched"),
    [
        ("pk", "pk", False),
        ("pk", "/对决", False),
        ("pk", "pk尾巴", False),
        ("suo", "嗦牛子", True),
        ("suo", "/suo", True),
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
        SUO_COMMAND,
    )

    commands = {
        "pk": PK_COMMAND,
        "suo": SUO_COMMAND,
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


@pytest.mark.parametrize(
    ("command_name", "message", "matched"),
    [
        ("rank", "银趴排行榜", True),
        ("rank", "IMPARTrank", True),
        ("rank", "impartRank尾巴", False),
        ("rank", "/银趴排行榜", False),
        ("rank", "jj排行榜", False),
        ("rank", "牛牛rank", False),
        ("interaction", "日群友", True),
        ("interaction", "透 群主", True),
        ("interaction", "透群主尾巴", False),
        ("interaction", "/日群友", False),
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
