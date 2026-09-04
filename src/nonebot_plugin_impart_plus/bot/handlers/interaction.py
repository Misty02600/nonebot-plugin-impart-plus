"""群友互动 Handler。"""

import asyncio
from random import choice
from typing import cast

from arclet.alconna import Arparma
from nonebot.matcher import Matcher
from nonebot_plugin_alconna import (
    AUTO,
    AlconnaMatcher,
    At,
    Match,
    UniMessage,
)
from nonebot_plugin_uninfo import Member, QryItrface, Uninfo
from nonebot_plugin_uniref import RefContext

from ...impart.app import InteractionGuardType, InteractionResult
from ...impart.core import (
    InteractionAction,
    InteractionParticipant,
    InteractionResolution,
    InteractionReversal,
)
from ..dependencies import botname, game_app
from ..matchers import INTERACTION_ACTIONS, interaction_matcher
from .shared import (
    JJ_NAMES,
    NOT_ALLOWED_TEXT,
    created_user_message,
    get_member_or_none,
    get_members_or_empty,
    get_user_or_none,
    member_display_name,
    member_has_role,
    user_at_target,
    user_display_name,
)


def _interaction_action(result: Arparma) -> InteractionAction:
    action = result.header_match.groups.get("action")
    parsed = INTERACTION_ACTIONS.get(action) if isinstance(action, str) else None
    if parsed is None:
        raise TypeError("互动命令未解析为 InteractionAction")
    return parsed


def select_interaction_target(
    kind: str,
    members: list[Member],
    uid: str,
) -> str | None:
    if kind == "群主":
        return next(
            (member.user.id for member in members if member_has_role(member, "OWNER")),
            None,
        )
    if kind == "管理":
        admin_ids = [
            member.user.id
            for member in members
            if member.user.id != uid and member_has_role(member, "ADMINISTRATOR")
        ]
        return choice(admin_ids) if admin_ids else None
    if kind == "群友":
        member_ids = [member.user.id for member in members if member.user.id != uid]
        return choice(member_ids) if member_ids else None
    raise ValueError(f"未知互动目标类型: {kind}")


async def send_interaction_prompt(
    kind: str,
    req_user_card: str,
    matcher: Matcher,
    requested_action: InteractionAction,
    resolution: InteractionResolution,
) -> None:
    target_text = {
        "群友": "随机一位幸运群友",
        "管理": "随机一位管理",
        "群主": "群主",
    }[kind]
    if resolution.reversal is InteractionReversal.WRONG_ACTION:
        message = (
            f"唔...你{requested_action.value}不了哦~\n"
            f"现在咱将{req_user_card}\n送给{target_text}色色！"
        )
    elif resolution.reversal is InteractionReversal.XNN:
        message = (
            f"{botname}发现你是xnn~现在咱将{req_user_card}\n送给{target_text}色色！"
        )
    elif kind == "群主":
        message = f"现在咱将把群主\n送给{req_user_card}色色！"
    else:
        message = f"现在咱将随机抽取一位幸运{kind}\n送给{req_user_card}色色！"
    await matcher.send(message)


def interaction_report(
    result: InteractionResult,
    req_user_card: str,
    uid: str,
    lucky_user_card: str,
    lucky_user: str,
) -> str:
    requester = (req_user_card, uid)
    target = (lucky_user_card, lucky_user)
    if result.resolution.actor is InteractionParticipant.REQUESTER:
        actor, counterpart = requester, target
    else:
        actor, counterpart = target, requester
    recipient = (
        requester
        if result.resolution.recipient is InteractionParticipant.REQUESTER
        else target
    )

    prefix = f"好欸！{actor[0]}({actor[1]})用时{result.seconds}秒 \n"
    if result.resolution.action is InteractionAction.INJECT:
        action = (
            f"给 {counterpart[0]}({counterpart[1]}) "
            f"注入了{result.ejaculation}毫升的{result.resolution.fluid.value}"
        )
    else:
        action = (
            f"从 {counterpart[0]}({counterpart[1]}) "
            f"榨出了{result.ejaculation}毫升的{result.resolution.fluid.value}"
        )
    report = f"{prefix}{action}, 当日总注入量为：{result.today_total}毫升\n"
    if result.feminized:
        name = choice(JJ_NAMES)
        return (
            f"{report}\n{recipient[0]}({recipient[1]})被注入了太多脱氧核糖核酸……"
            f"\n\n在{actor[0]}({actor[1]})的猛烈攻势下，TA的{name}彻底萎缩消失了♡"
            f"\n\n取而代之的是一个深度{abs(result.recipient_length)}cm的小学♡"
            f"\n\n{recipient[0]}({recipient[1]})已经完全雌堕，变成女孩子了喵！"
        )
    if result.risk_warning:
        return (
            f"{report}\n由于{recipient[0]}({recipient[1]})的当日注入量过多，"
            f"TA的{choice(JJ_NAMES)}开始变得不稳定了..."
        )
    return report


def _missing_target_message(kind: str) -> str:
    return {
        "群友": "喵喵喵? 找不到群友!",
        "管理": "喵喵喵? 找不到群管理!",
        "群主": "喵喵喵? 找不到群主!",
    }[kind]


@interaction_matcher.handle()
async def yinpa(
    matcher: Matcher,
    session: Uninfo,
    interface: QryItrface,
    refs: RefContext,
    result: Arparma,
    kind: str,
    targets: Match[tuple[At, ...]],
) -> None:
    requested_action = _interaction_action(result)
    scene_ref = refs.scene_ref
    user_ref = refs.user_ref
    uid = session.user.id
    mentioned = (
        user_at_target(targets.result[0])
        if kind == "群友" and targets.available
        else None
    )

    guard = await game_app.prepare_interaction(scene_ref, user_ref)
    if guard.type is InteractionGuardType.DISABLED:
        await matcher.finish(NOT_ALLOWED_TEXT, at_sender=True)
    if guard.type is InteractionGuardType.USER_CREATED:
        await matcher.finish(
            created_user_message(guard.created_users, user_ref, user_ref),
            at_sender=True,
        )
    if guard.type is InteractionGuardType.COOLING_DOWN:
        await matcher.finish(
            f"你已经榨不出来任何东西了, 请先休息{guard.remaining}秒",
            at_sender=True,
        )

    req_user_card = member_display_name(
        session.member,
        user_display_name(session.user, session.user.id),
    )
    members: list[Member] = []
    if mentioned is None:
        members = await get_members_or_empty(interface, session)
        if not members:
            message = "请@指定目标" if kind == "群友" else _missing_target_message(kind)
            await matcher.finish(message)

    reverse_roll = (
        game_app.roll_interaction()
        if requested_action is InteractionAction.INJECT
        else None
    )
    lucky_user = mentioned or select_interaction_target(kind, members, uid)
    if lucky_user is None:
        await matcher.finish(_missing_target_message(kind))
    if lucky_user == uid:
        await matcher.finish(f"你{requested_action.value}你自己?")

    lucky_user_ref = refs.build_user_ref(lucky_user)
    resolution = await game_app.begin_interaction(
        user_ref,
        lucky_user_ref,
        requested_action,
        reverse_roll,
    )
    if mentioned is None:
        await send_interaction_prompt(
            kind,
            req_user_card,
            matcher,
            requested_action,
            resolution,
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
        user_ref,
        lucky_user_ref,
        resolution,
    )
    report = interaction_report(
        interaction_result,
        req_user_card,
        uid,
        lucky_user_card,
        lucky_user,
    )
    message = UniMessage.text(report)
    if lucky_user_avatar:
        message.image(url=lucky_user_avatar)
    await cast(AlconnaMatcher, matcher).send(message, fallback=AUTO)
