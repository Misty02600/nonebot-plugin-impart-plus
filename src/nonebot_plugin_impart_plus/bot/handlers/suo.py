"""嗦牛子命令。"""

from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.matcher import Matcher

from ...core.game import ChallengeStatus, get_random_num
from ...core.world import LengthState
from .. import CooldownDep, DataManagerDep
from ..dependencies import AtTarget, RandomNickname, pick_jj_alias
from ..texts.interaction_texts import suo_target_negative
from ..texts.progression_texts import SuoCopy, suo_cd
from .common import group_enabled_check

# region 事件处理函数


async def suo_handler(
    matcher: Matcher,
    event: GroupMessageEvent,
    dm: DataManagerDep,
    cd: CooldownDep,
    at: AtTarget,
    botname: RandomNickname,
) -> None:
    """嗦牛子。"""
    uid = event.get_user_id()

    # CD 检查
    allowed, remaining = cd.check_suo(uid)
    if not allowed:
        await matcher.finish(
            suo_cd(remaining=remaining),
            at_sender=True,
        )

    target_id = int(uid if at == "寄" else at)
    pronoun = "你" if at == "寄" else "TA"

    if not await dm.is_in_table(target_id):
        await dm.add_new_user(target_id)
        await matcher.finish(
            SuoCopy(pronoun=pronoun, jj_name=pick_jj_alias()).create(),
            at_sender=True,
        )
        return

    # 目标在负值世界时不允许嗦
    target_length = await dm.get_jj_length(target_id)
    if LengthState(length=target_length).is_negative_world:
        jj_name = pick_jj_alias()
        await matcher.finish(
            suo_target_negative(pronoun=pronoun, jj_name=jj_name),
            at_sender=True,
        )
        return

    # 校验通过，记录 CD
    cd.record_suo(uid)

    random_num = get_random_num()
    target_status = await dm.update_challenge_status(target_id)

    if target_status == ChallengeStatus.IS_CHALLENGING:
        await matcher.finish(
            SuoCopy(pronoun=pronoun, jj_name=pick_jj_alias()).challenging(),
            at_sender=True,
        )
        return

    current_length = await dm.get_jj_length(target_id)
    await dm.set_jj_length(target_id, random_num)
    new_length = await dm.get_jj_length(target_id)

    jj_name = pick_jj_alias()
    if current_length < 25 <= new_length:
        await dm.update_challenge_status(target_id)
        copy = SuoCopy(
            pronoun=pronoun,
            jj_name=jj_name,
            delta=random_num,
            botname=botname,
        )
        await matcher.finish(copy.trigger_challenge(), at_sender=True)
    else:
        copy = SuoCopy(
            pronoun=pronoun,
            jj_name=jj_name,
            delta=random_num,
            length=new_length,
        )
        await matcher.finish(copy.finish(), at_sender=True)


# endregion

# region 命令注册

suo_matcher = on_command(
    "嗦牛子",
    aliases={"嗦", "suo"},
    priority=20,
    block=True,
    handlers=[group_enabled_check, suo_handler],
)

# endregion
