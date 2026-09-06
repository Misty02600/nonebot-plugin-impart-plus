"""PK 与成长 Handler。"""

from random import choice
from typing import cast

from arclet.alconna import Arparma
from nonebot.matcher import Matcher
from nonebot_plugin_alconna import AUTO, AlconnaMatcher, At, Match, UniMessage
from nonebot_plugin_uniref import RefContext, UserRef

from ...impart.app import GrowthOutcomeType, PkOutcome, PkOutcomeType
from ...impart.core import ChallengeTier, GrowthMode
from ..dependencies import botname, game_app
from ..matchers import (
    SELF_GROW_MODES,
    TARGET_GROW_MODES,
    pk_matcher,
    self_growth_matcher,
    target_growth_matcher,
)
from .shared import (
    HOLE_NAME,
    JJ_NAMES,
    NOT_ALLOWED_TEXT,
    challenge_title,
    created_user_message,
    opponent_title_loss,
    user_at_target,
)


def _growth_mode(
    result: Arparma,
    modes: dict[str, GrowthMode],
) -> GrowthMode:
    action = result.header_match.groups.get("action")
    mode = modes.get(action) if isinstance(action, str) else None
    if mode is None:
        raise TypeError("成长命令未解析为 GrowthMode")
    return mode


async def _finish_game_reply(
    matcher: Matcher,
    message: str,
    *,
    unlocked_users: dict[UserRef, int],
    mode: GrowthMode,
    new_xnn_users: tuple[UserRef, ...] = (),
) -> None:
    """先回复本局结果，再艾特本次解锁和进入 XNN 的成员；最后一条结束 matcher。"""
    if not unlocked_users and not new_xnn_users:
        await matcher.finish(message, at_sender=True)
        return
    await matcher.send(message, at_sender=True)
    notifications: list[UniMessage] = []
    for user, tier in unlocked_users.items():
        if mode is GrowthMode.DEPTH:
            text = " 你感到深渊的禁忌力量正涌入体内..."
            dimension = "深度"
        else:
            text = " 你感到一股神性的力量正涌入体内..."
            dimension = "长度"
        growth = "将翻倍" if tier == 1 else f"将提升至{tier + 1}倍"
        target_count = ("两", "三", "四")[tier - 1]
        text += f"\n你的任何基础{dimension}变动{growth}！"
        text += f"\nPK现在最多可以指定{target_count}个目标了！"
        if tier == 1 and mode is GrowthMode.DEPTH:
            text += "\n现在可以使用指令「夺舍」了！"
        notifications.append(UniMessage.at(user.id).text(text))
    for user in new_xnn_users:
        notifications.append(
            UniMessage.at(user.id).text(
                " 你醒啦，你已经变成xnn了！"
                "\n你的pk胜率和长度变化均减小一半！"
                "\n你现在可以主动使用「榨群友」了！"
                "\n你可以努力逃脱，或就此成为大家的rbq！"
            )
        )
    for index, notification in enumerate(notifications):
        if index == len(notifications) - 1:
            await cast(AlconnaMatcher, matcher).finish(notification, fallback=AUTO)
        else:
            await cast(AlconnaMatcher, matcher).send(notification, fallback=AUTO)


def _self_challenge_progress(
    status: str, mode: GrowthMode, challenge: ChallengeTier | None
) -> str:
    if challenge is None:
        return ""
    title = challenge_title(challenge.tier, mode)
    if status == "challenge_started_low_win":
        if mode is GrowthMode.DEPTH:
            return (
                f"\n{botname}检测到你的{HOLE_NAME}深度超过{challenge.entry:g}cm，已为你开启🕳️“深渊试炼”🕳️"
                f"\n你现在的胜率变为当前的{challenge.win_multiplier:.0%}，且无法使用“挖矿”与“舔”指令，"
                f"请以将{HOLE_NAME}深度提升至{challenge.target:g}cm为目标与他人pk吧！"
            )
        return (
            f"\n{botname}检测到你的{choice(JJ_NAMES)}长度超过{challenge.entry:g}cm，已为你开启✨“登神长阶”✨"
            f"\n你现在的胜率变为当前的{challenge.win_multiplier:.0%}，且无法使用“打胶”与“嗦”指令，请以将{choice(JJ_NAMES)}长度提升至{challenge.target:g}cm为目标与他人pk吧!"
        )
    if status in {"challenge_completed", "challenge_success_high_win"}:
        if mode is GrowthMode.DEPTH:
            return (
                f"\n🎉恭喜你完成深渊挑战🎉\n你的{HOLE_NAME}深度已超过{challenge.target:g}cm，授予你🎊“{title}”🎊称号"
                "\n你的胜率已恢复，“挖矿”与“舔”指令已重新开放，切记不忘初心，继续探索更深的境界喵！"
            )
        return (
            f"\n🎉恭喜你完成登神挑战🎉\n你的{choice(JJ_NAMES)}长度已超过{challenge.target:g}cm，授予你🎊“{title}”🎊称号"
            "\n你的胜率已恢复，“打胶”与“嗦”指令已重新开放，切记不忘初心，继续冲击更高的境界喵！"
        )
    return ""


def _opponent_challenge_progress(
    status: str, mode: GrowthMode, challenge: ChallengeTier | None
) -> str:
    if challenge is None:
        return ""
    title = challenge_title(challenge.tier, mode)
    if status == "challenge_started_low_win":
        if mode is GrowthMode.DEPTH:
            return (
                f"\n由于你对决的失败，触犯到了神秘的禁忌，{botname}检测到TA的{HOLE_NAME}深度超过{challenge.entry:g}cm，已为TA开启🕳️“深渊试炼”🕳️"
                f"\n现在TA的胜率变为当前的{challenge.win_multiplier:.0%}，且无法使用“挖矿”与“舔”指令，"
                f"请通知TA以将{HOLE_NAME}深度提升至{challenge.target:g}cm为目标与群友pk吧！"
            )
        return (
            f"\n由于你对决的失败，触犯到了神秘的禁忌，{botname}检测到TA的{choice(JJ_NAMES)}长度超过{challenge.entry:g}cm，已为TA开启✨“登神长阶”✨"
            f"\n现在TA的胜率变为当前的{challenge.win_multiplier:.0%}，且无法使用“打胶”与“嗦”指令，请通知TA以将{choice(JJ_NAMES)}长度提升至{challenge.target:g}cm为目标与群友pk吧！"
        )
    if status in {"challenge_completed", "challenge_success_high_win"}:
        if mode is GrowthMode.DEPTH:
            return (
                f"\n🎉恭喜你帮助TA完成深渊挑战🎉\nTA的{HOLE_NAME}深度超过{challenge.target:g}cm，授予TA🎊“{title}”🎊称号"
                "\nTA的胜率已恢复，“挖矿”与“舔”指令已重新开放，请提醒TA继续探索更深的境界喵！"
            )
        return (
            f"\n🎉恭喜你帮助TA完成登神挑战🎉\nTA的{choice(JJ_NAMES)}长度超过{challenge.target:g}cm，授予TA🎊“{title}”🎊称号"
            "\nTA的胜率已恢复，“打胶”与“嗦”指令已重新开放，请提醒TA不忘初心，继续冲击更高的境界喵！"
        )
    return ""


def _self_challenge_regress(
    status: str, mode: GrowthMode, challenge: ChallengeTier | None
) -> str:
    if challenge is None:
        return ""
    title = challenge_title(challenge.tier, mode)
    if status == "challenge_failed_high_win":
        if mode is GrowthMode.DEPTH:
            return (
                "\n很遗憾，深渊挑战失败，别气馁啦！"
                f"\n你的{HOLE_NAME}深度变浅了{challenge.penalty:g}cm喵，胜率已恢复，“挖矿”与“舔”指令已重新开放喵！"
            )
        return (
            "\n很遗憾，登神挑战失败，别气馁啦！"
            f"\n你的{choice(JJ_NAMES)}长度缩短了{challenge.penalty:g}cm喵，胜率已恢复，“打胶”与“嗦”指令已重新开放喵！"
        )
    if status == "challenge_completed_reduce":
        if mode is GrowthMode.DEPTH:
            return (
                f"\n很遗憾，你被深渊拒绝了，失去了称号「{title}」，别气馁啦！"
                f"\n你的{HOLE_NAME}深度变浅了{challenge.penalty:g}cm喵，请不忘初心，再次探索更深的境界喵！"
            )
        return (
            f"\n很遗憾，你跌落神坛，失去了称号「{title}」，别气馁啦！"
            f"\n你的{choice(JJ_NAMES)}长度缩短了{challenge.penalty:g}cm喵，请不忘初心，再次冲击更高的境界喵！"
        )
    return ""


def _opponent_challenge_regress(
    status: str, mode: GrowthMode, challenge: ChallengeTier | None
) -> str:
    if challenge is None:
        return ""
    title = challenge_title(challenge.tier, mode)
    if status == "challenge_failed_high_win":
        if mode is GrowthMode.DEPTH:
            return (
                f"\n由于你对决的胜利，{botname}检测到TA的{HOLE_NAME}深度已不足{challenge.entry:g}cm，很遗憾，TA的深渊挑战失败，{botname}替TA感谢你的鞭策喵！"
                f"\nTA的{HOLE_NAME}深度变浅了{challenge.penalty:g}cm喵，胜率已恢复，“挖矿”与“舔”指令已重新开放喵！"
            )
        return (
            f"\n由于你对决的胜利，{botname}检测到TA的{choice(JJ_NAMES)}长度已不足{challenge.entry:g}cm，很遗憾，TA的登神挑战失败，{botname}替TA感谢你的鞭策喵！"
            f"\nTA的{choice(JJ_NAMES)}长度缩短了{challenge.penalty:g}cm喵，胜率已恢复，“打胶”与“嗦”指令已重新开放喵！"
        )
    if status == "challenge_completed_reduce":
        if mode is GrowthMode.DEPTH:
            return (
                f"\n由于你对决的胜利，{botname}检测到TA的{HOLE_NAME}深度已不足{challenge.entry:g}cm，很遗憾，TA被深渊拒绝了，失去了称号「{title}」，{botname}替TA感谢你的鞭策喵！"
                f"\nTA的{HOLE_NAME}深度变浅了{challenge.penalty:g}cm喵，请不忘初心，再次探索更深的境界喵！"
            )
        return opponent_title_loss(
            cause="你对决的胜利",
            botname=botname,
            name=choice(JJ_NAMES),
            penalty_name=choice(JJ_NAMES),
            challenge=challenge,
        )
    return ""


@pk_matcher.handle()
async def pk(
    matcher: Matcher,
    refs: RefContext,
    targets: Match[tuple[At, ...]],
) -> None:
    scene_ref = refs.scene_ref
    user_ref = refs.user_ref
    preparation = await game_app.prepare_pk(scene_ref, user_ref)
    if not preparation.enabled:
        await matcher.finish(NOT_ALLOWED_TEXT, at_sender=True)
    if not targets.available:
        await matcher.finish("请艾特你要pk的目标", at_sender=True)
        return

    selected = targets.result[: preparation.max_targets]
    target_refs = tuple(
        dict.fromkeys(
            refs.build_user_ref(user_at_target(target)) for target in selected
        )
    )
    outcome = await game_app.execute_pk(scene_ref, user_ref, target_refs)
    if outcome.type is PkOutcomeType.DISABLED:
        await matcher.finish(NOT_ALLOWED_TEXT, at_sender=True)
    if outcome.type is PkOutcomeType.MISSING_TARGET:
        await matcher.finish("请艾特你要pk的目标", at_sender=True)
    if outcome.type is PkOutcomeType.COOLING_DOWN:
        await matcher.finish(
            f"你已经pk不动了喵, 请等待{outcome.remaining}秒后再pk喵",
            at_sender=True,
        )
    if outcome.type is PkOutcomeType.SELF_TARGET:
        await matcher.finish("你不能pk自己喵", at_sender=True)
    if outcome.type is PkOutcomeType.MULTI_TARGET_UNAVAILABLE:
        await matcher.finish("你当前的称号无法同时与这么多人pk喵", at_sender=True)
    if outcome.type is PkOutcomeType.USERS_CREATED:
        await matcher.finish(
            created_user_message(outcome.created_users, user_ref, *target_refs),
            at_sender=True,
        )
    if outcome.type is PkOutcomeType.WORLD_MISMATCH:
        name = choice(JJ_NAMES) if outcome.mode is GrowthMode.LENGTH else HOLE_NAME
        await matcher.finish(f"你只能和有{name}的人pk！", at_sender=True)
    if outcome.type is not PkOutcomeType.COMPLETED:
        return
    if outcome.won:
        await _handle_pk_win(matcher, outcome)
    else:
        await _handle_pk_loss(matcher, outcome)


def _target_label(index: int, target_count: int) -> str:
    return "对面" if target_count == 1 else f"目标{index}"


async def _handle_pk_win(matcher: Matcher, outcome: PkOutcome) -> None:
    attacker_change = abs(outcome.attacker_change)
    target_count = len(outcome.targets)
    separator = ", " if target_count == 1 else "\n"
    if outcome.mode is GrowthMode.DEPTH:
        uid_msg = f"对决胜利喵, 你的{HOLE_NAME}加深了{attacker_change}cm喵"
        for index, target in enumerate(outcome.targets, 1):
            uid_msg += (
                f"{separator}{_target_label(index, target_count)}"
                f"则在你{HOLE_NAME}的深暗压迫下"
                f"变浅了{abs(target.length_change)}cm喵"
            )
    else:
        name = choice(JJ_NAMES)
        uid_msg = f"对决胜利喵, 你的{name}增加了{attacker_change}cm喵"
        for index, target in enumerate(outcome.targets, 1):
            uid_msg += (
                f"{separator}{_target_label(index, target_count)}则在你的阴影笼罩下"
                f"减小了{abs(target.length_change)}cm喵"
            )

    uid_msg += _self_challenge_progress(
        outcome.attacker_status, outcome.mode, outcome.attacker_challenge
    )
    for index, target in enumerate(outcome.targets, 1):
        challenge = _opponent_challenge_regress(
            target.status, outcome.mode, target.challenge
        )
        if challenge and target_count > 1:
            uid_msg += f"\n{_target_label(index, target_count)}：" + challenge
        else:
            uid_msg += challenge

    probability_msg = (
        f"\n你的胜率现在为{round(outcome.attacker_probability * 100, 3):g}%喵"
    )
    await _finish_game_reply(
        matcher,
        f"{uid_msg}{probability_msg}",
        unlocked_users=outcome.unlocked_users,
        mode=outcome.mode,
        new_xnn_users=outcome.new_xnn_users,
    )


async def _handle_pk_loss(matcher: Matcher, outcome: PkOutcome) -> None:
    attacker_change = abs(outcome.attacker_change)
    target_count = len(outcome.targets)
    separator = ", " if target_count == 1 else "\n"
    if outcome.mode is GrowthMode.DEPTH:
        uid_msg = (
            f"对决失败喵, 在对面{HOLE_NAME}的深暗压迫下你的{HOLE_NAME}"
            f"变浅了{attacker_change}cm喵"
        )
        for index, target in enumerate(outcome.targets, 1):
            uid_msg += (
                f"{separator}{_target_label(index, target_count)}加深了"
                f"{abs(target.length_change)}cm喵"
            )
    else:
        name = choice(JJ_NAMES)
        uid_msg = (
            f"对决失败喵, 在对面{name}的阴影笼罩下你的{name}减小了{attacker_change}cm喵"
        )
        for index, target in enumerate(outcome.targets, 1):
            uid_msg += (
                f"{separator}{_target_label(index, target_count)}增加了"
                f"{abs(target.length_change)}cm喵"
            )

    attacker_challenge = _self_challenge_regress(
        outcome.attacker_status,
        outcome.mode,
        outcome.attacker_challenge,
    )
    uid_msg += attacker_challenge

    for index, target in enumerate(outcome.targets, 1):
        challenge = _opponent_challenge_progress(
            target.status, outcome.mode, target.challenge
        )
        if challenge and target_count > 1:
            uid_msg += f"\n{_target_label(index, target_count)}：" + challenge
        else:
            uid_msg += challenge

    probability_msg = (
        f"\n你的胜率现在为{round(outcome.attacker_probability * 100, 3):g}%喵"
    )
    await _finish_game_reply(
        matcher,
        f"{uid_msg}{probability_msg}",
        unlocked_users=outcome.unlocked_users,
        mode=outcome.mode,
        new_xnn_users=outcome.new_xnn_users,
    )


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
            created_user_message(outcome.created_users, user_ref, user_ref),
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
    if outcome.type is GrowthOutcomeType.ACTOR_CHALLENGING:
        message = (
            f"你的{choice(JJ_NAMES)}长度在任务范围内，不允许打胶，请专心与群友pk！"
            if mode is GrowthMode.LENGTH
            else f"你的{HOLE_NAME}深度在任务范围内，不允许挖矿，请专心与群友pk！"
        )
        await matcher.finish(message, at_sender=True)
    if outcome.challenge:
        challenge = outcome.challenge
        if mode is GrowthMode.DEPTH:
            await _finish_game_reply(
                matcher,
                f"挖矿结束喵, 你的{HOLE_NAME}很满意喵, 扣深了{outcome.amount}cm喵"
                f"\n由于你无休止的挖矿，触犯到了神秘的禁忌，{botname}检测到你的{HOLE_NAME}深度超过{challenge.entry:g}cm，已为你开启🕳️“深渊试炼”🕳️"
                f"\n你现在的胜率变为当前的{challenge.win_multiplier:.0%}，且无法使用“挖矿”与“舔”指令，请以将{HOLE_NAME}深度提升至{challenge.target:g}cm为目标与他人pk吧！",
                unlocked_users=outcome.unlocked_users,
                mode=mode,
            )
        await _finish_game_reply(
            matcher,
            f"打胶结束喵, 你的{choice(JJ_NAMES)}很满意喵, 导长了{outcome.amount}cm喵"
            f"\n由于你无休止的打胶，触犯到了神秘的禁忌，{botname}检测到你的{choice(JJ_NAMES)}长度超过{challenge.entry:g}cm，已为你开启✨“登神长阶”✨"
            f"\n你现在的胜率变为当前的{challenge.win_multiplier:.0%}，且无法使用“打胶”与“嗦”指令，请以将{choice(JJ_NAMES)}长度提升至{challenge.target:g}cm为目标与他人pk吧！",
            unlocked_users=outcome.unlocked_users,
            mode=mode,
        )
    if mode is GrowthMode.DEPTH:
        await _finish_game_reply(
            matcher,
            f"挖矿结束喵, 你的{HOLE_NAME}很满意喵, 扣深了{outcome.amount}cm喵, 目前深度为{abs(outcome.new_length)}cm喵",
            unlocked_users=outcome.unlocked_users,
            mode=mode,
        )
    await _finish_game_reply(
        matcher,
        f"打胶结束喵, 你的{choice(JJ_NAMES)}很满意喵, 导长了{outcome.amount}cm喵, 目前长度为{outcome.new_length}cm喵",
        unlocked_users=outcome.unlocked_users,
        mode=mode,
    )


@target_growth_matcher.handle()
async def grow_target(
    matcher: Matcher,
    refs: RefContext,
    result: Arparma,
    targets: Match[tuple[At, ...]],
) -> None:
    mode = _growth_mode(result, TARGET_GROW_MODES)
    action = "嗦" if mode is GrowthMode.LENGTH else "舔"
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
        await matcher.finish(f"请艾特你要{action}的目标", at_sender=True)
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
        await matcher.finish(
            f"你已经{action}不动了喵, 请等待{outcome.remaining}秒后再{action}喵",
            at_sender=True,
        )
    if outcome.type is GrowthOutcomeType.USER_CREATED:
        await matcher.finish(
            created_user_message(outcome.created_users, user_ref, target_ref),
            at_sender=True,
        )
    if outcome.type is GrowthOutcomeType.ACTOR_CHALLENGING:
        name = (
            choice(JJ_NAMES) if outcome.actor_mode is GrowthMode.LENGTH else HOLE_NAME
        )
        dimension = "长度" if outcome.actor_mode is GrowthMode.LENGTH else "深度"
        await matcher.finish(
            f"你的{name}{dimension}在任务范围内，不准{action}！请专心与群友pk！",
            at_sender=True,
        )
    if outcome.type is GrowthOutcomeType.TARGET_CHALLENGING:
        message = (
            f"TA的{choice(JJ_NAMES)}长度在任务范围内，不准嗦！请专心与群友pk！"
            if mode is GrowthMode.LENGTH
            else f"TA的{HOLE_NAME}深度在任务范围内，不准舔！请专心与群友pk！"
        )
        await matcher.finish(message, at_sender=True)
    if outcome.type is not GrowthOutcomeType.COMPLETED:
        return
    if outcome.challenge:
        challenge = outcome.challenge
        if mode is GrowthMode.DEPTH:
            await _finish_game_reply(
                matcher,
                f"TA的{HOLE_NAME}很满意喵, 舔深了{outcome.amount}cm喵"
                f"\n由于TA无休止的舔与被舔，触犯到了神秘的禁忌，{botname}检测到TA的{HOLE_NAME}深度超过{challenge.entry:g}cm，"
                f"\n已为TA开启🕳️“深渊试炼”🕳️，TA现在的胜率变为当前的{challenge.win_multiplier:.0%}，且无法使用“挖矿”与“舔”指令，请以将{HOLE_NAME}深度提升至{challenge.target:g}cm为目标与他人pk吧！",
                unlocked_users=outcome.unlocked_users,
                mode=mode,
            )
        await _finish_game_reply(
            matcher,
            f"TA的{choice(JJ_NAMES)}很满意喵, 嗦长了{outcome.amount}cm喵"
            f"\n由于TA无休止的嗦与被嗦，触犯到了神秘的禁忌，{botname}检测到TA的{choice(JJ_NAMES)}长度超过{challenge.entry:g}cm，"
            f"\n已为TA开启✨“登神长阶”✨，TA现在的胜率变为当前的{challenge.win_multiplier:.0%}，且无法使用“打胶”与“嗦”指令，请以将{choice(JJ_NAMES)}长度提升至{challenge.target:g}cm为目标与他人pk吧！",
            unlocked_users=outcome.unlocked_users,
            mode=mode,
        )
    if mode is GrowthMode.DEPTH:
        await _finish_game_reply(
            matcher,
            f"TA的{HOLE_NAME}很满意喵, 舔深了{outcome.amount}cm喵, 目前深度为{abs(outcome.new_length)}cm喵",
            unlocked_users=outcome.unlocked_users,
            mode=mode,
        )
    await _finish_game_reply(
        matcher,
        f"TA的{choice(JJ_NAMES)}很满意喵, 嗦长了{outcome.amount}cm喵, 目前长度为{outcome.new_length}cm喵",
        unlocked_users=outcome.unlocked_users,
        mode=mode,
    )
