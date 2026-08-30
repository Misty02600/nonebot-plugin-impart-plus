"""排行榜命令"""

from re import I

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageSegment
from nonebot.matcher import Matcher

from .. import DataManagerDep, DrawChartDep
from ..dependencies import pick_jj_alias
from .common import group_enabled_check

# region 事件处理函数


async def rank_handler(
    bot: Bot,
    matcher: Matcher,
    event: GroupMessageEvent,
    dm: DataManagerDep,
    chart: DrawChartDep,
) -> None:
    """输出前五后五和自己的排名"""
    uid = event.user_id
    rankdata = await dm.get_sorted_users()

    if len(rankdata) < 5:
        await matcher.finish("目前记录的数据量小于5, 无法显示rank喵")

    index = [i for i in range(len(rankdata)) if rankdata[i]["userid"] == uid]

    if not index:
        await dm.add_new_user(uid)
        await matcher.finish(
            f"你还没有创建{pick_jj_alias()}看不到rank喵, 咱帮你创建了喵, 目前长度是10cm喵",
            at_sender=True,
        )

    user_rank = index[0] + 1  # 1-indexed
    total_count = len(rankdata)
    user_idx = index[0]

    # 收集需要展示的用户索引（set 天然去重，避免人数 < 10 时 top5/bottom5 重叠）
    display_indices: set[int] = set()

    # 前 5 名
    for i in range(min(5, total_count)):
        display_indices.add(i)

    # 倒数 5 名
    for i in range(max(0, total_count - 5), total_count):
        display_indices.add(i)

    # 如果用户不在前5/后5，添加其上下各 1 位
    if user_rank > 5 and user_rank <= total_count - 5:
        start_idx = max(0, user_idx - 1)
        end_idx = min(total_count, user_idx + 2)
        for i in range(start_idx, end_idx):
            display_indices.add(i)

    # 批量获取用户信息（昵称+头像）
    user_info_map: dict[int, dict[str, str]] = {}
    for idx in display_indices:
        uid_to_query = rankdata[idx]["userid"]
        if uid_to_query in user_info_map:
            continue
        try:
            info = await bot.get_stranger_info(user_id=uid_to_query)
            user_info_map[uid_to_query] = {
                "nickname": info["nickname"],
                "avatar_url": f"https://q1.qlogo.cn/g?b=qq&nk={uid_to_query}&s=100",
            }
        except Exception:
            user_info_map[uid_to_query] = {
                "nickname": f"用户{uid_to_query}",
                "avatar_url": f"https://q1.qlogo.cn/g?b=qq&nk={uid_to_query}&s=100",
            }

    # 按排名顺序构建去重后的数据列表
    rank_entries = []
    for idx in sorted(display_indices):
        user = rankdata[idx]
        user_id = user["userid"]
        info = user_info_map[user_id]
        rank_entries.append(
            (
                idx + 1,
                str(user_id),
                info["nickname"],
                info["avatar_url"],
                user["jj_length"],
            )
        )

    # 渲染图表
    img_bytes = await chart.draw_bar_chart(
        rank_data=rank_entries,
        user_rank=user_rank,
        user_id=str(uid),
        total=total_count,
    )
    reply = f"你的排名为{user_rank}喵"
    await matcher.finish(MessageSegment.image(img_bytes) + reply, at_sender=True)


# endregion

# region 命令注册

rank_matcher = on_regex(
    r"^(银趴|impart)(排行榜|排名|榜单|rank)",
    flags=I,
    priority=20,
    block=True,
    handlers=[group_enabled_check, rank_handler],
)

# endregion
