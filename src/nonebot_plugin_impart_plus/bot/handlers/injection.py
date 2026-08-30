"""注入查询命令"""

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from .. import DataManagerDep, DrawChartDep
from ..dependencies import AtTarget
from .common import group_enabled_check

# region 事件处理函数


async def injection_handler(
    bot: Bot,
    matcher: Matcher,
    event: GroupMessageEvent,
    dm: DataManagerDep,
    chart: DrawChartDep,
    at: AtTarget,
    args: Message = CommandArg(),
) -> None:
    """查询注入量"""
    target_text = args.extract_plain_text()
    uid = event.get_user_id()

    if at != "寄":
        object_id = at
        label = "该用户"
    else:
        object_id = uid
        label = "您"

    data = await dm.get_ejaculation_data(int(object_id))

    if "历史" in target_text or "全部" in target_text:
        if not data:
            await matcher.finish(f"{label}历史总被注射量为0ml")

        inject_data: dict[str, float] = {}
        total = 0.0
        for item in data:
            total += item["volume"]
            inject_data[item["date"]] = item["volume"]

        if len(inject_data) < 2:
            await matcher.finish(f"{label}历史总被注射量为{total}ml")

        # 获取用户信息（昵称和头像）
        try:
            user_info = await bot.get_stranger_info(user_id=int(object_id))
            user_name = user_info["nickname"]
        except Exception:
            user_name = f"用户{object_id}"

        user_avatar = f"https://q1.qlogo.cn/g?b=qq&nk={object_id}&s=100"

        img_bytes = await chart.draw_line_chart(
            user_name=user_name,
            user_avatar=user_avatar,
            data=inject_data,
        )

        await matcher.finish(
            MessageSegment.text(f"{label}历史总被注射量为{total}ml")
            + MessageSegment.image(img_bytes)
        )
    else:
        ejaculation = await dm.get_today_ejaculation_data(int(object_id))
        await matcher.finish(f"{label}当日总被注射量为{ejaculation}ml")


# endregion

# region 命令注册

injection_matcher = on_command(
    "注入查询",
    aliases={"摄入查询", "射入查询"},
    priority=20,
    block=True,
    handlers=[group_enabled_check, injection_handler],
)

# endregion
