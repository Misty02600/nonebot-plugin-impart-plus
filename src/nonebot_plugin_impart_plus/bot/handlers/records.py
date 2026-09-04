"""排行榜 Handler。"""

from random import choice
from typing import cast

from nonebot.matcher import Matcher
from nonebot_plugin_alconna import AUTO, AlconnaMatcher, UniMessage
from nonebot_plugin_uninfo import QryItrface
from nonebot_plugin_uniref import RefContext

from ...impart.app import RankingOutcomeType
from ...infra.chart_renderer import draw_bar_chart
from ..dependencies import game_app
from ..matchers import rank_matcher
from .shared import (
    JJ_NAMES,
    NOT_ALLOWED_TEXT,
    get_user_or_none,
    user_display_name,
)


@rank_matcher.handle()
async def jjrank(
    matcher: Matcher,
    refs: RefContext,
    interface: QryItrface,
) -> None:
    scene_ref = refs.scene_ref
    user_ref = refs.user_ref
    outcome = await game_app.query_ranking(
        scene_ref,
        user_ref,
    )
    if outcome.type is RankingOutcomeType.DISABLED:
        await matcher.finish(NOT_ALLOWED_TEXT, at_sender=True)
    if outcome.type is RankingOutcomeType.TOO_FEW:
        await matcher.finish("目前记录的数据量小于5, 无法显示rank喵")
    if outcome.type is RankingOutcomeType.USER_CREATED:
        await matcher.finish(
            f"你还没有创建{choice(JJ_NAMES)}看不到rank喵, 咱帮你创建了喵, 目前长度是10cm喵",
            at_sender=True,
        )

    top5 = outcome.ranking[:5]
    last5 = outcome.ranking[-5:]
    top5users = [await get_user_or_none(interface, item.user.id) for item in top5]
    last5users = [await get_user_or_none(interface, item.user.id) for item in last5]
    top5names = [
        user_display_name(user, item.user.id)
        for user, item in zip(top5users, top5, strict=True)
    ]
    last5names = [
        user_display_name(user, item.user.id)
        for user, item in zip(last5users, last5, strict=True)
    ]
    data = {top5names[i]: top5[i].length for i in range(len(top5))}
    for i in range(len(last5)):
        data[last5names[i]] = last5[i].length
    img_bytes = await draw_bar_chart.draw_bar_chart(data)
    reply = f"你的排名为{outcome.index + 1}喵"
    await cast(AlconnaMatcher, matcher).finish(
        UniMessage.image(raw=img_bytes).text(reply),
        fallback=AUTO,
        at_sender=True,
    )
