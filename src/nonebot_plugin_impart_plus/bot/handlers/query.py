"""状态与互动记录查询 Handler。"""

from random import choice
from typing import cast

from nonebot import logger
from nonebot.matcher import Matcher
from nonebot_plugin_alconna import (
    AUTO,
    AlconnaMatcher,
    At,
    CommandResult,
    Match,
    UniMessage,
)
from nonebot_plugin_uninfo import QryItrface
from nonebot_plugin_uniref import RefContext

from ...impart.app import QueryOutcomeType
from ...impart.core import GrowthMode, LengthState
from ...infra import chart_renderer
from ..dependencies import game_app
from ..matchers import history_query_matcher, query_matcher
from .shared import (
    HOLE_NAME,
    JJ_NAMES,
    NOT_ALLOWED_TEXT,
    challenge_title,
    created_user_message,
    get_user_or_none,
    user_at_target,
    user_display_name,
)


@query_matcher.handle()
@history_query_matcher.handle()
async def query_user(
    matcher: Matcher,
    refs: RefContext,
    command_result: CommandResult,
    target: Match[At],
    interface: QryItrface,
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
        message = f"✨{challenge_title(outcome.challenge_tier, GrowthMode.LENGTH)}✨\n{pronoun}的{choice(JJ_NAMES)}目前长度为{outcome.length}cm"
    elif outcome.state is LengthState.ABYSS_LORD:
        message = f"🕳️{challenge_title(outcome.challenge_tier, GrowthMode.DEPTH)}🕳️\n{pronoun}的{HOLE_NAME}目前深度为{abs(outcome.length)}cm"
    elif outcome.state is LengthState.NORMAL:
        message = f"{pronoun}的{choice(JJ_NAMES)}目前长度为{outcome.length}cm"
    elif outcome.state is LengthState.XNN:
        status = "快要变成女孩子啦" if outcome.today_total > 200 else "已经是xnn啦"
        message = f"{pronoun}{status}！目前长度为{outcome.length}cm"
    else:
        message = f"{pronoun}的{HOLE_NAME}目前深度为{abs(outcome.length)}cm"

    message += f"，目前胜率为{round(outcome.win_probability * 100, 3):g}%"
    message += f"，当日总注入量为{outcome.today_total}ml"
    if outcome.history_total is None:
        await matcher.finish(f"{message}喵", at_sender=True)

    message += f"，历史总注入量为{outcome.history_total}ml"
    if len(outcome.history) < 2:
        await matcher.finish(f"{message}喵", at_sender=True)
    user = await get_user_or_none(interface, target_ref.id)
    try:
        img_bytes = await chart_renderer.render_history(
            outcome.history,
            name=user_display_name(user, target_ref.id),
            avatar_url=user.avatar if user else None,
            total=outcome.history_total,
        )
    except Exception:
        logger.exception("历史图表生成失败")
        await matcher.finish(f"{message}，图表生成失败喵", at_sender=True)
    await cast(AlconnaMatcher, matcher).finish(
        UniMessage.text(f"{message}喵").image(
            raw=img_bytes,
        ),
        fallback=AUTO,
        at_sender=True,
    )
