"""舔小学命令"""

from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.matcher import Matcher

from ...core.game import ChallengeStatus, get_random_num
from ...core.world import LengthState
from .. import CooldownDep, DataManagerDep
from ..dependencies import AtTarget, RandomNickname, pick_hole_alias
from ..texts.interaction_texts import tian_target_not_negative
from ..texts.progression_texts import TianCopy, tian_cd
from .common import group_enabled_check

# region 事件处理函数


async def tian_handler(
    matcher: Matcher,
    event: GroupMessageEvent,
    dm: DataManagerDep,
    cd: CooldownDep,
    at: AtTarget,
    botname: RandomNickname,
) -> None:
    """舔小学 — 负值世界增加目标深度。"""
    uid = event.get_user_id()

    # CD 检查（复用嗦 CD）
    allowed, remaining = cd.check_suo(uid)
    if not allowed:
        await matcher.finish(tian_cd(remaining=remaining), at_sender=True)

    target_id = int(uid if at == "寄" else at)
    pronoun = "你" if at == "寄" else "TA"

    # 目标必须存在且也是负值
    if not await dm.is_in_table(target_id):
        await dm.add_new_user(target_id)
        await matcher.finish(tian_target_not_negative(pronoun=pronoun), at_sender=True)
        return

    target_length = await dm.get_jj_length(target_id)
    if LengthState(length=target_length).is_positive_world:
        await matcher.finish(tian_target_not_negative(pronoun=pronoun), at_sender=True)
        return

    # 校验通过，记录 CD
    cd.record_suo(uid)

    random_num = get_random_num()
    target_status = await dm.update_challenge_status(target_id)

    if target_status == ChallengeStatus.IS_CHALLENGING:
        await matcher.finish(
            TianCopy(pronoun=pronoun, hole_name=pick_hole_alias()).challenging(),
            at_sender=True,
        )
        return

    current_depth = abs(target_length)
    # 负值世界：增加深度用负数
    await dm.set_jj_length(target_id, -random_num)
    new_length = await dm.get_jj_length(target_id)
    new_depth = abs(new_length)

    hole_name = pick_hole_alias()
    if current_depth < 25 <= new_depth:
        await dm.update_challenge_status(target_id)
        copy = TianCopy(
            pronoun=pronoun,
            hole_name=hole_name,
            delta=random_num,
            botname=botname,
        )
        await matcher.finish(copy.trigger_challenge(), at_sender=True)
    else:
        copy = TianCopy(
            pronoun=pronoun,
            hole_name=hole_name,
            delta=random_num,
            depth=new_depth,
        )
        await matcher.finish(copy.finish(), at_sender=True)


# endregion

# region 命令注册

tian_matcher = on_command(
    "舔小学",
    aliases={"舔"},
    priority=20,
    block=True,
    handlers=[group_enabled_check, tian_handler],
)

# endregion
