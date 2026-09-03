"""PK、成长与状态查询 Handler。"""

from random import choice

from arclet.alconna import Arparma
from nonebot.matcher import Matcher
from nonebot_plugin_alconna import At, Match
from nonebot_plugin_uniref import RefContext, UserRef

from ...impart.app import GrowthOutcomeType, PkOutcome, PkOutcomeType, QueryOutcomeType
from ...impart.core import GrowthMode, LengthState
from ..dependencies import botname, game_app
from ..matchers import (
    SELF_GROW_MODES,
    TARGET_GROW_MODES,
    pk_matcher,
    query_matcher,
    self_growth_matcher,
    target_growth_matcher,
)
from .shared import HOLE_NAME, JJ_NAMES, NOT_ALLOWED_TEXT, user_at_target


def _growth_mode(
    result: Arparma,
    modes: dict[str, GrowthMode],
) -> GrowthMode:
    action = result.header_match.groups.get("action")
    mode = modes.get(action) if isinstance(action, str) else None
    if mode is None:
        raise TypeError("成长命令未解析为 GrowthMode")
    return mode


def _created_user_message(
    created_users: tuple[UserRef, ...],
    user_ref: UserRef,
    target_ref: UserRef,
) -> str:
    user_created = user_ref in created_users
    target_created = target_ref != user_ref and target_ref in created_users
    jj_name = choice(JJ_NAMES)
    if user_created and target_created:
        return f"你们还没有{jj_name}喵，咱帮你们创建了喵，目前长度都是10cm喵"
    if user_created:
        return f"你还没有{jj_name}喵，咱帮你创建了喵，目前长度是10cm喵"
    if target_created:
        return f"TA还没有{jj_name}喵，咱帮TA创建了喵，目前长度是10cm喵"
    raise ValueError("创建结果不包含命令用户")


@pk_matcher.handle()
async def pk(
    matcher: Matcher,
    refs: RefContext,
    targets: Match[tuple[At, ...]],
) -> None:
    scene_ref = refs.scene_ref
    user_ref = refs.user_ref
    target_ref = (
        refs.build_user_ref(user_at_target(targets.result[0]))
        if targets.available
        else None
    )
    outcome = await game_app.execute_pk(
        scene_ref,
        user_ref,
        target_ref,
    )

    if outcome.type is PkOutcomeType.DISABLED:
        await matcher.finish(NOT_ALLOWED_TEXT, at_sender=True)
    if outcome.type is PkOutcomeType.MISSING_TARGET:
        await matcher.finish("请at你要pk的目标", at_sender=True)
    if target_ref is None:
        return
    if outcome.type is PkOutcomeType.COOLING_DOWN:
        await matcher.finish(
            f"你已经pk不动了喵, 请等待{outcome.remaining}秒后再pk喵",
            at_sender=True,
        )
    if outcome.type is PkOutcomeType.SELF_TARGET:
        await matcher.finish("你不能pk自己喵", at_sender=True)
    if outcome.type is PkOutcomeType.USERS_CREATED:
        await matcher.finish(
            _created_user_message(outcome.created_users, user_ref, target_ref),
            at_sender=True,
        )
    if outcome.type is PkOutcomeType.WORLD_MISMATCH:
        name = choice(JJ_NAMES) if outcome.mode is GrowthMode.LENGTH else HOLE_NAME
        await matcher.finish(f"你只能和有{name}的人pk！", at_sender=True)

    if outcome.resolution is None:
        return
    if outcome.resolution.won:
        await _handle_pk_win(matcher, outcome)
    else:
        await _handle_pk_loss(matcher, outcome)


async def _handle_pk_win(matcher: Matcher, outcome: PkOutcome) -> None:
    resolution = outcome.resolution
    if resolution is None:
        return
    if outcome.mode is GrowthMode.DEPTH:
        uid_msg = (
            f"对决胜利喵, 你的{HOLE_NAME}加深了{resolution.length_increase}cm喵, "
            f"对面则在你{HOLE_NAME}的深暗压迫下变浅了{resolution.length_decrease}cm喵"
        )
        await matcher.finish(
            f"{uid_msg}\n你的胜率现在为{outcome.attacker_probability:.0%}喵",
            at_sender=True,
        )
        return
    uid_msg = f"对决胜利喵, 你的{choice(JJ_NAMES)}增加了{resolution.length_increase}cm喵, 对面则在你的阴影笼罩下减小了{resolution.length_decrease}cm喵"

    if "challenge_started_low_win" in outcome.attacker_status:
        uid_msg += (
            f"\n{botname}检测到你的{choice(JJ_NAMES)}长度超过25cm，已为你开启✨“登神长阶”✨"
            f"\n你现在的胜率变为当前的80%，且无法使用“打胶”与“嗦”指令，请以将{choice(JJ_NAMES)}长度提升至30cm为目标与他人pk吧!"
        )
    elif "challenge_success_high_win" in outcome.attacker_status:
        uid_msg += (
            f"\n🎉恭喜你完成登神挑战🎉\n你的{choice(JJ_NAMES)}长度已超过30cm，授予你🎊“牛々の神”🎊称号"
            f"\n你的胜率已恢复，“打胶”与“嗦”指令已重新开放，切记不忘初心，继续冲击更高的境界喵！"
        )

    if "challenge_failed_high_win" in outcome.defender_status:
        uid_msg += (
            f"\n由于你对决的胜利，{botname}检测到TA的{choice(JJ_NAMES)}长度已不足25cm，很遗憾，TA的登神挑战失败，{botname}替TA感谢你的鞭策喵！"
            f"\nTA的{choice(JJ_NAMES)}长度缩短了5cm喵，胜率已恢复，“打胶”与“嗦”指令已重新开放喵！"
        )
    elif "challenge_completed_reduce" in outcome.defender_status:
        uid_msg += (
            f"\n由于你对决的胜利，{botname}检测到TA的{choice(JJ_NAMES)}长度已不足25cm，很遗憾，TA跌落神坛，{botname}替TA感谢你的鞭策喵！"
            f"\nTA的{choice(JJ_NAMES)}长度缩短了5cm喵，请不忘初心，再次冲击更高的境界喵！"
        )
    elif "length_near_zero" in outcome.defender_status:
        uid_msg += f"\n由于你对决的胜利，{botname}检测到TA已经变成xnn了喵！"
    elif "length_zero_or_negative" in outcome.defender_status:
        uid_msg += f"\n由于你对决的胜利，{botname}检测到TA已经变成女孩子了喵！"

    probability_msg = f"\n你的胜率现在为{outcome.attacker_probability:.0%}喵"
    await matcher.finish(f"{uid_msg}{probability_msg}", at_sender=True)


async def _handle_pk_loss(matcher: Matcher, outcome: PkOutcome) -> None:
    resolution = outcome.resolution
    if resolution is None:
        return
    if outcome.mode is GrowthMode.DEPTH:
        uid_msg = (
            f"对决失败喵, 在对面{HOLE_NAME}的深暗压迫下你的{HOLE_NAME}"
            f"变浅了{resolution.length_decrease}cm喵, 对面加深了{resolution.length_increase}cm喵"
        )
        await matcher.finish(
            f"{uid_msg}\n你的胜率现在为{outcome.attacker_probability:.0%}喵",
            at_sender=True,
        )
        return
    uid_msg = f"对决失败喵, 在对面{choice(JJ_NAMES)}的阴影笼罩下你的{choice(JJ_NAMES)}减小了{resolution.length_decrease}cm喵, 对面增加了{resolution.length_increase}cm喵"

    if "challenge_failed_high_win" in outcome.attacker_status:
        uid_msg += (
            "\n很遗憾，登神挑战失败，别气馁啦！"
            f"\n你的{choice(JJ_NAMES)}长度缩短了5cm喵，胜率已恢复，“打胶”与“嗦”指令已重新开放喵！"
        )
    elif "challenge_completed_reduce" in outcome.attacker_status:
        uid_msg += (
            "\n很遗憾，你跌落神坛，别气馁啦！"
            f"\n你的{choice(JJ_NAMES)}长度缩短了5cm喵，请不忘初心，再次冲击更高的境界喵！"
        )
    elif "length_near_zero" in outcome.attacker_status:
        uid_msg += "\n你醒啦, 你已经变成xnn了！"
    elif "length_zero_or_negative" in outcome.attacker_status:
        uid_msg += "\n你醒啦, 你已经变成女孩子了！"

    if "challenge_started_low_win" in outcome.defender_status:
        uid_msg += (
            f"\n由于你对决的失败，触犯到了神秘的禁忌，{botname}检测到TA的{choice(JJ_NAMES)}长度超过25cm，已为TA开启✨“登神长阶”✨"
            f"\n现在TA的胜率变为当前的80%，且无法使用“打胶”与“嗦”指令，请通知TA以将{choice(JJ_NAMES)}长度提升至30cm为目标与群友pk吧！"
        )
    elif "challenge_success_high_win" in outcome.defender_status:
        uid_msg += (
            f"\n🎉恭喜你帮助TA完成登神挑战🎉\nTA的{choice(JJ_NAMES)}长度超过30cm，授予TA🎊“牛々の神”🎊称号"
            "\nTA的胜率已恢复，“打胶”与“嗦”指令已重新开放，请提醒TA不忘初心，继续冲击更高的境界喵！"
        )

    probability_msg = f"\n你的胜率现在为{outcome.attacker_probability:.0%}喵"
    await matcher.finish(f"{uid_msg}{probability_msg}", at_sender=True)


@self_growth_matcher.handle()
async def grow_self(
    matcher: Matcher,
    refs: RefContext,
    result: Arparma,
) -> None:
    mode = _growth_mode(result, SELF_GROW_MODES)
    scene_ref = refs.scene_ref
    user_ref = refs.user_ref
    outcome = await game_app.grow_self(
        scene_ref,
        user_ref,
        mode,
    )
    if outcome.type is GrowthOutcomeType.DISABLED:
        await matcher.finish(NOT_ALLOWED_TEXT, at_sender=True)
    if outcome.type is GrowthOutcomeType.USER_CREATED:
        await matcher.finish(
            _created_user_message(outcome.created_users, user_ref, user_ref),
            at_sender=True,
        )
    if outcome.type is GrowthOutcomeType.WRONG_STATE:
        message = (
            f"你没有{choice(JJ_NAMES)}喵，打不了胶喵"
            if mode is GrowthMode.LENGTH
            else f"你没有{HOLE_NAME}喵，挖不了矿喵"
        )
        await matcher.finish(message, at_sender=True)
    if outcome.type is GrowthOutcomeType.COOLING_DOWN:
        action = "导" if mode is GrowthMode.LENGTH else "扣"
        await matcher.finish(
            f"你已经{action}不动了喵, 请等待{outcome.remaining}秒后再{action}喵",
            at_sender=True,
        )
    if mode is GrowthMode.DEPTH:
        await matcher.finish(
            f"开扣结束喵, 你的{HOLE_NAME}很满意喵, 深了{outcome.random_num}cm喵, 目前深度为{abs(outcome.new_length)}cm喵",
            at_sender=True,
        )
    if outcome.type is GrowthOutcomeType.CHALLENGING:
        await matcher.finish(
            f"你的{choice(JJ_NAMES)}长度在任务范围内，不允许打胶，请专心与群友pk！",
            at_sender=True,
        )
    if outcome.challenge_started:
        await matcher.finish(
            f"开导结束喵, 你的{choice(JJ_NAMES)}很满意喵, 长了{outcome.random_num}cm喵"
            f"\n由于你无休止的打胶，触犯到了神秘的禁忌，{botname}检测到你的{choice(JJ_NAMES)}长度超过25cm，已为你开启✨“登神长阶”✨"
            f"\n你现在的胜率变为当前的80%，且无法使用“打胶”与“嗦”指令，请以将{choice(JJ_NAMES)}长度提升至30cm为目标与他人pk吧！",
            at_sender=True,
        )
    await matcher.finish(
        f"开导结束喵, 你的{choice(JJ_NAMES)}很满意喵, 长了{outcome.random_num}cm喵, 目前长度为{outcome.new_length}cm喵",
        at_sender=True,
    )


@target_growth_matcher.handle()
async def grow_target(
    matcher: Matcher,
    refs: RefContext,
    result: Arparma,
    targets: Match[tuple[At, ...]],
) -> None:
    mode = _growth_mode(result, TARGET_GROW_MODES)
    scene_ref = refs.scene_ref
    user_ref = refs.user_ref
    mentioned = user_at_target(targets.result[0]) if targets.available else None
    target_ref = refs.build_user_ref(mentioned) if mentioned else None
    outcome = await game_app.grow_target(
        scene_ref,
        user_ref,
        target_ref,
        mode,
    )

    if outcome.type is GrowthOutcomeType.DISABLED:
        await matcher.finish(NOT_ALLOWED_TEXT, at_sender=True)
    if outcome.type is GrowthOutcomeType.MISSING_TARGET:
        await matcher.finish("请at你要嗦/舔的目标", at_sender=True)
    if outcome.type is GrowthOutcomeType.SELF_TARGET:
        message = (
            f"你嗦不到自己的{choice(JJ_NAMES)}喵"
            if mode is GrowthMode.LENGTH
            else f"你舔不到自己的{HOLE_NAME}喵"
        )
        await matcher.finish(message, at_sender=True)
    if target_ref is None:
        return
    if outcome.type is GrowthOutcomeType.WRONG_STATE:
        message = (
            f"TA没有{choice(JJ_NAMES)}喵，嗦不了喵"
            if mode is GrowthMode.LENGTH
            else f"TA没有{HOLE_NAME}喵，舔不了喵"
        )
        await matcher.finish(message, at_sender=True)
    if outcome.type is GrowthOutcomeType.COOLING_DOWN:
        action = "嗦" if mode is GrowthMode.LENGTH else "舔"
        await matcher.finish(
            f"你已经{action}不动了喵, 请等待{outcome.remaining}秒后再{action}喵",
            at_sender=True,
        )
    if outcome.type is GrowthOutcomeType.USER_CREATED:
        await matcher.finish(
            _created_user_message(outcome.created_users, user_ref, target_ref),
            at_sender=True,
        )
    if outcome.type is GrowthOutcomeType.CHALLENGING:
        await matcher.finish(
            f"TA的{choice(JJ_NAMES)}长度在任务范围内，不准嗦！请专心与群友pk！",
            at_sender=True,
        )
    if outcome.type is not GrowthOutcomeType.COMPLETED:
        return
    if mode is GrowthMode.DEPTH:
        await matcher.finish(
            f"TA的{HOLE_NAME}很满意喵, 舔深了{outcome.random_num}cm喵, 目前深度为{abs(outcome.new_length)}cm喵",
            at_sender=True,
        )
    if outcome.challenge_started:
        await matcher.finish(
            f"TA的{choice(JJ_NAMES)}很满意喵, 嗦长了{outcome.random_num}cm喵"
            f"\n由于TA无休止的嗦与被嗦，触犯到了神秘的禁忌，{botname}检测到TA的{choice(JJ_NAMES)}长度超过25cm，"
            f"\n已为TA开启✨“登神长阶”✨，TA现在的胜率变为80%，且无法使用“打胶”与“嗦”指令，请以将{choice(JJ_NAMES)}长度提升至30cm为目标与他人pk吧！",
            at_sender=True,
        )
    await matcher.finish(
        f"TA的{choice(JJ_NAMES)}很满意喵, 嗦长了{outcome.random_num}cm喵, 目前长度为{outcome.new_length}cm喵",
        at_sender=True,
    )


@query_matcher.handle()
async def queryjj(
    matcher: Matcher,
    refs: RefContext,
    target: Match[At],
) -> None:
    scene_ref = refs.scene_ref
    user_ref = refs.user_ref
    mentioned = user_at_target(target.result) if target.available else None
    target_ref = refs.build_user_ref(mentioned) if mentioned else user_ref
    pronoun = "TA" if mentioned else "你"
    outcome = await game_app.query_user(
        scene_ref,
        user_ref,
        target_ref,
    )

    if outcome.type is QueryOutcomeType.DISABLED:
        await matcher.finish(NOT_ALLOWED_TEXT, at_sender=True)
    if outcome.type is QueryOutcomeType.USER_CREATED:
        await matcher.finish(
            _created_user_message(outcome.created_users, user_ref, target_ref),
            at_sender=True,
        )

    if outcome.state is LengthState.GOD:
        msg = (
            f"✨牛々の神✨\n{pronoun}的{choice(JJ_NAMES)}目前长度为{outcome.length}cm喵"
        )
    elif outcome.state is LengthState.NORMAL:
        msg = f"{pronoun}的{choice(JJ_NAMES)}目前长度为{outcome.length}cm喵"
    elif outcome.state is LengthState.XNN:
        msg = f"{pronoun}已经是xnn啦！\n{pronoun}的{choice(JJ_NAMES)}目前长度为{outcome.length}cm喵"
    elif outcome.state is LengthState.NEAR_GIRL:
        msg = f"{pronoun}快要变成女孩子啦！\n{pronoun}的{choice(JJ_NAMES)}目前长度为{outcome.length}cm喵"
    else:
        msg = f"{pronoun}已经是女孩子啦！\n{pronoun}的{HOLE_NAME}目前深度为{abs(outcome.length)}cm喵"
    await matcher.finish(msg, at_sender=True)
