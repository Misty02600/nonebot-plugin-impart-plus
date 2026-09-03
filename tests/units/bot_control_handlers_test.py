from typing import cast

import pytest
from nonebot.matcher import Matcher

from .bot_test_utils import MatcherStub, make_ref_context, make_scene_ref


@pytest.mark.parametrize(
    ("enabled", "reply"),
    [
        (True, "功能已开启喵"),
        (False, "功能已禁用喵"),
    ],
)
async def test_toggle_handler_uses_uninfo_scene(
    monkeypatch: pytest.MonkeyPatch,
    enabled: bool,
    reply: str,
):
    from nonebot_plugin_uniref import SceneRef

    from nonebot_plugin_impart_plus.bot.handlers import control

    calls: list[tuple[SceneRef, bool]] = []

    async def set_scene_enabled(scene_ref: SceneRef, value: bool) -> None:
        calls.append((scene_ref, value))

    monkeypatch.setattr(control.game_app, "set_scene_enabled", set_scene_enabled)
    matcher = MatcherStub()
    await control.toggle_module(
        cast(Matcher, matcher),
        make_ref_context(scene_id="12345"),
        enabled,
    )

    assert calls == [(make_scene_ref("12345"), enabled)]
    assert matcher.messages == [reply]


async def test_help_uses_unimessage_auto_fallback():
    from nonebot_plugin_alconna import AUTO, Text, UniMessage

    from nonebot_plugin_impart_plus.bot.handlers import control

    matcher = MatcherStub()

    await control.yinpa_introduce(cast(Matcher, matcher))

    assert isinstance(matcher.raw_messages[0], UniMessage)
    assert isinstance(matcher.raw_messages[0][0], Text)
    assert matcher.options[0]["fallback"] is AUTO
