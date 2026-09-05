from typing import cast
from unittest.mock import AsyncMock

import pytest
from nonebot.exception import FinishedException, SkippedException
from nonebot.matcher import Matcher

from .bot_test_utils import FinishingMatcherStub, make_ref_context, make_user_ref


async def test_possession_uses_first_target_and_one_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_alconna import At, Match

    from nonebot_plugin_impart_plus.bot.handlers import possession
    from nonebot_plugin_impart_plus.impart.app import PossessionOutcome
    from nonebot_plugin_impart_plus.impart.core import PossessionStatus

    execute = AsyncMock(
        return_value=PossessionOutcome(
            PossessionStatus.COMPLETED,
            half=24.999,
            target_status="challenge_completed_reduce",
        )
    )
    monkeypatch.setattr(possession.game_app, "execute_possession", execute)
    name_calls = []

    def name(_):
        name_calls.append(1)
        return "牛牛"

    monkeypatch.setattr(possession, "choice", name)
    matcher = FinishingMatcherStub()
    refs = make_ref_context()
    with pytest.raises(FinishedException):
        await possession.possess(
            cast(Matcher, matcher),
            refs,
            Match((At("user", "2"), At("user", "3")), True),
        )
    execute.assert_awaited_once_with(refs.scene_ref, refs.user_ref, make_user_ref("2"))
    assert name_calls == [1]
    assert len(matcher.messages) == 1
    text = matcher.messages[0]
    assert text.count("24.999cm") == 2
    assert "由于你的夺舍" in text
    assert "长度缩短了5cm" in text
    assert "变成xnn" not in text

    execute.reset_mock()
    with pytest.raises(SkippedException):
        await possession.possess(
            cast(Matcher, matcher),
            refs,
            Match((At("role", "admin"), At("user", "2")), True),
        )
    execute.assert_not_awaited()


async def test_possession_missing_target_and_self_rejection_copy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_alconna import At, Match

    from nonebot_plugin_impart_plus.bot.handlers import possession
    from nonebot_plugin_impart_plus.impart.app import PossessionOutcome
    from nonebot_plugin_impart_plus.impart.core import PossessionStatus

    execute = AsyncMock(
        side_effect=[
            PossessionOutcome(PossessionStatus.MISSING_TARGET),
            PossessionOutcome(PossessionStatus.WRONG_TARGET),
            PossessionOutcome(PossessionStatus.LOCKED),
        ]
    )
    monkeypatch.setattr(possession.game_app, "execute_possession", execute)
    monkeypatch.setattr(possession, "choice", lambda _: "牛牛")
    messages = []
    for available in (False, True, True):
        matcher = FinishingMatcherStub()
        with pytest.raises(FinishedException):
            await possession.possess(
                cast(Matcher, matcher),
                make_ref_context(),
                Match((At("user", "10001"),), available),
            )
        messages.extend(matcher.messages)
    assert messages == [
        "请at你要夺舍的目标",
        "你不能夺舍没有牛牛的人！",
        "你尚未解锁此禁忌之术...",
    ]
