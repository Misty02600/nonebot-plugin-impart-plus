"""夺舍 Handler。"""

from random import choice

from nonebot.matcher import Matcher
from nonebot_plugin_alconna import At, Match
from nonebot_plugin_uniref import RefContext

from ...impart.core import PossessionStatus
from ..dependencies import botname, game_app
from ..matchers import possession_matcher
from .shared import (
    HOLE_NAME,
    JJ_NAMES,
    NOT_ALLOWED_TEXT,
    created_user_message,
    opponent_title_loss,
    user_at_target,
)


@possession_matcher.handle()
async def possess(
    matcher: Matcher, refs: RefContext, targets: Match[tuple[At, ...]]
) -> None:
    actor_ref = refs.user_ref
    target_ref = (
        refs.build_user_ref(user_at_target(targets.result[0]))
        if targets.available
        else None
    )
    outcome = await game_app.execute_possession(refs.scene_ref, actor_ref, target_ref)
    if outcome.type is PossessionStatus.DISABLED:
        await matcher.finish(NOT_ALLOWED_TEXT, at_sender=True)
    if outcome.type is PossessionStatus.MISSING_TARGET:
        await matcher.finish("请艾特你要夺舍的目标", at_sender=True)
    if target_ref is None:
        return
    if outcome.type is PossessionStatus.USERS_CREATED:
        await matcher.finish(
            created_user_message(outcome.created_users, actor_ref, target_ref),
            at_sender=True,
        )
    if outcome.type is PossessionStatus.LOCKED:
        await matcher.finish("你尚未解锁此禁忌之术...", at_sender=True)
    if outcome.type is PossessionStatus.TARGET_CHALLENGING:
        await matcher.finish(
            "一股神秘的力量庇护着TA，你的夺舍之术被无效化了...", at_sender=True
        )
    name = choice(JJ_NAMES)
    if outcome.type is PossessionStatus.WRONG_TARGET:
        await matcher.finish(f"你不能夺舍没有{name}的人！", at_sender=True)
    if outcome.type is PossessionStatus.TARGET_TOO_LONG:
        await matcher.finish(
            f"你只能夺舍{name}长度比你的{HOLE_NAME}深度短的人！", at_sender=True
        )
    message = (
        "深渊回应了你的期待，一股禁忌的力量在你的下体汇聚，你感到自己正在取回遗失之物..."
        f"\n再次睁眼时，你的{name}被重塑为{outcome.half}cm，"
        f"而对面的{name}也只剩下{outcome.half}cm了喵！"
    )
    if outcome.target_challenge:
        message += opponent_title_loss(
            cause="你的夺舍",
            botname=botname,
            name=name,
            penalty_name=name,
            challenge=outcome.target_challenge,
        )
    await matcher.finish(message, at_sender=True)
