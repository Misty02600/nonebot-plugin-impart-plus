"""NoneBot 事件接入与回复。"""

import asyncio
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
from nonebot_plugin_uninfo import Interface, Member, QryItrface, Uninfo, User

from .. import __plugin_meta__
from ..impart.app import (
    GrowthOutcomeType,
    InjectionQueryType,
    InteractionGuardType,
    PkOutcome,
    PkOutcomeType,
    QueryOutcomeType,
    RankingOutcomeType,
)
from ..impart.core import LengthState
from ..infra.chart_renderer import draw_bar_chart
from .context import legacy_scene_id, member_parent_scene_id
from .dependencies import botname, game_app, plugin_config

NOT_ALLOWED_TEXT = (
    '当前未开启impart游戏, 请管理员发送"开始银趴", "禁止银趴"以开启/关闭该功能'
)


def user_display_name(user: User | None, fallback: str) -> str:
    if user is None:
        return fallback
    return str(user.nick or user.name or fallback)


def member_display_name(member: Member | None, fallback: str) -> str:
    if member is None:
        return fallback
    return str(member.nick or member.user.nick or member.user.name or fallback)


def member_has_role(member: Member, role_id: str) -> bool:
    return any(role.id == role_id for role in member.roles)


async def get_user_or_none(interface: Interface, user_id: str) -> User | None:
    try:
        return await interface.get_user(user_id)
    except Exception:
        return None


async def get_member_or_none(
    interface: Interface,
    session: Uninfo,
    user_id: str,
) -> Member | None:
    try:
        return await interface.get_member(
            session.scene.type,
            member_parent_scene_id(session),
            user_id,
        )
    except Exception:
        return None


async def get_members_or_empty(
    interface: Interface,
    session: Uninfo,
) -> list[Member]:
    try:
        return await interface.get_members(
            session.scene.type,
            member_parent_scene_id(session),
        )
    except Exception:
        return []


class Impart:
    @staticmethod
    async def penalties_and_resets() -> None:
        await game_app.penalties_and_resets()

    @staticmethod
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
            await Impart.handle_pk_win(matcher, outcome)
        else:
            await Impart.handle_pk_loss(matcher, outcome)

    @staticmethod
    async def handle_pk_win(matcher: Matcher, outcome: PkOutcome) -> None:
        resolution = outcome.resolution
        if resolution is None:
            return
        uid_msg = f"对决胜利喵, 你的{choice(plugin_config.jj_variable)}增加了{resolution.length_increase}cm喵, 对面则在你的阴影笼罩下减小了{resolution.length_decrease}cm喵"

        if "challenge_started_low_win" in outcome.attacker_status:
            uid_msg += (
                f"\n{botname}检测到你的{choice(plugin_config.jj_variable)}长度超过25cm，已为你开启✨“登神长阶”✨"
                f"\n你现在的获胜概率变为当前的80%，且无法使用“打胶”与“嗦”指令，请以将{choice(plugin_config.jj_variable)}长度提升至30cm为目标与他人pk吧!"
            )
        elif "challenge_success_high_win" in outcome.attacker_status:
            uid_msg += (
                f"\n🎉恭喜你完成登神挑战🎉\n你的{choice(plugin_config.jj_variable)}长度已超过30cm，授予你🎊“牛々の神”🎊称号"
                f"\n你的获胜概率已恢复，“打胶”与“嗦”指令已重新开放，切记不忘初心，继续冲击更高的境界喵！"
            )

        if "challenge_failed_high_win" in outcome.defender_status:
            uid_msg += (
                f"\n由于你对决的胜利，{botname}检测到TA的{choice(plugin_config.jj_variable)}长度已不足25cm，很遗憾，TA的登神挑战失败，{botname}替TA感谢你的鞭策喵！"
                f"\nTA的{choice(plugin_config.jj_variable)}长度缩短了5cm喵，获胜概率已恢复，“打胶”与“嗦”指令已重新开放喵！"
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

    @staticmethod
    async def handle_pk_loss(matcher: Matcher, outcome: PkOutcome) -> None:
        resolution = outcome.resolution
        if resolution is None:
            return
        uid_msg = f"对决失败喵, 在对面{choice(plugin_config.jj_variable)}的阴影笼罩下你的{choice(plugin_config.jj_variable)}减小了{resolution.length_decrease}cm喵, 对面增加了{resolution.length_increase}cm喵"

        if "challenge_failed_high_win" in outcome.attacker_status:
            uid_msg += (
                "\n很遗憾，登神挑战失败，别气馁啦！"
                f"\n你的{choice(plugin_config.jj_variable)}长度缩短了5cm喵，获胜概率已恢复，“打胶”与“嗦”指令已重新开放喵！"
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
                f"\n现在TA的获胜概率变为当前的80%，且无法使用“打胶”与“嗦”指令，请通知TA以将{choice(plugin_config.jj_variable)}长度提升至30cm为目标与群友pk吧！"
            )
        elif "challenge_success_high_win" in outcome.defender_status:
            uid_msg += (
                f"\n🎉恭喜你帮助TA完成登神挑战🎉\nTA的{choice(plugin_config.jj_variable)}长度超过30cm，授予TA🎊“牛々の神”🎊称号"
                "\nTA的获胜概率已恢复，“打胶”与“嗦”指令已重新开放，请提醒TA不忘初心，继续冲击更高的境界喵！"
            )

        probability_msg = f"\n你的战力现在为{outcome.attacker_probability:.0%}喵"
        await matcher.finish(f"{uid_msg}{probability_msg}", at_sender=True)

    @staticmethod
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
                f"\n你现在的获胜概率变为当前的80%，且无法使用“打胶”与“嗦”指令，请以将{choice(plugin_config.jj_variable)}长度提升至30cm为目标与他人pk吧！",
                at_sender=True,
            )
        await matcher.finish(
            f"打胶结束喵, 你的{choice(plugin_config.jj_variable)}很满意喵, 长了{outcome.random_num}cm喵, 目前长度为{outcome.new_length}cm喵",
            at_sender=True,
        )

    @staticmethod
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
                f"\n已为{pronoun}开启✨“登神长阶”✨，{pronoun}现在的获胜概率变为80%，且无法使用“打胶”与“嗦”指令，请以将{choice(plugin_config.jj_variable)}长度提升至30cm为目标与他人pk吧！",
                at_sender=True,
            )
        await matcher.finish(
            f"{pronoun}的{choice(plugin_config.jj_variable)}很满意喵, 嗦长了{outcome.random_num}cm喵, 目前长度为{outcome.new_length}cm喵",
            at_sender=True,
        )

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    async def yinpa_member_handle(
        members: list[Member],
        req_user_card: str,
        matcher: Matcher,
        uid: int,
        random_nn: float,
    ) -> str:
        member_ids = [int(member.user.id) for member in members]
        if uid in member_ids:
            member_ids.remove(uid)
        if not member_ids:
            game_app.release_interaction_cooldown(uid)
            await matcher.finish("喵喵喵? 找不到群友!")
        lucky_user = choice(member_ids)
        jj_length = await game_app.get_length(uid)
        if jj_length > 5:
            await matcher.send(
                f"现在咱将随机抽取一位幸运群友\n送给{req_user_card}色色！"
            )
        elif 5 >= jj_length > 0:
            if random_nn < 0.5:
                await matcher.send(
                    f"{botname}发现你是xnn~现在咱将{req_user_card}\n送给随机一位幸运群友色色！"
                )
            else:
                await matcher.send(
                    f"现在咱将随机抽取一位幸运群友\n送给{req_user_card}色色！"
                )
        else:
            await matcher.send(
                f"唔...你透不了哦~\n现在咱将{req_user_card}\n送给随机一位幸运群友色色！"
            )
        return str(lucky_user)

    @staticmethod
    async def yinpa_owner_handle(
        uid: int,
        members: list[Member],
        req_user_card: str,
        matcher: Matcher,
        random_nn: float,
    ) -> str:
        lucky_user = next(
            (member.user.id for member in members if member_has_role(member, "OWNER")),
            str(uid),
        )
        if int(lucky_user) == uid:
            game_app.release_interaction_cooldown(uid)
            await matcher.finish("你透你自己?")
        jj_length = await game_app.get_length(uid)
        if jj_length <= 0:
            await matcher.send(
                f"唔...你透不了哦~\n现在咱将{req_user_card}\n送给群主色色！"
            )
        elif 5 >= jj_length > 0 and random_nn < 0.5:
            await matcher.send(
                f"{botname}发现你是xnn~现在咱将{req_user_card}\n送给群主色色！"
            )
        else:
            await matcher.send(f"现在咱将把群主\n送给{req_user_card}色色！")
        return str(lucky_user)

    @staticmethod
    async def yinpa_admin_handle(
        uid: int,
        members: list[Member],
        req_user_card: str,
        matcher: Matcher,
        random_nn: float,
    ) -> str:
        admin_id = [
            int(member.user.id)
            for member in members
            if member_has_role(member, "ADMINISTRATOR")
        ]
        if uid in admin_id:
            admin_id.remove(uid)
        if not admin_id:
            game_app.release_interaction_cooldown(uid)
            await matcher.finish("喵喵喵? 找不到群管理!")
        lucky_user = choice(admin_id)
        jj_length = await game_app.get_length(uid)
        if jj_length <= 0:
            await matcher.send(
                f"唔...你透不了哦~\n现在咱将{req_user_card}\n送给随机一位管理色色！"
            )
        elif 5 >= jj_length > 0 and random_nn < 0.5:
            await matcher.send(
                f"{botname}发现你是xnn~现在咱将{req_user_card}\n送给随机一位管理色色！"
            )
        else:
            await matcher.send(
                f"现在咱将随机抽取一位幸运管理\n送给{req_user_card}色色！"
            )
        return str(lucky_user)

    async def yinpa_identity_handle(
        self,
        kind: str,
        members: list[Member],
        req_user_card: str,
        matcher: Matcher,
        uid: int,
        random_nn: float,
    ) -> str:
        if kind == "群主":
            return await self.yinpa_owner_handle(
                uid, members, req_user_card, matcher, random_nn
            )
        if kind == "管理":
            return await self.yinpa_admin_handle(
                uid, members, req_user_card, matcher, random_nn
            )
        return await self.yinpa_member_handle(
            members, req_user_card, matcher, uid, random_nn
        )

    async def yinpa(
        self,
        matcher: Matcher,
        session: Uninfo,
        interface: QryItrface,
        kind: str,
        target: Match[At],
    ) -> None:
        scene_id = legacy_scene_id(session)
        uid = int(session.user.id)
        guard = await game_app.prepare_interaction(scene_id, uid)
        if guard.type is InteractionGuardType.DISABLED:
            await matcher.finish(NOT_ALLOWED_TEXT, at_sender=True)
        if guard.type is InteractionGuardType.COOLING_DOWN:
            await matcher.finish(
                f"你已经榨不出来任何东西了, 请先休息{guard.remaining}秒",
                at_sender=True,
            )

        req_user_card = member_display_name(
            session.member,
            user_display_name(session.user, session.user.id),
        )
        mentioned = target.result.target if target.available else None
        members: list[Member] = []
        if mentioned is None:
            members = await get_members_or_empty(interface, session)
            if not members:
                game_app.release_interaction_cooldown(uid)
                await matcher.finish(
                    "当前平台无法获取群成员列表，请明确@目标",
                )
        random_nn = game_app.roll_interaction()
        lucky_user = mentioned or await self.yinpa_identity_handle(
            kind, members, req_user_card, matcher, uid, random_nn
        )
        lucky_member = next(
            (member for member in members if member.user.id == lucky_user),
            None,
        ) or await get_member_or_none(interface, session, lucky_user)
        lucky_user_info = (
            lucky_member.user
            if lucky_member
            else await get_user_or_none(interface, lucky_user)
        )
        lucky_user_card = member_display_name(
            lucky_member,
            user_display_name(lucky_user_info, "群友"),
        )
        lucky_user_avatar = (lucky_member.user.avatar if lucky_member else None) or (
            lucky_user_info.avatar if lucky_user_info else None
        )
        await asyncio.sleep(2)
        interaction_result = await game_app.complete_interaction(
            uid,
            int(lucky_user),
            random_nn,
        )
        if interaction_result.reversed:
            report = f"好欸！{lucky_user_card}({lucky_user})用时{interaction_result.seconds}秒 \n给 {req_user_card}({uid}) 注入了{interaction_result.ejaculation}毫升的脱氧核糖核酸, 当日总注入量为：{interaction_result.today_total}毫升\n"
        else:
            report = f"好欸！{req_user_card}({uid})用时{interaction_result.seconds}秒 \n给 {lucky_user_card}({lucky_user}) 注入了{interaction_result.ejaculation}毫升的脱氧核糖核酸, 当日总注入量为：{interaction_result.today_total}毫升\n"
        message = UniMessage.text(report)
        if lucky_user_avatar:
            message.image(url=lucky_user_avatar)
        await cast(AlconnaMatcher, matcher).send(message, fallback=AUTO)

    @staticmethod
    async def open_module(
        matcher: Matcher,
        session: Uninfo,
        result: CommandResult,
    ) -> None:
        scene_id = legacy_scene_id(session)
        if "enable" in result.result.subcommands:
            await game_app.set_group_enabled(scene_id, True)
            await matcher.finish("功能已开启喵")
        elif "disable" in result.result.subcommands:
            await game_app.set_group_enabled(scene_id, False)
            await matcher.finish("功能已禁用喵")

    @staticmethod
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

    @staticmethod
    async def yinpa_introduce(matcher: Matcher) -> None:
        await cast(AlconnaMatcher, matcher).send(
            UniMessage.text(__plugin_meta__.usage),
            fallback=AUTO,
        )


impart = Impart()
