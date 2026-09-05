"""排行榜 Handler。"""

from random import choice
from typing import cast

from nonebot import logger
from nonebot.matcher import Matcher
from nonebot_plugin_alconna import AUTO, AlconnaMatcher, UniMessage
from nonebot_plugin_uninfo import QryItrface
from nonebot_plugin_uniref import RefContext

from ...impart.app import RankingOutcomeType
from ...infra import chart_renderer
from ...infra.chart_layout import RankEntry, select_indices
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

    entries: list[RankEntry] = []
    for index in select_indices(len(outcome.ranking), outcome.index):
        item = outcome.ranking[index]
        user = await get_user_or_none(interface, item.user.id)
        entries.append(
            RankEntry(
                user_id=item.user.id,
                name=user_display_name(user, item.user.id),
                length=item.length,
                rank=index + 1,
                is_self=index == outcome.index,
                avatar_url=user.avatar if user else None,
            )
        )
    reply = f"你的排名为{outcome.index + 1}喵"
    try:
        img_bytes = await chart_renderer.render_ranking(entries)
    except Exception:
        logger.exception("排行榜图表生成失败")
        await matcher.finish(f"{reply}\n图表生成失败", at_sender=True)
    await cast(AlconnaMatcher, matcher).finish(
        UniMessage.image(raw=img_bytes).text(reply),
        fallback=AUTO,
        at_sender=True,
    )
