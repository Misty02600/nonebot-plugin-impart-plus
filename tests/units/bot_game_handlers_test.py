from typing import cast

import pytest
from nonebot.exception import FinishedException
from nonebot.matcher import Matcher

from .bot_test_utils import FinishingMatcherStub, MatcherStub, make_session


async def test_growth_handler_uses_uninfo_identity(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_impart_plus.bot.handlers import game
    from nonebot_plugin_impart_plus.impart.app import GrowthOutcome, GrowthOutcomeType

    calls: list[tuple[int, str]] = []

    async def grow_self(scene_id: int, user_id: str) -> GrowthOutcome:
        calls.append((scene_id, user_id))
        return GrowthOutcome(
            GrowthOutcomeType.COMPLETED,
            random_num=1.25,
            new_length=11.25,
        )

    monkeypatch.setattr(game.game_app, "grow_self", grow_self)
    matcher = MatcherStub()

    await game.dajiao(
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
    from nonebot_plugin_alconna import At, Match

    from nonebot_plugin_impart_plus.bot.handlers import game
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

    monkeypatch.setattr(game.game_app, "query_user", query_user)
    matcher = MatcherStub()

    await game.queryjj(
        cast(Matcher, matcher),
        make_session(1, "12345"),
        Match(At("user", "67890"), True),
    )

    assert calls == [(12345, 67890)]
    assert len(matcher.messages) == 1
    assert "TA的" in matcher.messages[0]
    assert "12.5cm" in matcher.messages[0]


async def test_pk_handler_requires_and_uses_mention(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_alconna import At

    from nonebot_plugin_impart_plus.bot.handlers import game
    from nonebot_plugin_impart_plus.impart.app import PkOutcome, PkOutcomeType

    calls: list[tuple[int, str, str]] = []

    async def execute_pk(
        scene_id: int,
        attacker_id: str,
        defender_id: str,
    ) -> PkOutcome:
        calls.append((scene_id, attacker_id, defender_id))
        return PkOutcome(PkOutcomeType.USERS_CREATED)

    monkeypatch.setattr(game.game_app, "execute_pk", execute_pk)
    matcher = FinishingMatcherStub()
    with pytest.raises(FinishedException):
        await game.pk(
            cast(Matcher, matcher),
            make_session(1, "12345"),
            At("user", "67890"),
        )

    assert calls == [(12345, "10001", "67890")]
    assert len(matcher.messages) == 1


async def test_suo_handler_defaults_to_self(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_alconna import At, Match

    from nonebot_plugin_impart_plus.bot.handlers import game
    from nonebot_plugin_impart_plus.impart.app import GrowthOutcome, GrowthOutcomeType

    calls: list[tuple[int, str, int]] = []

    async def grow_target(
        scene_id: int,
        user_id: str,
        target_id: int,
    ) -> GrowthOutcome:
        calls.append((scene_id, user_id, target_id))
        return GrowthOutcome(
            GrowthOutcomeType.COMPLETED,
            random_num=1.5,
            new_length=11.5,
        )

    monkeypatch.setattr(game.game_app, "grow_target", grow_target)
    matcher = FinishingMatcherStub()

    with pytest.raises(FinishedException):
        await game.suo(
            cast(Matcher, matcher),
            make_session(1, "12345"),
            Match(At("user", "unused"), False),
        )

    assert calls == [(12345, "10001", 10001)]
    assert "你的" in matcher.messages[0]
