"""排行榜与注入记录查询 Handler。"""

from random import choice
from typing import cast

from nonebot.matcher import Matcher
from nonebot_plugin_alconna import (
    AUTO,
    AlconnaMatcher,
    At,
    CommandResult,
    Match,
    UniMessage,
)
from nonebot_plugin_uninfo import QryItrface, Uninfo

from ...impart.app import InjectionQueryType, RankingOutcomeType
from ...infra.chart_renderer import draw_bar_chart
from ..context import legacy_scene_id
from ..dependencies import game_app, plugin_config
from ..matchers import injection_query_matcher, rank_matcher
from .shared import NOT_ALLOWED_TEXT, get_user_or_none, user_display_name


@rank_matcher.handle()
async def jjrank(
    matcher: Matcher,
    session: Uninfo,
    interface: QryItrface,
) -> None:
    outcome = await game_app.query_ranking(
        legacy_scene_id(session),
        int(session.user.id),
    )
    if outcome.type is RankingOutcomeType.DISABLED:
        await matcher.finish(NOT_ALLOWED_TEXT, at_sender=True)
    if outcome.type is RankingOutcomeType.TOO_FEW:
        await matcher.finish("目前记录的数据量小于5, 无法显示rank喵")
    if outcome.type is RankingOutcomeType.USER_CREATED:
        await matcher.finish(
            f"你还没有创建{choice(plugin_config.jj_variable)}看不到rank喵, 咱帮你创建了喵, 目前长度是10cm喵",
            at_sender=True,
        )

    top5 = outcome.ranking[:5]
    last5 = outcome.ranking[-5:]
    top5users = [
        await get_user_or_none(interface, str(item["userid"])) for item in top5
    ]
    last5users = [
        await get_user_or_none(interface, str(item["userid"])) for item in last5
    ]
    top5names = [
        user_display_name(user, str(item["userid"]))
        for user, item in zip(top5users, top5, strict=True)
    ]
    last5names = [
        user_display_name(user, str(item["userid"]))
        for user, item in zip(last5users, last5, strict=True)
    ]
    data = {top5names[i]: top5[i]["jj_length"] for i in range(len(top5))}
    for i in range(len(last5)):
        data[last5names[i]] = last5[i]["jj_length"]
    img_bytes = await draw_bar_chart.draw_bar_chart(data)
    reply = f"你的排名为{outcome.index + 1}喵"
    await cast(AlconnaMatcher, matcher).finish(
        UniMessage.image(raw=img_bytes).text(reply),
        fallback=AUTO,
        at_sender=True,
    )


@injection_query_matcher.handle()
async def query_injection(
    matcher: Matcher,
    session: Uninfo,
    command_result: CommandResult,
    target: Match[At],
) -> None:
    mentioned = target.result.target if target.available else None
    object_id = mentioned or session.user.id
    replay = "该用户" if mentioned else "您"
    result = await game_app.query_injection(
        legacy_scene_id(session),
        int(object_id),
        history="history" in command_result.result.options,
    )
    if result.type is InjectionQueryType.DISABLED:
        await matcher.finish(NOT_ALLOWED_TEXT, at_sender=True)
    if result.type is InjectionQueryType.DAILY:
        await matcher.finish(f"{replay}当日总被注射量为{result.total}ml")
    if result.type is InjectionQueryType.HISTORY_TEXT:
        await matcher.finish(f"{replay}历史总被注射量为{result.total}ml")
    await cast(AlconnaMatcher, matcher).finish(
        UniMessage.text(f"{replay}历史总被注射量为{result.total}ml").image(
            raw=await draw_bar_chart.draw_line_chart(result.history),
        ),
        fallback=AUTO,
    )
