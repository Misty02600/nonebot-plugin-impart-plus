"""打胶命令"""

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.matcher import Matcher

from ...core.game import ChallengeStatus, get_random_num
from ...core.world import LengthState
from .. import CooldownDep, DataManagerDep
from ..dependencies import RandomNickname, pick_jj_alias
from ..texts.interaction_texts import wrong_world_negative
from ..texts.progression_texts import DajiaoCopy, dajiao_cd
from .common import group_enabled_check

# region 事件处理函数


async def dajiao_handler(
    matcher: Matcher,
    event: GroupMessageEvent,
    dm: DataManagerDep,
    cd: CooldownDep,
    botname: RandomNickname,
) -> None:
    """打胶"""
    uid = event.get_user_id()

    # 负值玩家不能使用正值指令
    if await dm.is_in_table(int(uid)):
        length = await dm.get_jj_length(int(uid))
        if LengthState(length=length).is_negative_world:
            await matcher.finish(wrong_world_negative(pick_jj_alias()), at_sender=True)

    # CD 检查
    allowed, remaining = cd.check_dj(uid)
    if not allowed:
        await matcher.finish(
            dajiao_cd(remaining=remaining),
            at_sender=True,
        )

    cd.record_dj(uid)

    if not await dm.is_in_table(int(uid)):
        await dm.add_new_user(int(uid))
        await matcher.finish(
            DajiaoCopy(jj_name=pick_jj_alias()).create(),
            at_sender=True,
        )
        return

    uid_length = await dm.get_jj_length(int(uid))
    random_num = get_random_num()
    uid_status = await dm.update_challenge_status(int(uid))

    if uid_status == ChallengeStatus.IS_CHALLENGING:
        await matcher.finish(
            DajiaoCopy(jj_name=pick_jj_alias()).challenging(),
            at_sender=True,
        )
        return

    await dm.set_jj_length(int(uid), random_num)
    new_length = await dm.get_jj_length(int(uid))

    jj_name = pick_jj_alias()
    if uid_length < 25 <= new_length:
        await dm.update_challenge_status(int(uid))
        copy = DajiaoCopy(
            jj_name=jj_name,
            delta=random_num,
            botname=botname,
        )
        await matcher.finish(copy.trigger_challenge(), at_sender=True)
    else:
        copy = DajiaoCopy(
            jj_name=jj_name,
            delta=random_num,
            length=new_length,
        )
        await matcher.finish(copy.finish(), at_sender=True)


# endregion

# region 命令注册

dajiao_matcher = on_regex(
    "^(打胶|开导)$",
    priority=20,
    block=True,
    handlers=[group_enabled_check, dajiao_handler],
)

# endregion
