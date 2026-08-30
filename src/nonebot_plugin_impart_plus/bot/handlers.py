"""matcher的handle模块"""

import asyncio
import random
import time
from random import choice

from httpx import AsyncClient
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, RegexGroup

from ..infra.chart_renderer import draw_bar_chart
from ..infra.data_manager import (
    add_new_user,
    check_group_allow,
    get_ejaculation_data,
    get_jj_length,
    get_sorted,
    get_today_ejaculation_data,
    get_win_probability,
    insert_ejaculation,
    is_in_table,
    punish_all_inactive_users,
    set_group_allow,
    set_jj_length,
    set_win_probability,
    update_activity,
    update_challenge_status,
)
from .dependencies import cooldown, plugin_config

ban_id_set: set[str] = (
    set(plugin_config.ban_id_list.split(",")) if plugin_config.ban_id_list else set()
)
botname: str = next(iter(plugin_config.nickname), "BOT")


async def has_at(event: GroupMessageEvent) -> bool:
    msg = event.get_message()
    return next(
        (msg_seg.data["qq"] != "all" for msg_seg in msg if msg_seg.type == "at"),
        False,
    )


async def get_at(event: GroupMessageEvent) -> str:
    msg = event.get_message()
    return next(
        (
            "寄" if msg_seg.data["qq"] == "all" else str(msg_seg.data["qq"])
            for msg_seg in msg
            if msg_seg.type == "at"
        ),
        "寄",
    )


def get_random_num() -> float:
    rand_num = random.random()
    rand_num = random.uniform(0, 1) if rand_num > 0.1 else random.uniform(1, 2)
    return round(rand_num, 3)


async def get_stranger_info(client: AsyncClient, uid: int) -> str:
    try:
        resp = (await client.get(f"https://api.usuuu.com/qq/{uid}")).json()
        return resp["data"]["name"]
    except Exception:
        return "获取用户id失败"


class Impart:
    penalties_impact: bool = plugin_config.isalive  # 重置每日活跃度

    @staticmethod
    async def penalties_and_resets() -> None:
        """重置每日活跃度"""
        if Impart.penalties_impact:
            await punish_all_inactive_users()

    @staticmethod
    async def pk(matcher: Matcher, event: GroupMessageEvent) -> None:
        """pk的响应器"""
        await Impart.penalties_and_resets()
        if not await check_group_allow(event.group_id):
            await matcher.finish(plugin_config.not_allow, at_sender=True)

        uid: str = event.get_user_id()
        allow: bool = await cooldown.pkcd_check(uid)  # CD是否允许pk
        if not allow:  # 如果不允许pk, 则返回
            await matcher.finish(
                f"你已经pk不动了喵, 请等待{round(cooldown.pk_cd_time - (time.time() - cooldown.pk_cd_data[uid]), 3)}秒后再pk喵",
                at_sender=True,
            )

        cooldown.pk_cd_data.update({uid: time.time()})  # 更新CD时间
        at: str = await get_at(event)  # 获取at的id
        if at == uid:  # 如果at的id和uid相同, 则返回
            await matcher.finish("你不能pk自己喵", at_sender=True)

        # 执行pk逻辑
        if await is_in_table(userid=int(uid)) and await is_in_table(int(at)):
            random_num = random.random()
            win = random_num < await get_win_probability(userid=int(uid))
            random_num: float = get_random_num()  # 重新生成一个随机数
            length_increase = round(random_num / 2, 3)
            length_decrease = random_num
            if win:
                await set_win_probability(int(uid), -0.01)
                await set_win_probability(int(at), 0.01)
                await set_jj_length(int(uid), random_num / 2)
                await set_jj_length(int(at), -random_num)
                await Impart.handle_pk_win(
                    matcher, uid, at, length_increase, length_decrease
                )
            else:
                await set_win_probability(int(uid), 0.01)  # 己方，增加1%的获胜概率
                await set_win_probability(int(at), -0.01)  # 对方，减少1%的获胜概率
                await set_jj_length(int(uid), -random_num)
                await set_jj_length(int(at), random_num / 2)
                await Impart.handle_pk_loss(
                    matcher, uid, at, length_increase, length_decrease
                )
        else:
            # 创建新的用户
            if not await is_in_table(userid=int(uid)):
                await add_new_user(int(uid))
            if not await is_in_table(userid=int(at)):
                await add_new_user(int(at))
            del cooldown.pk_cd_data[uid]  # 删除CD时间
            await matcher.finish(
                f"你或对面还没有创建{choice(plugin_config.jj_variable)}喵, 咱全帮你创建了喵, 你们的{choice(plugin_config.jj_variable)}长度都是10cm喵",
                at_sender=True,
            )

    @staticmethod
    async def handle_pk_win(
        matcher: Matcher,
        uid: str,
        at: str,
        length_increase: float,
        length_decrease: float,
    ) -> None:
        """处理pk胜利逻辑"""
        # 检查 UID 达到25cm或30cm的条件
        uid_status = await update_challenge_status(int(uid))

        # 检查 AT 长度变化条件
        at_status = await update_challenge_status(int(at))

        # 设置基本消息模板
        uid_msg = f"对决胜利喵, 你的{choice(plugin_config.jj_variable)}增加了{length_increase}cm喵, 对面则在你的阴影笼罩下减小了{length_decrease}cm喵"

        # 根据 UID 调整消息
        if "challenge_started_low_win" in uid_status:
            uid_msg += (
                f"\n{botname}检测到你的{choice(plugin_config.jj_variable)}长度超过25cm，已为你开启✨“登神长阶”✨"
                f"\n你现在的获胜概率变为当前的80%，且无法使用“打胶”与“嗦”指令，请以将{choice(plugin_config.jj_variable)}长度提升至30cm为目标与他人pk吧!"
            )
        elif "challenge_success_high_win" in uid_status:
            uid_msg += (
                f"\n🎉恭喜你完成登神挑战🎉\n你的{choice(plugin_config.jj_variable)}长度已超过30cm，授予你🎊“牛々の神”🎊称号"
                f"\n你的获胜概率已恢复，“打胶”与“嗦”指令已重新开放，切记不忘初心，继续冲击更高的境界喵！"
            )

        # 根据 AT 调整消息
        if "challenge_failed_high_win" in at_status:
            uid_msg += (
                f"\n由于你对决的胜利，{botname}检测到TA的{choice(plugin_config.jj_variable)}长度已不足25cm，很遗憾，TA的登神挑战失败，{botname}替TA感谢你的鞭策喵！"
                f"\nTA的{choice(plugin_config.jj_variable)}长度缩短了5cm喵，获胜概率已恢复，“打胶”与“嗦”指令已重新开放喵！"
            )
        elif "challenge_completed_reduce" in at_status:
            uid_msg += (
                f"\n由于你对决的胜利，{botname}检测到TA的{choice(plugin_config.jj_variable)}长度已不足25cm，很遗憾，TA跌落神坛，{botname}替TA感谢你的鞭策喵！"
                f"\nTA的{choice(plugin_config.jj_variable)}长度缩短了5cm喵，请不忘初心，再次冲击更高的境界喵！"
            )
        elif "length_near_zero" in at_status:
            uid_msg += f"\n由于你对决的胜利，{botname}检测到TA已经变成xnn了喵！"
        elif "length_zero_or_negative" in at_status:
            uid_msg += f"\n由于你对决的胜利，{botname}检测到TA已经变成女孩子了喵！"

        probability_msg = (
            f"\n你的战力现在为{await get_win_probability(userid=int(uid)):.0%}喵"
        )

        await matcher.finish(f"{uid_msg}{probability_msg}", at_sender=True)

    @staticmethod
    async def handle_pk_loss(
        matcher: Matcher,
        uid: str,
        at: str,
        length_increase: float,
        length_decrease: float,
    ) -> None:
        """处理pk失败逻辑"""

        uid_status = await update_challenge_status(int(uid))
        at_status = await update_challenge_status(int(at))

        uid_msg = f"对决失败喵, 在对面{choice(plugin_config.jj_variable)}的阴影笼罩下你的{choice(plugin_config.jj_variable)}减小了{length_decrease}cm喵, 对面增加了{length_increase}cm喵"

        if "challenge_failed_high_win" in uid_status:
            uid_msg += (
                f"\n很遗憾，登神挑战失败，别气馁啦！"
                f"\n你的{choice(plugin_config.jj_variable)}长度缩短了5cm喵，获胜概率已恢复，“打胶”与“嗦”指令已重新开放喵！"
            )
        elif "challenge_completed_reduce" in uid_status:
            uid_msg += (
                f"\n很遗憾，你跌落神坛，别气馁啦！"
                f"\n你的{choice(plugin_config.jj_variable)}长度缩短了5cm喵，请不忘初心，再次冲击更高的境界喵！"
            )
        elif "length_near_zero" in uid_status:
            uid_msg += "\n你醒啦, 你已经变成xnn了！"
        elif "length_zero_or_negative" in uid_status:
            uid_msg += "\n你醒啦, 你已经变成女孩子了！"

        if "challenge_started_low_win" in at_status:
            uid_msg += (
                f"\n由于你对决的失败，触犯到了神秘的禁忌，{botname}检测到TA的{choice(plugin_config.jj_variable)}长度超过25cm，已为TA开启✨“登神长阶”✨"
                f"\n现在TA的获胜概率变为当前的80%，且无法使用“打胶”与“嗦”指令，请通知TA以将{choice(plugin_config.jj_variable)}长度提升至30cm为目标与群友pk吧！"
            )
        elif "challenge_success_high_win" in at_status:
            uid_msg += (
                f"\n🎉恭喜你帮助TA完成登神挑战🎉\nTA的{choice(plugin_config.jj_variable)}长度超过30cm，授予TA🎊“牛々の神”🎊称号"
                f"\nTA的获胜概率已恢复，“打胶”与“嗦”指令已重新开放，请提醒TA不忘初心，继续冲击更高的境界喵！"
            )

        probability_msg = (
            f"\n你的战力现在为{await get_win_probability(userid=int(uid)):.0%}喵"
        )

        await matcher.finish(f"{uid_msg}{probability_msg}", at_sender=True)

    @staticmethod
    async def dajiao(matcher: Matcher, event: GroupMessageEvent) -> None:
        """打胶的响应器"""
        await Impart.penalties_and_resets()
        # 检查群组权限
        if not await check_group_allow(event.group_id):
            await matcher.finish(plugin_config.not_allow, at_sender=True)
        # 获取用户ID
        uid: str = event.get_user_id()
        # 检查CD时间是否允许
        allow = await cooldown.cd_check(uid)
        if not allow:
            remaining_time = round(
                cooldown.dj_cd_time - (time.time() - cooldown.cd_data[uid]), 3
            )
            await matcher.finish(
                f"你已经打不动了喵, 请等待{remaining_time}秒后再打喵",
                at_sender=True,
            )
        # 更新CD时间
        cooldown.cd_data[uid] = time.time()

        # 检查用户数据
        if not await is_in_table(userid=int(uid)):
            await add_new_user(int(uid))  # 创建新用户
            await matcher.finish(
                f"你还没有创建{choice(plugin_config.jj_variable)}, 咱帮你创建了喵, 目前长度是10cm喵",
                at_sender=True,
            )
            return

        # 获取当前长度和随机数
        uid_length = await get_jj_length(int(uid))
        random_num = get_random_num()
        uid_status = await update_challenge_status(int(uid))

        # 牛子长度范围限制
        if "is_challenging" in uid_status:
            await matcher.finish(
                f"你的{choice(plugin_config.jj_variable)}长度在任务范围内，不允许打胶，请专心与群友pk！",
                at_sender=True,
            )
            return

        # 增长逻辑
        await set_jj_length(int(uid), random_num)
        new_length = await get_jj_length(int(uid))
        if uid_length < 25 <= new_length:
            await update_challenge_status(int(uid))
            await matcher.finish(
                f"打胶结束喵, 你的{choice(plugin_config.jj_variable)}很满意喵, 长了{random_num}cm喵"
                f"\n由于你无休止的打胶，触犯到了神秘的禁忌，{botname}检测到你的{choice(plugin_config.jj_variable)}长度超过25cm，已为你开启✨“登神长阶”✨"
                f"\n你现在的获胜概率变为当前的80%，且无法使用“打胶”与“嗦”指令，请以将{choice(plugin_config.jj_variable)}长度提升至30cm为目标与他人pk吧！",
                at_sender=True,
            )
        else:
            await matcher.finish(
                f"打胶结束喵, 你的{choice(plugin_config.jj_variable)}很满意喵, 长了{random_num}cm喵, 目前长度为{await get_jj_length(int(uid))}cm喵",
                at_sender=True,
            )

    @staticmethod
    async def suo(matcher: Matcher, event: GroupMessageEvent) -> None:
        """嗦牛子的响应器"""
        await Impart.penalties_and_resets()
        if not await check_group_allow(event.group_id):
            await matcher.finish(plugin_config.not_allow, at_sender=True)

        uid: str = event.get_user_id()

        allow = await cooldown.suo_cd_check(uid)
        if not allow:
            remaining_time = round(
                cooldown.suo_cd_time - (time.time() - cooldown.suo_cd_data[uid]),
                3,
            )
            await matcher.finish(
                f"你已经嗦不动了喵, 请等待{remaining_time}秒后再嗦喵",
                at_sender=True,
            )

        cooldown.suo_cd_data[uid] = time.time()
        # 获取at的用户ID
        at: str = await get_at(event)
        target_id = int(uid if at == "寄" else at)  # 如果没有at，则使用自己的uid
        pronoun = "你" if at == "寄" else "TA"  # 判断是自己还是被@用户

        if not await is_in_table(userid=target_id):
            await add_new_user(target_id)
            del cooldown.suo_cd_data[uid]  # 删除CD时间
            msg = f"{pronoun}还没有创建{choice(plugin_config.jj_variable)}喵, 咱帮{pronoun}创建了喵, 目前长度是10cm喵"
            await matcher.finish(msg, at_sender=True)
            return

        # 获取当前长度和随机数
        current_length = await get_jj_length(target_id)
        random_num = get_random_num()
        target_status = await update_challenge_status(target_id)

        if "is_challenging" in target_status:
            msg = f"{pronoun}的{choice(plugin_config.jj_variable)}长度在任务范围内，不准嗦！请专心与群友pk！"
            await matcher.finish(msg, at_sender=True)
            return

        # 增长逻辑
        await set_jj_length(target_id, random_num)
        new_length = await get_jj_length(target_id)
        if current_length < 25 <= new_length:
            await update_challenge_status(target_id)
            msg = (
                f"{pronoun}的{choice(plugin_config.jj_variable)}很满意喵, 嗦长了{random_num}cm喵"
                f"\n由于{pronoun}无休止的嗦与被嗦，触犯到了神秘的禁忌，{botname}检测到{pronoun}的{choice(plugin_config.jj_variable)}长度超过25cm，"
                f"\n已为{pronoun}开启✨“登神长阶”✨，{pronoun}现在的获胜概率变为80%，且无法使用“打胶”与“嗦”指令，请以将{choice(plugin_config.jj_variable)}长度提升至30cm为目标与他人pk吧！"
            )
            await matcher.finish(msg, at_sender=True)
        else:
            msg = f"{pronoun}的{choice(plugin_config.jj_variable)}很满意喵, 嗦长了{random_num}cm喵, 目前长度为{new_length}cm喵"
            await matcher.finish(msg, at_sender=True)

    @staticmethod
    async def queryjj(matcher: Matcher, event: GroupMessageEvent) -> None:
        """查询某人jj的响应器"""
        await Impart.penalties_and_resets()
        if not await check_group_allow(event.group_id):
            await matcher.finish(plugin_config.not_allow, at_sender=True)

        uid: str = event.get_user_id()
        at = await get_at(event)
        target_id = int(at if at != "寄" else uid)
        pronoun = "你" if at == "寄" else "TA"

        # 创建用户数据如果不存在
        if not await is_in_table(userid=target_id):
            await add_new_user(target_id)
            msg = f"{pronoun}还没有创建{choice(plugin_config.jj_variable)}喵, 咱帮{pronoun}创建了喵, 目前长度是10cm喵"
            await matcher.finish(msg, at_sender=True)

        length = await get_jj_length(target_id)

        # 根据不同的长度范围生成响应消息
        if length >= 30:
            msg = f"✨牛々の神✨\n{pronoun}的{choice(plugin_config.jj_variable)}目前长度为{length}cm喵"
        elif 30 > length > 5:
            msg = (
                f"{pronoun}的{choice(plugin_config.jj_variable)}目前长度为{length}cm喵"
            )
        elif 5 >= length > 1:
            msg = f"{pronoun}已经是xnn啦！\n{pronoun}的{choice(plugin_config.jj_variable)}目前长度为{length}cm喵"
        elif 1 >= length > 0:
            msg = f"{pronoun}快要变成女孩子啦！\n{pronoun}的{choice(plugin_config.jj_variable)}目前长度为{length}cm喵"
        else:
            msg = f"{pronoun}已经是女孩子啦！\n{pronoun}的{choice(plugin_config.jj_variable)}目前长度为{length}cm喵"

        await matcher.finish(msg, at_sender=True)

    @staticmethod
    async def jjrank(bot: Bot, matcher: Matcher, event: GroupMessageEvent) -> None:
        """输出前五后五和自己的排名"""
        if not await check_group_allow(event.group_id):
            await matcher.finish(plugin_config.not_allow, at_sender=True)
        uid: int = event.user_id
        rankdata: list[dict] = await get_sorted()
        if len(rankdata) < 5:
            await matcher.finish("目前记录的数据量小于5, 无法显示rank喵")
        top5: list = rankdata[:5]  # 取前5
        last5: list = rankdata[-5:]  # 取后5
        # 获取自己的排名
        index: list = [i for i in range(len(rankdata)) if rankdata[i]["userid"] == uid]
        if not index:  # 如果用户没有创建JJ
            await add_new_user(uid)
            await matcher.finish(
                f"你还没有创建{choice(plugin_config.jj_variable)}看不到rank喵, 咱帮你创建了喵, 目前长度是10cm喵",
                at_sender=True,
            )
        # top5和end5的信息，然后获取其网名
        top5info = [
            await bot.get_stranger_info(user_id=name["userid"]) for name in top5
        ]
        last5info = [
            await bot.get_stranger_info(user_id=name["userid"]) for name in last5
        ]

        top5names = [name["nickname"] for name in top5info]
        last5names = [name["nickname"] for name in last5info]

        data = {top5names[i]: top5[i]["jj_length"] for i in range(len(top5))}
        for i in range(len(last5)):
            data[last5names[i]] = last5[i]["jj_length"]
        img_bytes = await draw_bar_chart.draw_bar_chart(data)
        reply2 = f"你的排名为{index[0] + 1}喵"
        await matcher.finish(MessageSegment.image(img_bytes) + reply2, at_sender=True)

    @staticmethod
    async def yinpa_prehandle(
        bot: Bot,
        args: tuple,
        matcher: Matcher,
        event: GroupMessageEvent,
    ) -> tuple[int, str, str, list]:
        """透群员的预处理环节"""
        await Impart.penalties_and_resets()
        gid, uid = event.group_id, event.user_id
        if not await check_group_allow(event.group_id):
            await matcher.finish(plugin_config.not_allow, at_sender=True)
        allow = await cooldown.fuck_cd_check(str(uid))  # CD检查是否允许
        if not allow:
            await matcher.finish(
                f"你已经榨不出来任何东西了, 请先休息{round(cooldown.fuck_cd_time - (time.time() - cooldown.ejaculation_cd[str(uid)]), 3)}秒",
                at_sender=True,
            )
        cooldown.ejaculation_cd.update({str(uid): time.time()})  # 记录时间
        req_user_card: str = str(event.sender.card or event.sender.nickname)
        prep_list = await bot.get_group_member_list(group_id=gid)
        return uid, req_user_card, args[0], prep_list

    @staticmethod
    async def yinpa_member_handle(
        prep_list: list,
        req_user_card: str,
        matcher: Matcher,
        event: GroupMessageEvent,
        random_nn: float,  # 添加 random_nn 参数
    ) -> str:
        prep_list = [prep.get("user_id", 123456) for prep in prep_list]  # 群友列表
        target = await get_at(event)  # 获取消息有没有at
        uid = event.user_id  # 获取当前用户ID

        if target == "寄":  # 没有@对象
            # 随机抽取幸运成员
            prep_list = [
                user for user in prep_list if str(user) not in ban_id_set
            ]  # 排除QQ号列表中的用户
            if not prep_list:  # 如果排除后没有有效用户
                prep_list = [
                    user for user in prep_list if str(user) in ban_id_set
                ]  # 从排除的用户中抽取

            if uid in prep_list:
                prep_list.remove(uid)  # 移除当前用户

            lucky_user = choice(prep_list)
            jj_length = await get_jj_length(int(uid))

            if jj_length > 5:
                await matcher.send(
                    f"现在咱将随机抽取一位幸运群友\n送给{req_user_card}色色！"
                )
            elif 5 >= jj_length > 0:
                if random_nn < 0.5:  # 50%概率
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
        else:  # 有@对象
            lucky_user = target

        return lucky_user

    @staticmethod
    async def yinpa_owner_handle(
        uid: int,
        prep_list: list,
        req_user_card: str,
        matcher: Matcher,
        random_nn: float,  # 添加 random_nn 参数
    ) -> str:
        lucky_user: str = next(
            (prep["user_id"] for prep in prep_list if prep["role"] == "owner"),
            str(uid),
        )
        if int(lucky_user) == uid:  # 如果群主是自己
            del cooldown.ejaculation_cd[str(uid)]
            await matcher.finish("你透你自己?")

        jj_length = await get_jj_length(uid)
        if jj_length <= 0:
            await matcher.send(
                f"唔...你透不了哦~\n现在咱将{req_user_card}\n送给群主色色！"
            )
        elif 5 >= jj_length > 0 and random_nn < 0.5:
            await matcher.send(
                f"{botname}发现你是xnn~现在咱将{req_user_card}\n送给群主色色！"
            )
        else:
            await matcher.send(f"现在咱将把群主\n送给{req_user_card}色色！")

        return lucky_user

    @staticmethod
    async def yinpa_admin_handle(
        uid: int,
        prep_list: list,
        req_user_card: str,
        matcher: Matcher,
        random_nn: float,  # 添加 random_nn 参数
    ) -> str:
        admin_id: list = [
            prep["user_id"]
            for prep in prep_list
            if prep["role"] == "admin" and str(prep["user_id"]) not in ban_id_set
        ]
        if not admin_id:  # 如果排除后没有有效用户
            admin_id = [
                prep["user_id"]
                for prep in prep_list
                if prep["role"] == "admin" and str(prep["user_id"]) in ban_id_set
            ]  # 从排除的用户中抽取

        if uid in admin_id:  # 如果自己是管理的话， 移除自己
            admin_id.remove(uid)
        if not admin_id:  # 如果没有管理的话, del cd信息， 然后finish
            del cooldown.ejaculation_cd[str(uid)]
            await matcher.finish("喵喵喵? 找不到群管理!")

        lucky_user: str = choice(admin_id)  # random抽取一个管理
        jj_length = await get_jj_length(uid)

        if jj_length <= 0:
            await matcher.send(
                f"唔...你透不了哦~\n现在咱将{req_user_card}\n送给随机一位管理色色！"
            )
        elif 5 >= jj_length > 0 and random_nn < 0.5:
            await matcher.send(
                f"{botname}发现你是xnn~现在咱将{req_user_card}\n送给随机一位管理色色！"
            )
        else:
            await matcher.send(
                f"现在咱将随机抽取一位幸运管理\n送给{req_user_card}色色！"
            )

        return lucky_user

    async def yinpa_identity_handle(
        self,
        command: str,
        prep_list: list,
        req_user_card: str,
        matcher: Matcher,
        event: GroupMessageEvent,
        random_nn: float,  # 添加 random_nn 参数
    ) -> str:
        uid: int = event.user_id
        if "群主" in command:  # 如果发送的命令里面含有群主， 说明在透群主
            return await self.yinpa_owner_handle(
                uid, prep_list, req_user_card, matcher, random_nn
            )
        elif "管理" in command:  # 如果发送的命令里面含有管理， 说明在透管理
            return await self.yinpa_admin_handle(
                uid, prep_list, req_user_card, matcher, random_nn
            )
        else:  # 最后是群员
            return await self.yinpa_member_handle(
                prep_list, req_user_card, matcher, event, random_nn
            )

    async def yinpa(
        self,
        bot: Bot,
        matcher: Matcher,
        event: GroupMessageEvent,
        args: tuple = RegexGroup(),
    ) -> None:
        if not await check_group_allow(event.group_id):
            await matcher.finish(plugin_config.not_allow, at_sender=True)
        uid, req_user_card, command, prep_list = await self.yinpa_prehandle(
            matcher=matcher, bot=bot, args=args, event=event
        )

        random_nn = random.uniform(0, 1)  # 生成一个随机数

        lucky_user: str = await self.yinpa_identity_handle(
            command=command,
            prep_list=prep_list,
            req_user_card=req_user_card,
            matcher=matcher,
            event=event,
            random_nn=random_nn,  # 传递 random_nn
        )

        lucky_user_card = next(
            (
                prep["card"] or prep["nickname"]
                for prep in prep_list
                if prep["user_id"] == int(lucky_user)
            ),
            "群友",
        )

        await asyncio.sleep(2)  # 休眠2秒, 更有效果
        await update_activity(int(lucky_user))  # 更新活跃度
        await update_activity(uid)  # 更新活跃度

        # 检查await get_jj_length的返回值并确定好要发送的消息
        jj_length = await get_jj_length(uid)
        if jj_length <= 0 or (5 >= jj_length > 0 and random_nn < 0.5):
            # 1--100的随机数， 保留三位
            ejaculation = round(random.uniform(1, 100), 3)
            await insert_ejaculation(int(uid), ejaculation)
            # 互换req_user_card与lucky_user_card
            repo_1 = f"好欸！{lucky_user_card}({lucky_user})用时{random.randint(1, 20)}秒 \n给 {req_user_card}({uid}) 注入了{ejaculation}毫升的脱氧核糖核酸, 当日总注入量为：{await get_today_ejaculation_data(int(uid))}毫升\n"
        else:
            # 1--100的随机数， 保留三位
            ejaculation = round(random.uniform(1, 100), 3)
            await insert_ejaculation(int(lucky_user), ejaculation)
            repo_1 = f"好欸！{req_user_card}({uid})用时{random.randint(1, 20)}秒 \n给 {lucky_user_card}({lucky_user}) 注入了{ejaculation}毫升的脱氧核糖核酸, 当日总注入量为：{await get_today_ejaculation_data(int(lucky_user))}毫升\n"

        await matcher.send(
            repo_1
            + MessageSegment.image(f"https://q1.qlogo.cn/g?b=qq&nk={lucky_user}&s=640")
        )  # 结束

    @staticmethod
    async def open_module(
        matcher: Matcher, event: GroupMessageEvent, args: tuple = RegexGroup()
    ) -> None:
        """开关"""
        gid: int = event.group_id
        command: str = args[0]
        if "开启" in command or "开始" in command:
            await set_group_allow(gid, True)
            await matcher.finish("功能已开启喵")
        elif "禁止" in command or "关闭" in command:
            await set_group_allow(gid, False)
            await matcher.finish("功能已禁用喵")

    @staticmethod
    async def query_injection(
        matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()
    ) -> None:
        """查询某人的注入量"""
        await Impart.penalties_and_resets()
        if not await check_group_allow(event.group_id):
            await matcher.finish(plugin_config.not_allow, at_sender=True)
        target = args.extract_plain_text()  # 获取命令参数
        user_id: str = event.get_user_id()
        # 判断带不带at
        [object_id, replay1] = (
            [await get_at(event), "该用户"]
            if await get_at(event) != "寄"
            else [user_id, "您"]
        )
        #  获取用户的所有注入数据
        data: list[dict] = await get_ejaculation_data(int(object_id))
        ejaculation = 0  # 先初始化0
        if "历史" in target or "全部" in target:
            if not data:
                await matcher.finish(f"{replay1}历史总被注射量为0ml")
            inject_data = {}
            for item in data:  # 遍历所有的日期
                temp: float = item["volume"]  # 获取注入量
                ejaculation += temp  # 注入量求和
                date: str = item["date"]  # 获取日期
                inject_data[date] = temp
            if len(inject_data) < 2:
                await matcher.finish(f"{replay1}历史总被注射量为{ejaculation}ml")

            await matcher.finish(
                MessageSegment.text(f"{replay1}历史总被注射量为{ejaculation}ml")
                + MessageSegment.image(
                    await draw_bar_chart.draw_line_chart(inject_data)
                )
            )
        else:
            ejaculation: float = await get_today_ejaculation_data(int(object_id))
            await matcher.finish(f"{replay1}当日总被注射量为{ejaculation}ml")

    @staticmethod
    async def yinpa_introduce(matcher: Matcher) -> None:
        """输出用法"""
        usage_text = plugin_config.usage
        await matcher.send(MessageSegment.text(usage_text))


impart = Impart()
