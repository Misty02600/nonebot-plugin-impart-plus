"""状态与互动记录查询 Handler。"""

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
from nonebot_plugin_uniref import RefContext

from ...impart.app import QueryOutcomeType
from ...impart.core import LengthState
from ...infra.chart_renderer import draw_bar_chart
from ..dependencies import game_app
from ..matchers import history_query_matcher, query_matcher
from .shared import (
    HOLE_NAME,
    JJ_NAMES,
    NOT_ALLOWED_TEXT,
    created_user_message,
    user_at_target,
)


@query_matcher.handle()
@history_query_matcher.handle()
async def query_user(
    matcher: Matcher,
    refs: RefContext,
    command_result: CommandResult,
    target: Match[At],
) -> None:
    user_ref = refs.user_ref
    mentioned = user_at_target(target.result) if target.available else None
    target_ref = refs.build_user_ref(mentioned) if mentioned else user_ref
    pronoun = "TA" if mentioned else "你"
    outcome = await game_app.query_user(
        refs.scene_ref,
        user_ref,
        target_ref,
        history="history_query" in command_result.result.subcommands,
    )

    if outcome.type is QueryOutcomeType.DISABLED:
        await matcher.finish(NOT_ALLOWED_TEXT, at_sender=True)
    if outcome.type is QueryOutcomeType.USER_CREATED:
        await matcher.finish(
            created_user_message(outcome.created_users, user_ref, target_ref),
            at_sender=True,
        )

    if outcome.state is LengthState.GOD:
        message = (
            f"✨牛々の神✨\n{pronoun}的{choice(JJ_NAMES)}目前长度为{outcome.length}cm喵"
        )
    elif outcome.state is LengthState.ABYSS_LORD:
        message = (
            f"🕳️深淵の主🕳️\n{pronoun}的{HOLE_NAME}目前深度为{abs(outcome.length)}cm喵"
        )
    elif outcome.state is LengthState.NORMAL:
        message = f"{pronoun}的{choice(JJ_NAMES)}目前长度为{outcome.length}cm喵"
    elif outcome.state is LengthState.XNN:
        status = "快要变成女孩子啦" if outcome.today_total > 200 else "已经是xnn啦"
        message = (
            f"{pronoun}{status}！\n{pronoun}的{choice(JJ_NAMES)}目前长度为"
            f"{outcome.length}cm喵"
        )
    else:
        message = (
            f"{pronoun}已经是女孩子啦！\n{pronoun}的{HOLE_NAME}目前深度为"
            f"{abs(outcome.length)}cm喵"
        )

    message += f"\n{pronoun}当日总注入量为{outcome.today_total}ml"
    if outcome.history_total is None:
        await matcher.finish(message, at_sender=True)

    message += f"\n{pronoun}历史总注入量为{outcome.history_total}ml"
    if len(outcome.history) < 2:
        await matcher.finish(message, at_sender=True)
    await cast(AlconnaMatcher, matcher).finish(
        UniMessage.text(message).image(
            raw=await draw_bar_chart.draw_line_chart(outcome.history),
        ),
        fallback=AUTO,
        at_sender=True,
    )
