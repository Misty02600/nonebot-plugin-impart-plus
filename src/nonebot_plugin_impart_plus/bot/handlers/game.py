"""PK、成长与状态查询 Handler。"""

from random import choice

from nonebot.matcher import Matcher
from nonebot_plugin_alconna import At, Match
from nonebot_plugin_uninfo import Uninfo

from ...impart.app import GrowthOutcomeType, PkOutcome, PkOutcomeType, QueryOutcomeType
from ...impart.core import LengthState
from ..context import legacy_scene_id
from ..dependencies import botname, game_app, plugin_config
from ..matchers import grow_matcher, pk_matcher, query_matcher, suo_matcher
from .shared import NOT_ALLOWED_TEXT


@pk_matcher.handle()
async def pk(
    matcher: Matcher,
    session: Uninfo,
    target: At,
) -> None:
    outcome = await game_app.execute_pk(
        legacy_scene_id(session),
        session.user.id,
        target.target,
    )

    if outcome.type is PkOutcomeType.DISABLED:
        await matcher.finish(NOT_ALLOWED_TEXT, at_sender=True)
    if outcome.type is PkOutcomeType.COOLING_DOWN:
        await matcher.finish(
            f"你已经pk不动了喵, 请等待{outcome.remaining}秒后再pk喵",
            at_sender=True,
        )
    if outcome.type is PkOutcomeType.SELF_TARGET:
        await matcher.finish("你不能pk自己喵", at_sender=True)
    if outcome.type is PkOutcomeType.USERS_CREATED:
        await matcher.finish(
            f"你或对面还没有创建{choice(plugin_config.jj_variable)}喵, 咱全帮你创建了喵, 你们的{choice(plugin_config.jj_variable)}长度都是10cm喵",
            at_sender=True,
        )

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
    uid_msg = f"对决胜利喵, 你的{choice(plugin_config.jj_variable)}增加了{resolution.length_increase}cm喵, 对面则在你的阴影笼罩下减小了{resolution.length_decrease}cm喵"

    if "challenge_started_low_win" in outcome.attacker_status:
        uid_msg += (
            f"\n{botname}检测到你的{choice(plugin_config.jj_variable)}长度超过25cm，已为你开启✨“登神长阶”✨"
            f"\n你现在的战力变为当前的80%，且无法使用“打胶”与“嗦”指令，请以将{choice(plugin_config.jj_variable)}长度提升至30cm为目标与他人pk吧!"
        )
    elif "challenge_success_high_win" in outcome.attacker_status:
        uid_msg += (
            f"\n🎉恭喜你完成登神挑战🎉\n你的{choice(plugin_config.jj_variable)}长度已超过30cm，授予你🎊“牛々の神”🎊称号"
            f"\n你的战力已恢复，“打胶”与“嗦”指令已重新开放，切记不忘初心，继续冲击更高的境界喵！"
        )

    if "challenge_failed_high_win" in outcome.defender_status:
        uid_msg += (
            f"\n由于你对决的胜利，{botname}检测到TA的{choice(plugin_config.jj_variable)}长度已不足25cm，很遗憾，TA的登神挑战失败，{botname}替TA感谢你的鞭策喵！"
            f"\nTA的{choice(plugin_config.jj_variable)}长度缩短了5cm喵，战力已恢复，“打胶”与“嗦”指令已重新开放喵！"
        )
    elif "challenge_completed_reduce" in outcome.defender_status:
        uid_msg += (
            f"\n由于你对决的胜利，{botname}检测到TA的{choice(plugin_config.jj_variable)}长度已不足25cm，很遗憾，TA跌落神坛，{botname}替TA感谢你的鞭策喵！"
            f"\nTA的{choice(plugin_config.jj_variable)}长度缩短了5cm喵，请不忘初心，再次冲击更高的境界喵！"
        )
    elif "length_near_zero" in outcome.defender_status:
        uid_msg += f"\n由于你对决的胜利，{botname}检测到TA已经变成xnn了喵！"
    elif "length_zero_or_negative" in outcome.defender_status:
        uid_msg += f"\n由于你对决的胜利，{botname}检测到TA已经变成女孩子了喵！"

    probability_msg = f"\n你的战力现在为{outcome.attacker_probability:.0%}喵"
    await matcher.finish(f"{uid_msg}{probability_msg}", at_sender=True)


async def _handle_pk_loss(matcher: Matcher, outcome: PkOutcome) -> None:
    resolution = outcome.resolution
    if resolution is None:
        return
    uid_msg = f"对决失败喵, 在对面{choice(plugin_config.jj_variable)}的阴影笼罩下你的{choice(plugin_config.jj_variable)}减小了{resolution.length_decrease}cm喵, 对面增加了{resolution.length_increase}cm喵"

    if "challenge_failed_high_win" in outcome.attacker_status:
        uid_msg += (
            "\n很遗憾，登神挑战失败，别气馁啦！"
            f"\n你的{choice(plugin_config.jj_variable)}长度缩短了5cm喵，战力已恢复，“打胶”与“嗦”指令已重新开放喵！"
        )
    elif "challenge_completed_reduce" in outcome.attacker_status:
        uid_msg += (
            "\n很遗憾，你跌落神坛，别气馁啦！"
            f"\n你的{choice(plugin_config.jj_variable)}长度缩短了5cm喵，请不忘初心，再次冲击更高的境界喵！"
        )
    elif "length_near_zero" in outcome.attacker_status:
        uid_msg += "\n你醒啦, 你已经变成xnn了！"
    elif "length_zero_or_negative" in outcome.attacker_status:
        uid_msg += "\n你醒啦, 你已经变成女孩子了！"

    if "challenge_started_low_win" in outcome.defender_status:
        uid_msg += (
            f"\n由于你对决的失败，触犯到了神秘的禁忌，{botname}检测到TA的{choice(plugin_config.jj_variable)}长度超过25cm，已为TA开启✨“登神长阶”✨"
            f"\n现在TA的战力变为当前的80%，且无法使用“打胶”与“嗦”指令，请通知TA以将{choice(plugin_config.jj_variable)}长度提升至30cm为目标与群友pk吧！"
        )
    elif "challenge_success_high_win" in outcome.defender_status:
        uid_msg += (
            f"\n🎉恭喜你帮助TA完成登神挑战🎉\nTA的{choice(plugin_config.jj_variable)}长度超过30cm，授予TA🎊“牛々の神”🎊称号"
            "\nTA的战力已恢复，“打胶”与“嗦”指令已重新开放，请提醒TA不忘初心，继续冲击更高的境界喵！"
        )

    probability_msg = f"\n你的战力现在为{outcome.attacker_probability:.0%}喵"
    await matcher.finish(f"{uid_msg}{probability_msg}", at_sender=True)


@grow_matcher.handle()
async def dajiao(matcher: Matcher, session: Uninfo) -> None:
    outcome = await game_app.grow_self(
        legacy_scene_id(session),
        session.user.id,
    )
    if outcome.type is GrowthOutcomeType.DISABLED:
        await matcher.finish(NOT_ALLOWED_TEXT, at_sender=True)
    if outcome.type is GrowthOutcomeType.COOLING_DOWN:
        await matcher.finish(
            f"你已经打不动了喵, 请等待{outcome.remaining}秒后再打喵",
            at_sender=True,
        )
    if outcome.type is GrowthOutcomeType.USER_CREATED:
        await matcher.finish(
            f"你还没有创建{choice(plugin_config.jj_variable)}, 咱帮你创建了喵, 目前长度是10cm喵",
            at_sender=True,
        )
    if outcome.type is GrowthOutcomeType.CHALLENGING:
        await matcher.finish(
            f"你的{choice(plugin_config.jj_variable)}长度在任务范围内，不允许打胶，请专心与群友pk！",
            at_sender=True,
        )
    if outcome.challenge_started:
        await matcher.finish(
            f"打胶结束喵, 你的{choice(plugin_config.jj_variable)}很满意喵, 长了{outcome.random_num}cm喵"
            f"\n由于你无休止的打胶，触犯到了神秘的禁忌，{botname}检测到你的{choice(plugin_config.jj_variable)}长度超过25cm，已为你开启✨“登神长阶”✨"
            f"\n你现在的战力变为当前的80%，且无法使用“打胶”与“嗦”指令，请以将{choice(plugin_config.jj_variable)}长度提升至30cm为目标与他人pk吧！",
            at_sender=True,
        )
    await matcher.finish(
        f"打胶结束喵, 你的{choice(plugin_config.jj_variable)}很满意喵, 长了{outcome.random_num}cm喵, 目前长度为{outcome.new_length}cm喵",
        at_sender=True,
    )


@suo_matcher.handle()
async def suo(
    matcher: Matcher,
    session: Uninfo,
    target: Match[At],
) -> None:
    mentioned = target.result.target if target.available else None
    target_id = int(mentioned or session.user.id)
    pronoun = "TA" if mentioned else "你"
    outcome = await game_app.grow_target(
        legacy_scene_id(session),
        session.user.id,
        target_id,
    )

    if outcome.type is GrowthOutcomeType.DISABLED:
        await matcher.finish(NOT_ALLOWED_TEXT, at_sender=True)
    if outcome.type is GrowthOutcomeType.COOLING_DOWN:
        await matcher.finish(
            f"你已经嗦不动了喵, 请等待{outcome.remaining}秒后再嗦喵",
            at_sender=True,
        )
    if outcome.type is GrowthOutcomeType.USER_CREATED:
        await matcher.finish(
            f"{pronoun}还没有创建{choice(plugin_config.jj_variable)}喵, 咱帮{pronoun}创建了喵, 目前长度是10cm喵",
            at_sender=True,
        )
    if outcome.type is GrowthOutcomeType.CHALLENGING:
        await matcher.finish(
            f"{pronoun}的{choice(plugin_config.jj_variable)}长度在任务范围内，不准嗦！请专心与群友pk！",
            at_sender=True,
        )
    if outcome.challenge_started:
        await matcher.finish(
            f"{pronoun}的{choice(plugin_config.jj_variable)}很满意喵, 嗦长了{outcome.random_num}cm喵"
            f"\n由于{pronoun}无休止的嗦与被嗦，触犯到了神秘的禁忌，{botname}检测到{pronoun}的{choice(plugin_config.jj_variable)}长度超过25cm，"
            f"\n已为{pronoun}开启✨“登神长阶”✨，{pronoun}现在的战力变为80%，且无法使用“打胶”与“嗦”指令，请以将{choice(plugin_config.jj_variable)}长度提升至30cm为目标与他人pk吧！",
            at_sender=True,
        )
    await matcher.finish(
        f"{pronoun}的{choice(plugin_config.jj_variable)}很满意喵, 嗦长了{outcome.random_num}cm喵, 目前长度为{outcome.new_length}cm喵",
        at_sender=True,
    )


@query_matcher.handle()
async def queryjj(
    matcher: Matcher,
    session: Uninfo,
    target: Match[At],
) -> None:
    mentioned = target.result.target if target.available else None
    target_id = int(mentioned or session.user.id)
    pronoun = "TA" if mentioned else "你"
    outcome = await game_app.query_user(
        legacy_scene_id(session),
        target_id,
    )

    if outcome.type is QueryOutcomeType.DISABLED:
        await matcher.finish(NOT_ALLOWED_TEXT, at_sender=True)
    if outcome.type is QueryOutcomeType.USER_CREATED:
        await matcher.finish(
            f"{pronoun}还没有创建{choice(plugin_config.jj_variable)}喵, 咱帮{pronoun}创建了喵, 目前长度是10cm喵",
            at_sender=True,
        )

    if outcome.state is LengthState.GOD:
        msg = f"✨牛々の神✨\n{pronoun}的{choice(plugin_config.jj_variable)}目前长度为{outcome.length}cm喵"
    elif outcome.state is LengthState.NORMAL:
        msg = f"{pronoun}的{choice(plugin_config.jj_variable)}目前长度为{outcome.length}cm喵"
    elif outcome.state is LengthState.XNN:
        msg = f"{pronoun}已经是xnn啦！\n{pronoun}的{choice(plugin_config.jj_variable)}目前长度为{outcome.length}cm喵"
    elif outcome.state is LengthState.NEAR_GIRL:
        msg = f"{pronoun}快要变成女孩子啦！\n{pronoun}的{choice(plugin_config.jj_variable)}目前长度为{outcome.length}cm喵"
    else:
        msg = f"{pronoun}已经是女孩子啦！\n{pronoun}的{choice(plugin_config.jj_variable)}目前长度为{outcome.length}cm喵"
    await matcher.finish(msg, at_sender=True)
