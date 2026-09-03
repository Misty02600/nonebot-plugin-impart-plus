from typing import cast

import pytest
from nonebot.exception import FinishedException
from nonebot.matcher import Matcher

from .bot_test_utils import (
    FinishingMatcherStub,
    make_ref_context,
    make_scene_ref,
    make_user_ref,
)


async def test_injection_query_reads_typed_target_and_history_option(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_alconna import At, CommandResult, Match
    from nonebot_plugin_uniref import SceneRef, UserRef

    from nonebot_plugin_impart_plus.bot.handlers import records
    from nonebot_plugin_impart_plus.bot.matchers import INJECTION_QUERY_COMMAND
    from nonebot_plugin_impart_plus.impart.app import (
        InjectionQueryResult,
        InjectionQueryType,
    )

    calls: list[tuple[SceneRef, UserRef, bool]] = []

    async def query_injection(
        scene_ref: SceneRef,
        user_ref: UserRef,
        *,
        history: bool,
    ) -> InjectionQueryResult:
        calls.append((scene_ref, user_ref, history))
        return InjectionQueryResult(InjectionQueryType.HISTORY_TEXT, total=8.5)

    monkeypatch.setattr(records.game_app, "query_injection", query_injection)
    matcher = FinishingMatcherStub()

    with pytest.raises(FinishedException):
        await records.query_injection(
            cast(Matcher, matcher),
            make_ref_context(scene_id="12345"),
            CommandResult(result=INJECTION_QUERY_COMMAND.parse("注入查询 历史")),
            Match(
                At("user", "67890"),
                True,
            ),
        )

    assert calls == [(make_scene_ref("12345"), make_user_ref("67890"), True)]
    assert matcher.messages == ["该用户历史总被注射量为8.5ml"]


async def test_rank_uses_uninfo_user_directory(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_uninfo import Interface, User
    from nonebot_plugin_uniref import SceneRef, UserRef

    from nonebot_plugin_impart_plus.bot.handlers import records
    from nonebot_plugin_impart_plus.impart.app import (
        RankingEntry,
        RankingOutcome,
        RankingOutcomeType,
    )

    ranking = [
        RankingEntry(make_user_ref(str(user_id)), float(user_id))
        for user_id in range(1, 11)
    ]
    app_calls: list[tuple[SceneRef, UserRef]] = []
    user_calls: list[str] = []
    chart_data: list[dict[str, float]] = []

    async def query_ranking(
        scene_ref: SceneRef,
        user_ref: UserRef,
    ) -> RankingOutcome:
        app_calls.append((scene_ref, user_ref))
        return RankingOutcome(
            RankingOutcomeType.COMPLETED,
            ranking=ranking,
            index=3,
        )

    class InterfaceStub:
        async def get_user(self, user_id: str) -> User:
            user_calls.append(user_id)
            return User(id=user_id, nick=f"用户{user_id}")

    async def draw_bar(data: dict[str, float]) -> bytes:
        chart_data.append(data)
        return b"png"

    monkeypatch.setattr(records.game_app, "query_ranking", query_ranking)
    monkeypatch.setattr(records.draw_bar_chart, "draw_bar_chart", draw_bar)
    matcher = FinishingMatcherStub()

    with pytest.raises(FinishedException):
        await records.jjrank(
            cast(Matcher, matcher),
            make_ref_context(scene_id="12345"),
            cast(Interface, InterfaceStub()),
        )

    assert app_calls == [(make_scene_ref("12345"), make_user_ref())]
    assert user_calls == ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    assert chart_data[0]["用户1"] == 1.0
    assert chart_data[0]["用户10"] == 10.0
    assert "你的排名为4喵" in matcher.messages[0]
    from nonebot_plugin_alconna import AUTO, Image, Text, UniMessage

    assert isinstance(matcher.raw_messages[0], UniMessage)
    assert isinstance(matcher.raw_messages[0][0], Image)
    assert isinstance(matcher.raw_messages[0][1], Text)
    assert matcher.options[0]["fallback"] is AUTO


async def test_injection_history_chart_uses_unimessage_image(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_alconna import (
        AUTO,
        At,
        CommandResult,
        Image,
        Match,
        Text,
        UniMessage,
    )
    from nonebot_plugin_uniref import SceneRef, UserRef

    from nonebot_plugin_impart_plus.bot.handlers import records
    from nonebot_plugin_impart_plus.bot.matchers import INJECTION_QUERY_COMMAND
    from nonebot_plugin_impart_plus.impart.app import (
        InjectionQueryResult,
        InjectionQueryType,
    )

    async def query_injection(
        _: SceneRef,
        __: UserRef,
        *,
        history: bool,
    ) -> InjectionQueryResult:
        assert history is True
        return InjectionQueryResult(
            InjectionQueryType.HISTORY_CHART,
            total=8.5,
            history={"2026-08-30": 3.0, "2026-08-31": 5.5},
        )

    async def draw_line(_: dict[str, float]) -> bytes:
        return b"png"

    monkeypatch.setattr(records.game_app, "query_injection", query_injection)
    monkeypatch.setattr(records.draw_bar_chart, "draw_line_chart", draw_line)
    matcher = FinishingMatcherStub()

    with pytest.raises(FinishedException):
        await records.query_injection(
            cast(Matcher, matcher),
            make_ref_context(scene_id="12345"),
            CommandResult(result=INJECTION_QUERY_COMMAND.parse("注入查询 历史")),
            Match(At("user", "unused"), False),
        )

    assert isinstance(matcher.raw_messages[0], UniMessage)
    assert isinstance(matcher.raw_messages[0][0], Text)
    assert isinstance(matcher.raw_messages[0][1], Image)
    assert matcher.options[0]["fallback"] is AUTO
