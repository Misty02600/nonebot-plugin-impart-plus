"""群友互动 Handler。"""

import asyncio
from random import choice
from typing import cast

from nonebot.matcher import Matcher
from nonebot_plugin_alconna import (
    AUTO,
    AlconnaMatcher,
    At,
    Match,
    UniMessage,
)
from nonebot_plugin_uninfo import Member, QryItrface, Uninfo
from nonebot_plugin_uniref import RefContext, UserRef

from ...impart.app import InteractionGuardType
from ..dependencies import botname, game_app
from ..matchers import interaction_matcher
from .shared import (
    NOT_ALLOWED_TEXT,
    get_member_or_none,
    get_members_or_empty,
    get_user_or_none,
    member_display_name,
    member_has_role,
    user_at_target,
    user_display_name,
)


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
            if member_has_role(member, "ADMINISTRATOR")
        ]
        if not admin_ids:
            return None
        other_admin_ids = [user_id for user_id in admin_ids if user_id != uid]
        return choice(other_admin_ids or admin_ids)
    if kind == "群友":
        member_ids = [member.user.id for member in members if member.user.id != uid]
        return choice(member_ids) if member_ids else None
    raise ValueError(f"未知互动目标类型: {kind}")


async def send_interaction_prompt(
    kind: str,
    req_user_card: str,
    matcher: Matcher,
    user_ref: UserRef,
    random_nn: float,
) -> None:
    jj_length = await game_app.get_length(user_ref)
    target_text = {
        "群友": "随机一位幸运群友",
        "管理": "随机一位管理",
        "群主": "群主",
    }[kind]
    if jj_length <= 0:
        message = f"唔...你透不了哦~\n现在咱将{req_user_card}\n送给{target_text}色色！"
    elif jj_length <= 5 and random_nn < 0.5:
        message = (
            f"{botname}发现你是xnn~现在咱将{req_user_card}\n送给{target_text}色色！"
        )
    elif kind == "群主":
        message = f"现在咱将把群主\n送给{req_user_card}色色！"
    else:
        message = f"现在咱将随机抽取一位幸运{kind}\n送给{req_user_card}色色！"
    await matcher.send(message)


@interaction_matcher.handle()
async def yinpa(
    matcher: Matcher,
    session: Uninfo,
    interface: QryItrface,
    refs: RefContext,
    kind: str,
    target: Match[At],
) -> None:
    scene_ref = refs.scene_ref
    user_ref = refs.user_ref
    uid = session.user.id
    mentioned = (
        user_at_target(target.result) if kind == "群友" and target.available else None
    )

    guard = await game_app.prepare_interaction(scene_ref, user_ref)
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
    members: list[Member] = []
    if mentioned is None:
        members = await get_members_or_empty(interface, session)
        if not members:
            game_app.release_interaction_cooldown(user_ref)
            await matcher.finish("请@指定目标" if kind == "群友" else f"没找到{kind}")
    random_nn = game_app.roll_interaction()
    lucky_user = mentioned or select_interaction_target(kind, members, uid)
    if lucky_user is None:
        game_app.release_interaction_cooldown(user_ref)
        await matcher.finish(
            "喵喵喵? 找不到群友!" if kind == "群友" else f"没找到{kind}"
        )
    if lucky_user == uid:
        game_app.release_interaction_cooldown(user_ref)
        await matcher.finish("你透你自己?")
    if mentioned is None:
        await send_interaction_prompt(
            kind,
            req_user_card,
            matcher,
            user_ref,
            random_nn,
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
        refs.build_user_ref(lucky_user),
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
