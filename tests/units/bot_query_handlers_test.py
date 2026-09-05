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


@pytest.mark.parametrize(
    ("total", "status"),
    [(200.0, "已经是xnn啦"), (200.001, "快要变成女孩子啦")],
)
async def test_query_merges_xnn_state_and_daily_total(
    monkeypatch: pytest.MonkeyPatch,
    total: float,
    status: str,
) -> None:
    from nonebot_plugin_alconna import At, CommandResult, Match
    from nonebot_plugin_uniref import SceneRef, UserRef

    from nonebot_plugin_impart_plus.bot.handlers import query
    from nonebot_plugin_impart_plus.bot.matchers import IMPART_COMMAND
    from nonebot_plugin_impart_plus.impart.app import QueryOutcome, QueryOutcomeType
    from nonebot_plugin_impart_plus.impart.core import LengthState

    calls: list[tuple[SceneRef, UserRef, UserRef, bool]] = []

    async def query_user(
        scene_ref: SceneRef,
        requester_ref: UserRef,
        target_ref: UserRef,
        *,
        history: bool,
    ) -> QueryOutcome:
        calls.append((scene_ref, requester_ref, target_ref, history))
        return QueryOutcome(
            QueryOutcomeType.COMPLETED,
            length=4.0,
            state=LengthState.XNN,
            today_total=total,
        )

    monkeypatch.setattr(query.game_app, "query_user", query_user)
    monkeypatch.setattr(query, "choice", lambda _: "牛牛")
    matcher = FinishingMatcherStub()

    with pytest.raises(FinishedException):
        await query.query_user(
            cast(Matcher, matcher),
            make_ref_context(scene_id="12345"),
            CommandResult(result=IMPART_COMMAND.parse("银趴查询")),
            Match(At("user", "67890"), True),
        )

    assert calls == [
        (make_scene_ref("12345"), make_user_ref(), make_user_ref("67890"), False)
    ]
    assert matcher.messages == [
        f"TA{status}！\nTA的牛牛目前长度为4.0cm喵\nTA当日总注入量为{total}ml"
    ]


async def test_history_query_appends_total_and_chart(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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

    from nonebot_plugin_impart_plus.bot.handlers import query
    from nonebot_plugin_impart_plus.bot.matchers import IMPART_COMMAND
    from nonebot_plugin_impart_plus.impart.app import QueryOutcome, QueryOutcomeType
    from nonebot_plugin_impart_plus.impart.core import LengthState

    async def query_user(
        _: SceneRef,
        __: UserRef,
        ___: UserRef,
        *,
        history: bool,
    ) -> QueryOutcome:
        assert history is True
        return QueryOutcome(
            QueryOutcomeType.COMPLETED,
            length=-2.5,
            state=LengthState.GIRL,
            today_total=5.5,
            history_total=8.5,
            history={"2026-08-30": 3.0, "2026-08-31": 5.5},
        )

    async def draw_line(_: dict[str, float]) -> bytes:
        return b"png"

    monkeypatch.setattr(query.game_app, "query_user", query_user)
    monkeypatch.setattr(query.draw_bar_chart, "draw_line_chart", draw_line)
    matcher = FinishingMatcherStub()

    with pytest.raises(FinishedException):
        await query.query_user(
            cast(Matcher, matcher),
            make_ref_context(scene_id="12345"),
            CommandResult(result=IMPART_COMMAND.parse("银趴查询历史")),
            Match(At("user", "unused"), False),
        )

    assert isinstance(matcher.raw_messages[0], UniMessage)
    assert isinstance(matcher.raw_messages[0][0], Text)
    assert isinstance(matcher.raw_messages[0][1], Image)
    assert "你的小学目前深度为2.5cm喵" in matcher.messages[0]
    assert "你当日总注入量为5.5ml" in matcher.messages[0]
    assert "你历史总注入量为8.5ml" in matcher.messages[0]
    assert matcher.options[0]["fallback"] is AUTO


async def test_query_uses_held_tier_for_title_in_retention_band(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from unittest.mock import AsyncMock

    from nonebot_plugin_alconna import At, CommandResult, Match

    from nonebot_plugin_impart_plus.bot.handlers import query
    from nonebot_plugin_impart_plus.bot.matchers import IMPART_COMMAND
    from nonebot_plugin_impart_plus.impart.app import QueryOutcome, QueryOutcomeType
    from nonebot_plugin_impart_plus.impart.core import classify_length

    for tier, length, positive, negative in (
        (1, 27, "日耀の柱", "虛空の眼"),
        (2, 310, "贯星长枪", "世界大穴"),
        (3, 1020, "牛々の神", "深淵の主"),
    ):
        for sign, title in ((1, positive), (-1, negative)):
            outcome = QueryOutcome(
                QueryOutcomeType.COMPLETED,
                length=sign * length,
                challenge_tier=tier,
                state=classify_length(sign * length, challenge_tier=tier),
            )
            monkeypatch.setattr(
                query.game_app, "query_user", AsyncMock(return_value=outcome)
            )
            matcher = FinishingMatcherStub()
            with pytest.raises(FinishedException):
                await query.query_user(
                    cast(Matcher, matcher),
                    make_ref_context(),
                    CommandResult(result=IMPART_COMMAND.parse("银趴查询")),
                    Match(At("user", "unused"), False),
                )
            assert title in matcher.messages[0]
