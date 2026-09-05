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

from ...impart.app import InteractionGuard, InteractionGuardType, InteractionResult
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
    target_card: str,
) -> None:
    target_text = {
        "群友": "随机一位幸运群友",
        "管理": "随机一位管理",
        "群主": "群主",
    }[kind]
    if resolution.action is InteractionAction.CUDDLE:
        message = f"{botname}发现你俩都是xnn喵~现在咱将{req_user_card}\n送给{target_card}色色！"
    elif resolution.reversal is InteractionReversal.WRONG_ACTION:
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
    requester = InteractionParticipant.REQUESTER
    target = InteractionParticipant.TARGET
    people = {
        requester: f"{req_user_card}({uid})",
        target: f"{lucky_user_card}({lucky_user})",
    }
    if result.resolution.action is InteractionAction.CUDDLE:
        self_receipt = result.receipts[requester]
        target_receipt = result.receipts[target]
        report = (
            f"好欸！{people[requester]}和{people[target]}蹭蹭贴贴了{result.seconds}秒\n"
            f"分别挤出了{target_receipt.volume}毫升和{self_receipt.volume}毫升的脱氧核糖核酸，"
            f"当日总注入量分别为：{self_receipt.settlement.total}毫升、"
            f"{target_receipt.settlement.total}毫升\n"
        )
    else:
        transfer = result.resolution.transfers[0]
        receipt = result.receipts[transfer.recipient]
        if result.resolution.action is InteractionAction.INJECT:
            actor = transfer.source
            action = (
                f"给 {people[transfer.recipient]} 注入了"
                f"{receipt.volume}毫升的{transfer.fluid.value}"
            )
        else:
            actor = transfer.recipient
            action = (
                f"从 {people[transfer.source]} 榨出了"
                f"{receipt.volume}毫升的{transfer.fluid.value}"
            )
        report = (
            f"好欸！{people[actor]}用时{result.seconds}秒 \n"
            f"{action}, 当日总注入量为：{receipt.settlement.total}毫升\n"
        )

    transfers = {
        transfer.recipient: transfer for transfer in result.resolution.transfers
    }
    for person in (requester, target):
        receipt = result.receipts.get(person)
        if receipt is None:
            continue
        settlement = receipt.settlement
        transfer = transfers[person]
        if settlement.feminized:
            if result.resolution.action is InteractionAction.CUDDLE:
                cause = "在一阵缠绵后"
            elif result.resolution.action is InteractionAction.SQUEEZE:
                cause = f"在{people[person]}的主动索求下"
            else:
                cause = f"在{people[transfer.source]}的猛烈攻势下"
            name = choice(JJ_NAMES)
            report += (
                f"\n{people[person]}被注入了太多{transfer.fluid.value}……"
                f"\n\n{cause}，TA的{name}彻底萎缩消失了♡"
                f"\n\n取而代之的是一个深度{abs(settlement.length)}cm的小学♡"
                f"\n\n{people[person]}已经完全雌堕，变成了女孩子喵！"
            )
        elif settlement.risk_warning:
            report += (
                f"\n由于{people[person]}的当日注入量过多，"
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
    )
    if isinstance(resolution, InteractionGuard):
        await matcher.finish(
            f"你已经榨不出来任何东西了, 请先休息{resolution.remaining}秒",
            at_sender=True,
        )
        return

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
    if mentioned is None:
        await send_interaction_prompt(
            kind, req_user_card, matcher, requested_action, resolution, lucky_user_card
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
