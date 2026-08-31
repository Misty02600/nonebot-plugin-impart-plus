"""群友互动 Handler。"""

import asyncio
from random import choice
from typing import cast

from nonebot.matcher import Matcher
from nonebot_plugin_alconna import AUTO, AlconnaMatcher, At, Match, UniMessage
from nonebot_plugin_uninfo import Member, QryItrface, Uninfo

from ...impart.app import InteractionGuardType
from ..context import legacy_scene_id
from ..dependencies import botname, game_app
from ..matchers import interaction_matcher
from .shared import (
    NOT_ALLOWED_TEXT,
    get_member_or_none,
    get_members_or_empty,
    get_user_or_none,
    member_display_name,
    member_has_role,
    user_display_name,
)


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
        await matcher.send(f"现在咱将随机抽取一位幸运群友\n送给{req_user_card}色色！")
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
        await matcher.send(f"唔...你透不了哦~\n现在咱将{req_user_card}\n送给群主色色！")
    elif 5 >= jj_length > 0 and random_nn < 0.5:
        await matcher.send(
            f"{botname}发现你是xnn~现在咱将{req_user_card}\n送给群主色色！"
        )
    else:
        await matcher.send(f"现在咱将把群主\n送给{req_user_card}色色！")
    return str(lucky_user)


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
        await matcher.send(f"现在咱将随机抽取一位幸运管理\n送给{req_user_card}色色！")
    return str(lucky_user)


async def yinpa_identity_handle(
    kind: str,
    members: list[Member],
    req_user_card: str,
    matcher: Matcher,
    uid: int,
    random_nn: float,
) -> str:
    if kind == "群主":
        return await yinpa_owner_handle(uid, members, req_user_card, matcher, random_nn)
    if kind == "管理":
        return await yinpa_admin_handle(uid, members, req_user_card, matcher, random_nn)
    return await yinpa_member_handle(members, req_user_card, matcher, uid, random_nn)


@interaction_matcher.handle()
async def yinpa(
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
    lucky_user = mentioned or await yinpa_identity_handle(
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
