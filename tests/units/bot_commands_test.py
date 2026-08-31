from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

import pytest
from nonebot.matcher import Matcher

if TYPE_CHECKING:
    from nonebot_plugin_uninfo import Session


def make_session(scene_type: int, scene_id: str = "42") -> "Session":
    from nonebot_plugin_uninfo import Scene, SceneType, Session, User

    return Session(
        self_id="10000",
        adapter="OneBot V11",
        scope="QQClient",
        scene=Scene(id=scene_id, type=SceneType(scene_type)),
        user=User(id="10001"),
    )


@dataclass
class MatcherStub:
    messages: list[str] = field(default_factory=list)

    async def finish(self, message: str, **_: object) -> None:
        self.messages.append(message)


@pytest.mark.parametrize(
    ("message", "matched"),
    [
        ("银趴帮助", True),
        ("IMPART介绍", True),
        ("银趴帮助尾巴", False),
        ("/银趴帮助", False),
    ],
)
def test_help_command_preserves_regex_range(message: str, matched: bool):
    from nonebot_plugin_impart_plus.bot.commands import HELP_COMMAND

    assert HELP_COMMAND.parse(message).matched is matched


@pytest.mark.parametrize(
    ("message", "matched"),
    [
        ("开始银趴", True),
        ("关闭IMPART", True),
        ("开启impart尾巴", True),
        ("/开始银趴", False),
        ("请开始银趴", False),
    ],
)
def test_toggle_command_preserves_regex_range(message: str, matched: bool):
    from nonebot_plugin_impart_plus.bot.commands import TOGGLE_COMMAND

    assert TOGGLE_COMMAND.parse(message).matched is matched


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
    from nonebot_plugin_impart_plus.bot.commands import GROW_COMMAND

    assert GROW_COMMAND.parse(message).matched is matched


@pytest.mark.parametrize(
    ("message", "matched"),
    [
        ("查询", True),
        ("/查询", True),
        ("查询尾巴", False),
        ("/查询 尾巴", True),
    ],
)
def test_query_command_uses_command_start(message: str, matched: bool):
    from nonebot_plugin_impart_plus.bot.commands import QUERY_COMMAND

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
    ("message", "enabled", "reply"),
    [
        ("开始银趴", True, "功能已开启喵"),
        ("禁止impart", False, "功能已禁用喵"),
    ],
)
async def test_toggle_handler_uses_uninfo_scene(
    monkeypatch: pytest.MonkeyPatch,
    message: str,
    enabled: bool,
    reply: str,
):
    from nonebot_plugin_alconna import CommandResult
    from nonebot_plugin_uninfo import SceneType

    from nonebot_plugin_impart_plus.bot.commands import TOGGLE_COMMAND
    from nonebot_plugin_impart_plus.bot.handlers import game_app, impart

    calls: list[tuple[int, bool]] = []

    async def set_group_enabled(scene_id: int, value: bool) -> None:
        calls.append((scene_id, value))

    monkeypatch.setattr(game_app, "set_group_enabled", set_group_enabled)
    matcher = MatcherStub()
    result = CommandResult(result=TOGGLE_COMMAND.parse(message))

    await impart.open_module(
        cast(Matcher, matcher),
        make_session(SceneType.GROUP, "12345"),
        result,
    )

    assert calls == [(12345, enabled)]
    assert matcher.messages == [reply]


async def test_growth_handler_uses_uninfo_identity(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_impart_plus.bot.handlers import game_app, impart
    from nonebot_plugin_impart_plus.impart.app import GrowthOutcome, GrowthOutcomeType

    calls: list[tuple[int, str]] = []

    async def grow_self(scene_id: int, user_id: str) -> GrowthOutcome:
        calls.append((scene_id, user_id))
        return GrowthOutcome(
            GrowthOutcomeType.COMPLETED,
            random_num=1.25,
            new_length=11.25,
        )

    monkeypatch.setattr(game_app, "grow_self", grow_self)
    matcher = MatcherStub()

    await impart.dajiao(
        cast(Matcher, matcher),
        make_session(1, "12345"),
    )

    assert calls == [(12345, "10001")]
    assert len(matcher.messages) == 1
    assert "长了1.25cm" in matcher.messages[0]
    assert "目前长度为11.25cm" in matcher.messages[0]


async def test_query_handler_prefers_typed_mention(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_alconna import At, Match, UniMessage

    from nonebot_plugin_impart_plus.bot.handlers import game_app, impart
    from nonebot_plugin_impart_plus.impart.app import QueryOutcome, QueryOutcomeType
    from nonebot_plugin_impart_plus.impart.core import LengthState

    calls: list[tuple[int, int]] = []

    async def query_user(scene_id: int, user_id: int) -> QueryOutcome:
        calls.append((scene_id, user_id))
        return QueryOutcome(
            QueryOutcomeType.COMPLETED,
            length=12.5,
            state=LengthState.NORMAL,
        )

    monkeypatch.setattr(game_app, "query_user", query_user)
    matcher = MatcherStub()

    await impart.queryjj(
        cast(Matcher, matcher),
        make_session(1, "12345"),
        Match(At("user", "67890"), True),
        Match(UniMessage(), False),
    )

    assert calls == [(12345, 67890)]
    assert len(matcher.messages) == 1
    assert "TA的" in matcher.messages[0]
    assert "12.5cm" in matcher.messages[0]


def test_mention_can_be_recovered_from_tail():
    from nonebot_plugin_alconna import At, Match, Text, UniMessage

    from nonebot_plugin_impart_plus.bot.context import mentioned_user_id

    assert (
        mentioned_user_id(
            Match(At("user", "unused"), False),
            Match(UniMessage([Text("前置文字 "), At("user", "67890")]), True),
        )
        == "67890"
    )
