"""查询命令"""

from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.matcher import Matcher

from .. import DataManagerDep
from ..dependencies import AtTarget, pick_hole_alias, pick_jj_alias
from ..texts.progression_texts import NegQueryCopy, QueryCopy
from .common import group_enabled_check

# region 事件处理函数


async def query_handler(
    matcher: Matcher,
    event: GroupMessageEvent,
    dm: DataManagerDep,
    at: AtTarget,
) -> None:
    """查询 jj 长度"""
    uid = event.get_user_id()

    # TODO 寄是干嘛的，添加注释

    target_id = int(at if at != "寄" else uid)
    pronoun = "你" if at == "寄" else "TA"

    if not await dm.is_in_table(target_id):
        await dm.add_new_user(target_id)
        await matcher.finish(
            QueryCopy(pronoun=pronoun, jj_name=pick_jj_alias()).create(),
            at_sender=True,
        )

    length = await dm.get_jj_length(target_id)
    prob = await dm.get_win_probability(target_id)

    if length <= 0:
        # 负值世界：显示深度（绝对值）
        nq = NegQueryCopy(
            pronoun=pronoun,
            hole_name=pick_hole_alias(),
            depth=abs(length),
            prob=prob,
        )
        msg = nq.abyss_lord() if abs(length) >= 30 else nq.girl()
    else:
        qc = QueryCopy(
            pronoun=pronoun, jj_name=pick_jj_alias(), length=length, prob=prob
        )
        if length >= 30:
            msg = qc.god()
        elif length > 5:
            msg = qc.normal()
        else:
            msg = qc.near_girl()

    await matcher.finish(msg, at_sender=True)


# endregion

# region 命令注册

query_matcher = on_command(
    "查询",
    priority=20,
    block=False,
    handlers=[group_enabled_check, query_handler],
)

# endregion
