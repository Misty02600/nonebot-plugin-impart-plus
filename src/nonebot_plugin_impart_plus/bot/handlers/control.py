"""功能开关与帮助 Handler。"""

from typing import cast

from nonebot.matcher import Matcher
from nonebot_plugin_alconna import AUTO, AlconnaMatcher, UniMessage
from nonebot_plugin_uniref import RefContext

from ... import __plugin_meta__
from ..dependencies import game_app
from ..matchers import help_matcher, toggle_matcher


@toggle_matcher.handle()
async def toggle_module(
    matcher: Matcher,
    refs: RefContext,
    enabled: bool,
) -> None:
    await game_app.set_scene_enabled(refs.scene_ref, enabled)
    await matcher.finish("功能已开启喵" if enabled else "功能已禁用喵")


@help_matcher.handle()
async def yinpa_introduce(matcher: Matcher) -> None:
    await cast(AlconnaMatcher, matcher).send(
        UniMessage.text(__plugin_meta__.usage),
        fallback=AUTO,
    )
