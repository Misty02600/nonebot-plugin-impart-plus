"""开扣（挖矿）命令"""

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.matcher import Matcher

from ...core.game import ChallengeStatus, get_random_num
from .. import CooldownDep, DataManagerDep
from ..dependencies import RandomNickname, pick_hole_alias
from ..texts.interaction_texts import wrong_world_positive
from ..texts.progression_texts import KaikouCopy, kaikou_cd
from .common import group_enabled_check

# region 事件处理函数


async def kaikou_handler(
    matcher: Matcher,
    event: GroupMessageEvent,
    dm: DataManagerDep,
    cd: CooldownDep,
    botname: RandomNickname,
) -> None:
    """开扣（挖矿）— 负值世界自增深度。"""
    uid = event.get_user_id()

    # 正值玩家不能使用负值指令
    if await dm.is_in_table(int(uid)):
        length = await dm.get_jj_length(int(uid))
        if length > 0:
            await matcher.finish(wrong_world_positive(), at_sender=True)
    else:
        # 新玩家默认正值，不能使用
        await dm.add_new_user(int(uid))
        await matcher.finish(wrong_world_positive(), at_sender=True)

    # CD 检查（复用打胶 CD）
    allowed, remaining = cd.check_dj(uid)
    if not allowed:
        await matcher.finish(kaikou_cd(remaining=remaining), at_sender=True)

    cd.record_dj(uid)

    uid_length = await dm.get_jj_length(int(uid))
    random_num = get_random_num()
    uid_status = await dm.update_challenge_status(int(uid))

    if uid_status == ChallengeStatus.IS_CHALLENGING:
        await matcher.finish(
            KaikouCopy(hole_name=pick_hole_alias()).challenging(),
            at_sender=True,
        )
        return

    # 负值世界：增长用负数（深度增加）
    await dm.set_jj_length(int(uid), -random_num)
    new_length = await dm.get_jj_length(int(uid))
    new_depth = abs(new_length)

    hole_name = pick_hole_alias()
    if abs(uid_length) < 25 <= new_depth:
        await dm.update_challenge_status(int(uid))
        copy = KaikouCopy(
            hole_name=hole_name,
            delta=random_num,
            botname=botname,
        )
        await matcher.finish(copy.trigger_challenge(), at_sender=True)
    else:
        copy = KaikouCopy(
            hole_name=hole_name,
            delta=random_num,
            depth=new_depth,
        )
        await matcher.finish(copy.finish(), at_sender=True)


# endregion

# region 命令注册

kaikou_matcher = on_regex(
    r"^(开扣|挖矿)$",
    priority=20,
    block=True,
    handlers=[group_enabled_check, kaikou_handler],
)

# endregion
