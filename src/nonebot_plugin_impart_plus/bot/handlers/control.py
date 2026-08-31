"""功能开关与帮助 Handler。"""

from typing import cast

from nonebot.matcher import Matcher
from nonebot_plugin_alconna import AUTO, AlconnaMatcher, UniMessage
from nonebot_plugin_uninfo import Uninfo

from ... import __plugin_meta__
from ..context import legacy_scene_id
from ..dependencies import game_app
from ..matchers import disable_matcher, enable_matcher, help_matcher


async def _set_module_enabled(
    matcher: Matcher,
    session: Uninfo,
    enabled: bool,
) -> None:
    await game_app.set_group_enabled(legacy_scene_id(session), enabled)
    await matcher.finish("功能已开启喵" if enabled else "功能已禁用喵")


@enable_matcher.handle()
async def enable_module(matcher: Matcher, session: Uninfo) -> None:
    await _set_module_enabled(matcher, session, True)


@disable_matcher.handle()
async def disable_module(matcher: Matcher, session: Uninfo) -> None:
    await _set_module_enabled(matcher, session, False)


@help_matcher.handle()
async def yinpa_introduce(matcher: Matcher) -> None:
    await cast(AlconnaMatcher, matcher).send(
        UniMessage.text(__plugin_meta__.usage),
        fallback=AUTO,
    )
