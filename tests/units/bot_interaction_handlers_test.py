from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest
from arclet.alconna import Arparma
from nonebot.exception import FinishedException
from nonebot.matcher import Matcher

from .bot_test_utils import (
    FinishingMatcherStub,
    MatcherStub,
    make_ref_context,
    make_scene_ref,
    make_session,
    make_user_ref,
)


def _parse_interaction(action: str, kind: str) -> Arparma:
    from nonebot_plugin_impart_plus.bot.matchers import INTERACTION_COMMAND

    result = INTERACTION_COMMAND.parse(f"{action}{kind}")
    assert result.matched
    return result


def _receipt(
    volume: float,
    total: float,
    length: float,
    *,
    warning: bool = False,
    feminized: bool = False,
):
    from nonebot_plugin_impart_plus.impart.app import InteractionReceipt
    from nonebot_plugin_impart_plus.impart.core import InteractionVolumeSettlement

    return InteractionReceipt(
        volume, InteractionVolumeSettlement(total, length, warning, feminized)
    )


async def test_explicit_interaction_uses_only_first_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_alconna import At, Match
    from nonebot_plugin_uninfo import Interface, Member, User
    from nonebot_plugin_uniref import SceneRef, UserRef

    from nonebot_plugin_impart_plus.bot.handlers import interaction
    from nonebot_plugin_impart_plus.impart.app import (
        InteractionGuard,
        InteractionGuardType,
        InteractionResult,
    )
    from nonebot_plugin_impart_plus.impart.core import (
        InteractionAction,
        InteractionResolution,
        resolve_interaction,
    )

    resolution = resolve_interaction(
        InteractionAction.INJECT,
        10.0,
        10.0,
    )
    prepare_calls: list[tuple[SceneRef, UserRef]] = []
    begin_calls: list[tuple[UserRef, UserRef, InteractionAction]] = []

    async def prepare_interaction(
        scene_ref: SceneRef,
        user_ref: UserRef,
    ) -> InteractionGuard:
        prepare_calls.append((scene_ref, user_ref))
        return InteractionGuard(InteractionGuardType.ALLOWED)

    async def begin_interaction(
        user_ref: UserRef,
        target_ref: UserRef,
        requested_action: InteractionAction,
    ) -> InteractionResolution:
        begin_calls.append((user_ref, target_ref, requested_action))
        return resolution

    async def complete_interaction(
        _: UserRef,
        __: UserRef,
        prepared: InteractionResolution,
    ) -> InteractionResult:
        assert prepared is resolution
        return InteractionResult(
            resolution,
            3,
            {resolution.transfers[0].recipient: _receipt(2.5, 8.0, 10.0)},
        )

    class InterfaceStub:
        async def get_members(self, *_: object) -> list[Member]:
            raise AssertionError("显式 At 不应枚举成员")

        async def get_member(self, *_: object) -> Member:
            return Member(
                User(
                    id="67890",
                    nick="目标",
                    avatar="https://example.com/avatar.png",
                )
            )

        async def get_user(self, user_id: str) -> User:
            return User(id=user_id, nick="目标")

    monkeypatch.setattr(
        interaction.game_app, "prepare_interaction", prepare_interaction
    )
    monkeypatch.setattr(interaction.game_app, "begin_interaction", begin_interaction)
    monkeypatch.setattr(
        interaction.game_app, "complete_interaction", complete_interaction
    )
    monkeypatch.setattr(interaction.asyncio, "sleep", AsyncMock())
    matcher = MatcherStub()

    await interaction.yinpa(
        cast(Matcher, matcher),
        make_session(1, "12345"),
        cast(Interface, InterfaceStub()),
        make_ref_context(scene_id="12345"),
        _parse_interaction("透", "群友"),
        "群友",
        Match((At("user", "67890"), At("user", "99999")), True),
    )

    assert prepare_calls == [(make_scene_ref("12345"), make_user_ref())]
    assert begin_calls == [
        (
            make_user_ref(),
            make_user_ref("67890"),
            InteractionAction.INJECT,
        )
    ]
    assert len(matcher.messages) == 1
    assert "给 目标(67890) 注入了2.5毫升的脱氧核糖核酸" in matcher.messages[0]
    from nonebot_plugin_alconna import AUTO, Image, Text, UniMessage

    assert isinstance(matcher.raw_messages[0], UniMessage)
    assert isinstance(matcher.raw_messages[0][0], Text)
    assert isinstance(matcher.raw_messages[0][1], Image)
    assert matcher.options[0]["fallback"] is AUTO


async def test_non_user_first_mention_skips_before_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot.exception import SkippedException
    from nonebot_plugin_alconna import At, Match
    from nonebot_plugin_uninfo import Interface

    from nonebot_plugin_impart_plus.bot.handlers import interaction

    prepare_interaction = AsyncMock()
    monkeypatch.setattr(
        interaction.game_app,
        "prepare_interaction",
        prepare_interaction,
    )

    with pytest.raises(SkippedException):
        await interaction.yinpa(
            cast(Matcher, MatcherStub()),
            make_session(1, "12345"),
            cast(Interface, object()),
            make_ref_context(scene_id="12345"),
            _parse_interaction("透", "群友"),
            "群友",
            Match((At("role", "1"), At("user", "67890")), True),
        )

    prepare_interaction.assert_not_awaited()


async def test_new_requester_stops_before_target_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_alconna import Match
    from nonebot_plugin_uninfo import Interface

    from nonebot_plugin_impart_plus.bot.handlers import interaction
    from nonebot_plugin_impart_plus.impart.app import (
        InteractionGuard,
        InteractionGuardType,
    )

    user_ref = make_user_ref()
    monkeypatch.setattr(
        interaction.game_app,
        "prepare_interaction",
        AsyncMock(
            return_value=InteractionGuard(
                InteractionGuardType.USER_CREATED,
                created_users=(user_ref,),
            )
        ),
    )
    begin_interaction = AsyncMock()
    monkeypatch.setattr(interaction.game_app, "begin_interaction", begin_interaction)
    monkeypatch.setattr(interaction, "created_user_message", lambda *_: "已创建")
    matcher = FinishingMatcherStub()

    with pytest.raises(FinishedException):
        await interaction.yinpa(
            cast(Matcher, matcher),
            make_session(1, "12345"),
            cast(Interface, object()),
            make_ref_context(scene_id="12345"),
            _parse_interaction("榨", "群友"),
            "群友",
            Match((), False),
        )

    begin_interaction.assert_not_awaited()
    assert matcher.messages == ["已创建"]
    assert matcher.options == [{"at_sender": True}]


@pytest.mark.parametrize(
    ("action", "kind", "members_kind", "expected"),
    [
        ("透", "群友", "empty", "请艾特指定目标"),
        ("透", "管理", "regular", "喵喵喵? 找不到群管理!"),
        ("透", "群主", "regular", "喵喵喵? 找不到群主!"),
        ("榨", "群友", "self", "喵喵喵? 找不到群友!"),
        ("榨", "群主", "self_owner", "你榨你自己?"),
    ],
)
async def test_invalid_automatic_targets_do_not_begin_interaction(
    monkeypatch: pytest.MonkeyPatch,
    action: str,
    kind: str,
    members_kind: str,
    expected: str,
) -> None:
    from nonebot_plugin_alconna import At, Match
    from nonebot_plugin_uninfo import Interface, Member, Role, User

    from nonebot_plugin_impart_plus.bot.handlers import interaction
    from nonebot_plugin_impart_plus.impart.app import (
        InteractionGuard,
        InteractionGuardType,
    )

    members = {
        "empty": [],
        "regular": [Member(User(id="20002"))],
        "self": [Member(User(id="10001"))],
        "self_owner": [
            Member(User(id="10001"), roles=[Role("OWNER", 100)]),
        ],
    }[members_kind]

    class InterfaceStub:
        async def get_members(self, *_: object) -> list[Member]:
            return members

    monkeypatch.setattr(
        interaction.game_app,
        "prepare_interaction",
        AsyncMock(return_value=InteractionGuard(InteractionGuardType.ALLOWED)),
    )
    begin_interaction = AsyncMock()
    monkeypatch.setattr(interaction.game_app, "begin_interaction", begin_interaction)
    matcher = FinishingMatcherStub()
    ignored_targets = (
        Match((At("user", "67890"), At("user", "99999")), True)
        if kind != "群友"
        else Match((), False)
    )

    with pytest.raises(FinishedException):
        await interaction.yinpa(
            cast(Matcher, matcher),
            make_session(1, "12345"),
            cast(Interface, InterfaceStub()),
            make_ref_context(scene_id="12345"),
            _parse_interaction(action, kind),
            kind,
            ignored_targets,
        )

    begin_interaction.assert_not_awaited()
    assert matcher.messages == [expected]


def test_role_target_selection_excludes_requester_from_admins() -> None:
    from nonebot_plugin_uninfo import Member, Role, User

    from nonebot_plugin_impart_plus.bot.handlers.interaction import (
        select_interaction_target,
    )

    members = [
        Member(User(id="10001"), roles=[Role("ADMINISTRATOR", 10)]),
        Member(User(id="20002"), roles=[Role("ADMINISTRATOR", 10)]),
        Member(User(id="30003"), roles=[Role("OWNER", 100)]),
    ]

    assert select_interaction_target("管理", members, "10001") == "20002"
    assert select_interaction_target("群主", members, "10001") == "30003"
    assert select_interaction_target("管理", members[:1], "10001") is None


@pytest.mark.parametrize(
    (
        "requested",
        "requester_length",
        "target_length",
        "kind",
        "expected",
    ),
    [
        ("INJECT", 10.0, 10.0, "群主", "现在咱将把群主\n送给发起者色色！"),
        (
            "INJECT",
            3.0,
            4.0,
            "群友",
            "BOT发现你俩都是xnn喵~现在咱将发起者\n送给目标色色！",
        ),
        (
            "SQUEEZE",
            3.0,
            4.0,
            "管理",
            "BOT发现你俩都是xnn喵~现在咱将发起者\n送给目标色色！",
        ),
        (
            "INJECT",
            3.0,
            4.0,
            "群主",
            "BOT发现你俩都是xnn喵~现在咱将发起者\n送给目标色色！",
        ),
        (
            "INJECT",
            -10.0,
            10.0,
            "管理",
            "唔...你透不了哦~\n现在咱将发起者\n送给随机一位管理色色！",
        ),
        (
            "SQUEEZE",
            10.0,
            -10.0,
            "群友",
            "唔...你榨不了哦~\n现在咱将发起者\n送给随机一位幸运群友色色！",
        ),
        (
            "INJECT",
            3.0,
            10.0,
            "群友",
            "BOT发现你是xnn~现在咱将发起者\n送给随机一位幸运群友色色！",
        ),
    ],
)
async def test_interaction_prompt_matches_resolution(
    monkeypatch: pytest.MonkeyPatch,
    requested: str,
    requester_length: float,
    target_length: float,
    kind: str,
    expected: str,
) -> None:
    from nonebot_plugin_impart_plus.bot.handlers import interaction
    from nonebot_plugin_impart_plus.impart.core import (
        InteractionAction,
        resolve_interaction,
    )

    monkeypatch.setattr(interaction, "botname", "BOT")
    action = InteractionAction[requested]
    resolution = resolve_interaction(
        action,
        requester_length,
        target_length,
    )
    matcher = MatcherStub()

    await interaction.send_interaction_prompt(
        kind,
        "发起者",
        cast(Matcher, matcher),
        action,
        resolution,
        "目标",
    )

    assert matcher.messages == [expected]


@pytest.mark.parametrize(
    (
        "requested",
        "requester_length",
        "target_length",
        "expected",
    ),
    [
        (
            "INJECT",
            10.0,
            10.0,
            "好欸！发起者(10001)用时4秒 \n给 目标(20002) 注入了12.5毫升的脱氧核糖核酸, 当日总注入量为：20.0毫升\n",
        ),
        (
            "INJECT",
            -10.0,
            10.0,
            "好欸！目标(20002)用时4秒 \n给 发起者(10001) 注入了12.5毫升的脱氧核糖核酸, 当日总注入量为：20.0毫升\n",
        ),
        (
            "SQUEEZE",
            -10.0,
            -10.0,
            "好欸！发起者(10001)用时4秒 \n从 目标(20002) 榨出了12.5毫升的妹汁, 当日总注入量为：20.0毫升\n",
        ),
        (
            "SQUEEZE",
            10.0,
            -10.0,
            "好欸！目标(20002)用时4秒 \n从 发起者(10001) 榨出了12.5毫升的脱氧核糖核酸, 当日总注入量为：20.0毫升\n",
        ),
    ],
)
def test_interaction_report_matches_actual_action(
    requested: str,
    requester_length: float,
    target_length: float,
    expected: str,
) -> None:
    from nonebot_plugin_impart_plus.bot.handlers.interaction import interaction_report
    from nonebot_plugin_impart_plus.impart.app import InteractionResult
    from nonebot_plugin_impart_plus.impart.core import (
        InteractionAction,
        resolve_interaction,
    )

    resolution = resolve_interaction(
        InteractionAction[requested],
        requester_length,
        target_length,
    )
    result = InteractionResult(
        resolution,
        4,
        {resolution.transfers[0].recipient: _receipt(12.5, 20.0, target_length)},
    )

    assert interaction_report(result, "发起者", "10001", "目标", "20002") == expected


def test_interaction_report_appends_risk_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_impart_plus.bot.handlers import interaction
    from nonebot_plugin_impart_plus.impart.app import InteractionResult
    from nonebot_plugin_impart_plus.impart.core import (
        InteractionAction,
        resolve_interaction,
    )

    resolution = resolve_interaction(
        InteractionAction.INJECT,
        10.0,
        4.0,
    )
    monkeypatch.setattr(interaction, "choice", lambda _: "牛牛")
    recipient = resolution.transfers[0].recipient
    warning = InteractionResult(
        resolution, 4, {recipient: _receipt(20.0, 210.0, 4.0, warning=True)}
    )
    feminized = InteractionResult(
        resolution, 4, {recipient: _receipt(20.0, 1010.0, -1.0, feminized=True)}
    )

    warning_text = interaction.interaction_report(
        warning,
        "发起者",
        "10001",
        "目标",
        "20002",
    )
    feminized_text = interaction.interaction_report(
        feminized,
        "发起者",
        "10001",
        "目标",
        "20002",
    )

    assert warning_text.endswith(
        "由于目标(20002)的当日注入量过多，TA的牛牛开始变得不稳定了..."
    )
    assert "目标(20002)被注入了太多脱氧核糖核酸……" in feminized_text
    assert "在发起者(10001)的猛烈攻势下，TA的牛牛彻底萎缩消失了♡" in feminized_text
    assert "取而代之的是一个深度1.0cm的小学♡" in feminized_text
    assert feminized_text.endswith("目标(20002)已经完全雌堕，变成了女孩子喵！")


def test_cuddle_report_keeps_outputs_totals_and_events_in_member_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_impart_plus.bot.handlers import interaction
    from nonebot_plugin_impart_plus.impart.app import InteractionResult
    from nonebot_plugin_impart_plus.impart.core import (
        InteractionAction,
        InteractionParticipant,
        resolve_interaction,
    )

    resolution = resolve_interaction(InteractionAction.INJECT, 3.0, 4.0)
    result = InteractionResult(
        resolution,
        4,
        {
            InteractionParticipant.REQUESTER: _receipt(
                3.0, 993.0, -2.0, feminized=True
            ),
            InteractionParticipant.TARGET: _receipt(7.0, 207.0, 4.0, warning=True),
        },
    )
    monkeypatch.setattr(interaction, "choice", lambda _: "牛牛")
    report = interaction.interaction_report(result, "发起者", "10001", "目标", "20002")
    assert "发起者(10001)和目标(20002)蹭蹭贴贴了4秒" in report
    assert "分别挤出了7.0毫升和3.0毫升" in report
    assert "当日总注入量分别为：993.0毫升、207.0毫升" in report
    assert "在一阵缠绵后" in report
    assert report.index("发起者(10001)被注入了太多") < report.index("由于目标(20002)")
    assert "由于发起者" not in report


def test_squeeze_event_uses_recipient_and_frozen_fluid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_impart_plus.bot.handlers import interaction
    from nonebot_plugin_impart_plus.impart.app import InteractionResult
    from nonebot_plugin_impart_plus.impart.core import (
        InteractionAction,
        InteractionParticipant,
        resolve_interaction,
    )

    resolution = resolve_interaction(InteractionAction.SQUEEZE, -30.0, -10.0)
    result = InteractionResult(
        resolution,
        4,
        {
            InteractionParticipant.REQUESTER: _receipt(
                20.0, 1010.0, -2.0, feminized=True
            ),
        },
    )
    monkeypatch.setattr(interaction, "choice", lambda _: "牛牛")
    report = interaction.interaction_report(result, "发起者", "10001", "目标", "20002")
    assert "榨出了20.0毫升的妹汁" in report
    assert "发起者(10001)被注入了太多妹汁" in report
    assert "在发起者(10001)的主动索求下" in report
    assert "猛烈攻势" not in report


async def test_late_cooldown_rejection_stops_before_profile_and_animation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_alconna import At, Match
    from nonebot_plugin_uninfo import Interface

    from nonebot_plugin_impart_plus.bot.handlers import interaction
    from nonebot_plugin_impart_plus.impart.app import (
        InteractionGuard,
        InteractionGuardType,
    )

    monkeypatch.setattr(
        interaction.game_app,
        "prepare_interaction",
        AsyncMock(
            return_value=InteractionGuard(InteractionGuardType.ALLOWED),
        ),
    )
    monkeypatch.setattr(
        interaction.game_app,
        "begin_interaction",
        AsyncMock(
            return_value=InteractionGuard(
                InteractionGuardType.COOLING_DOWN, remaining=60
            ),
        ),
    )
    complete = AsyncMock()
    sleep = AsyncMock()
    profile = AsyncMock()
    monkeypatch.setattr(interaction.game_app, "complete_interaction", complete)
    monkeypatch.setattr(interaction.asyncio, "sleep", sleep)
    monkeypatch.setattr(interaction, "get_member_or_none", profile)
    matcher = FinishingMatcherStub()
    with pytest.raises(FinishedException):
        await interaction.yinpa(
            cast(Matcher, matcher),
            make_session(1, "12345"),
            cast(Interface, object()),
            make_ref_context(scene_id="12345"),
            _parse_interaction("透", "群友"),
            "群友",
            Match((At("user", "67890"),), True),
        )
    assert "请先休息60秒" in matcher.messages[0]
    complete.assert_not_awaited()
    sleep.assert_not_awaited()
    profile.assert_not_awaited()


async def test_member_query_exception_is_logged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_uninfo import Interface, Member

    from nonebot_plugin_impart_plus.bot.handlers import shared

    failure = RuntimeError("member query failed")

    class InterfaceStub:
        async def get_members(self, *_: object) -> list[Member]:
            raise failure

    session = make_session(1, "12345")
    logger = Mock()
    monkeypatch.setattr(shared, "logger", logger)

    members = await shared.get_members_or_empty(
        cast(Interface, InterfaceStub()),
        session,
    )

    assert members == []
    logger.opt.assert_called_once_with(exception=failure)
    logger.opt.return_value.warning.assert_called_once_with(
        "获取成员列表失败: adapter={}, scene_type={}",
        session.adapter,
        session.scene.type.name,
    )
