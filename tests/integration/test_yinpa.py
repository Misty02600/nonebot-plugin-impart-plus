"""银趴（透群友 / 榨群友）— 端到端 matcher 测试。

TargetCtx 需要调用 bot.get_group_member_list，须用
ctx.should_call_api 声明模拟返回。execute_tou / execute_zha
含 asyncio.sleep(2) 须 patch 掉。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

# TargetCtx DI 需要 OB11 Bot 实例（有 get_group_member_list 方法）
from nonebot.adapters.onebot.v11 import Bot as OB11Bot
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebug import App
from tests.fake import fake_group_message_event_v11

from .conftest import ANY_MSG, GROUP_ID, TARGET_ID, USER_ID

MEMBER_LIST = [
    {
        "user_id": USER_ID,
        "nickname": "TestUser",
        "card": "测试用户",
        "role": "member",
        "sex": "male",
    },
    {
        "user_id": TARGET_ID,
        "nickname": "TargetUser",
        "card": "目标用户",
        "role": "member",
        "sex": "male",
    },
    {
        "user_id": 22222222,
        "nickname": "Owner",
        "card": "群主大人",
        "role": "owner",
        "sex": "male",
    },
]


def _tou_event(msg: str = "透群友"):
    return fake_group_message_event_v11(
        user_id=USER_ID,
        group_id=GROUP_ID,
        message=Message(msg),
        raw_message=msg,
    )


def _zha_event(msg: str = "榨群友"):
    return fake_group_message_event_v11(
        user_id=USER_ID,
        group_id=GROUP_ID,
        message=Message(msg),
        raw_message=msg,
    )


def _zha_at_event(msg: str = "榨群友", at_qq: str = str(TARGET_ID)):
    segments = MessageSegment.text(msg + " ") + MessageSegment.at(at_qq)
    return fake_group_message_event_v11(
        user_id=USER_ID,
        group_id=GROUP_ID,
        message=Message(segments),
        raw_message=msg,
    )


def _tou_at_event(msg: str = "透群友", at_qq: str = str(TARGET_ID)):
    segments = MessageSegment.text(msg + " ") + MessageSegment.at(at_qq)
    return fake_group_message_event_v11(
        user_id=USER_ID,
        group_id=GROUP_ID,
        message=Message(segments),
        raw_message=msg,
    )


@pytest.mark.asyncio(loop_scope="session")
async def test_tou_positive_normal(app: App, fresh_env):
    """透群友 — 正值玩家正常执行。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 10.0)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 10.0)

    from nonebot_plugin_impart_plus.bot.handlers.yinpa import yinpa_matcher

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.yinpa.asyncio.sleep",
        new_callable=AsyncMock,
    ):
        async with app.test_matcher(yinpa_matcher) as ctx:
            bot = ctx.create_bot(base=OB11Bot)
            event = _tou_event()
            ctx.receive_event(bot, event)
            # get_group_member_list 来自 TargetCtx DI
            ctx.should_call_api(
                "get_group_member_list",
                {"group_id": GROUP_ID},
                result=MEMBER_LIST,
            )
            # execute_tou 发两条消息：菜单 + 结算报告
            ctx.should_call_send(event, ANY_MSG, result=None)
            ctx.should_call_send(event, ANY_MSG, result=None)


@pytest.mark.asyncio(loop_scope="session")
async def test_tou_negative_blocked(app: App, fresh_env):
    """透群友 — 负值玩家被阵营守卫阻断。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, -5.0)

    from nonebot_plugin_impart_plus.bot.handlers.yinpa import yinpa_matcher

    async with app.test_matcher(yinpa_matcher) as ctx:
        bot = ctx.create_bot(base=OB11Bot)
        event = _tou_event()
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
        ctx.should_finished(yinpa_matcher)


@pytest.mark.asyncio(loop_scope="session")
async def test_tou_cd_blocks(app: App, fresh_env):
    """透群友 — CD 内无法二次操作。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 10.0)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 10.0)

    from nonebot_plugin_impart_plus.bot.handlers.yinpa import yinpa_matcher

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.yinpa.asyncio.sleep",
        new_callable=AsyncMock,
    ):
        # 第一次成功
        async with app.test_matcher(yinpa_matcher) as ctx:
            bot = ctx.create_bot(base=OB11Bot)
            event = _tou_event()
            ctx.receive_event(bot, event)
            ctx.should_call_api(
                "get_group_member_list",
                {"group_id": GROUP_ID},
                result=MEMBER_LIST,
            )
            ctx.should_call_send(event, ANY_MSG, result=None)
            ctx.should_call_send(event, ANY_MSG, result=None)

        # 第二次被 CD 挡住
        async with app.test_matcher(yinpa_matcher) as ctx:
            bot = ctx.create_bot(base=OB11Bot)
            event = _tou_event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
            ctx.should_finished(yinpa_matcher)


@pytest.mark.asyncio(loop_scope="session")
async def test_zha_negative_normal(app: App, fresh_env):
    """榨群友 — 负值玩家正常执行，目标为正值。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, -5.0)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 10.0)

    from nonebot_plugin_impart_plus.bot.handlers.yinpa import zha_matcher

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.yinpa.asyncio.sleep",
        new_callable=AsyncMock,
    ):
        async with app.test_matcher(zha_matcher) as ctx:
            bot = ctx.create_bot(base=OB11Bot)
            event = _zha_event()
            ctx.receive_event(bot, event)
            ctx.should_call_api(
                "get_group_member_list",
                {"group_id": GROUP_ID},
                result=MEMBER_LIST,
            )
            # execute_zha 发两条消息：菜单 + 结算报告
            ctx.should_call_send(event, ANY_MSG, result=None)
            ctx.should_call_send(event, ANY_MSG, result=None)


@pytest.mark.asyncio(loop_scope="session")
async def test_zha_positive_blocked(app: App, fresh_env):
    """榨群友 — 正值玩家被阵营守卫阻断。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 10.0)
    from nonebot_plugin_impart_plus.bot.handlers.yinpa import zha_matcher

    async with app.test_matcher(zha_matcher) as ctx:
        bot = ctx.create_bot(base=OB11Bot)
        event = _zha_event()
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
        ctx.should_finished(zha_matcher)


@pytest.mark.asyncio(loop_scope="session")
async def test_zha_member_at_target(app: App, fresh_env):
    """榨群友 + @ 指定目标应命中 matcher 并正常执行。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, -5.0)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 10.0)

    from nonebot_plugin_impart_plus.bot.handlers.yinpa import zha_matcher

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.yinpa.asyncio.sleep",
        new_callable=AsyncMock,
    ):
        async with app.test_matcher(zha_matcher) as ctx:
            bot = ctx.create_bot(base=OB11Bot)
            event = _zha_at_event()
            ctx.receive_event(bot, event)
            ctx.should_call_api(
                "get_group_member_list",
                {"group_id": GROUP_ID},
                result=MEMBER_LIST,
            )
            ctx.should_call_send(event, ANY_MSG, result=None)
            ctx.should_call_send(event, ANY_MSG, result=None)


@pytest.mark.asyncio(loop_scope="session")
async def test_tou_admin_at_allowed(app: App, fresh_env):
    """透管理 + @ 可触发，且目标依然按管理随机选择。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 10.0)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 10.0)

    admin_member_list = [
        {
            "user_id": USER_ID,
            "nickname": "TestUser",
            "card": "测试用户",
            "role": "member",
            "sex": "male",
        },
        {
            "user_id": TARGET_ID,
            "nickname": "TargetUser",
            "card": "目标用户",
            "role": "admin",
            "sex": "male",
        },
        {
            "user_id": 22222222,
            "nickname": "Owner",
            "card": "群主大人",
            "role": "owner",
            "sex": "male",
        },
    ]

    from nonebot_plugin_impart_plus.bot.handlers.yinpa import yinpa_admin_matcher

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.yinpa.asyncio.sleep",
        new_callable=AsyncMock,
    ):
        async with app.test_matcher(yinpa_admin_matcher) as ctx:
            bot = ctx.create_bot(base=OB11Bot)
            event = _tou_at_event("透管理")
            ctx.receive_event(bot, event)
            ctx.should_call_api(
                "get_group_member_list",
                {"group_id": GROUP_ID},
                result=admin_member_list,
            )
            ctx.should_call_send(event, ANY_MSG, result=None)
            ctx.should_call_send(event, ANY_MSG, result=None)


@pytest.mark.asyncio(loop_scope="session")
async def test_zha_owner_at_allowed(app: App, fresh_env):
    """榨群主 + @ 可触发，且目标依然固定群主。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, -5.0)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 10.0)

    from nonebot_plugin_impart_plus.bot.handlers.yinpa import zha_owner_matcher

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.yinpa.asyncio.sleep",
        new_callable=AsyncMock,
    ):
        async with app.test_matcher(zha_owner_matcher) as ctx:
            bot = ctx.create_bot(base=OB11Bot)
            event = _zha_at_event("榨群主")
            ctx.receive_event(bot, event)
            ctx.should_call_api(
                "get_group_member_list",
                {"group_id": GROUP_ID},
                result=MEMBER_LIST,
            )
            ctx.should_call_send(event, ANY_MSG, result=None)
            ctx.should_call_send(event, ANY_MSG, result=None)


@pytest.mark.asyncio(loop_scope="session")
async def test_tou_ri_alias(app: App, fresh_env):
    """日群友 — "日" 前缀别名可触发。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 10.0)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 10.0)

    from nonebot_plugin_impart_plus.bot.handlers.yinpa import yinpa_matcher

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.yinpa.asyncio.sleep",
        new_callable=AsyncMock,
    ):
        async with app.test_matcher(yinpa_matcher) as ctx:
            bot = ctx.create_bot(base=OB11Bot)
            event = _tou_event("日群友")
            ctx.receive_event(bot, event)
            ctx.should_call_api(
                "get_group_member_list",
                {"group_id": GROUP_ID},
                result=MEMBER_LIST,
            )
            ctx.should_call_send(event, ANY_MSG, result=None)
            ctx.should_call_send(event, ANY_MSG, result=None)


@pytest.mark.asyncio(loop_scope="session")
async def test_zha_tou_share_cd(app: App, fresh_env):
    """榨群友 和 透群友 共享 fuck CD。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, -5.0)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 10.0)

    from nonebot_plugin_impart_plus.bot.handlers.yinpa import yinpa_matcher, zha_matcher

    # 先榨群友
    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.yinpa.asyncio.sleep",
        new_callable=AsyncMock,
    ):
        async with app.test_matcher(zha_matcher) as ctx:
            bot = ctx.create_bot(base=OB11Bot)
            event = _zha_event()
            ctx.receive_event(bot, event)
            ctx.should_call_api(
                "get_group_member_list",
                {"group_id": GROUP_ID},
                result=MEMBER_LIST,
            )
            ctx.should_call_send(event, ANY_MSG, result=None)
            ctx.should_call_send(event, ANY_MSG, result=None)

    # 把 USER 改为正值，再透群友 → 应被 CD 挡住
    await dm.set_jj_length_absolute(USER_ID, 10.0)

    async with app.test_matcher(yinpa_matcher) as ctx:
        bot = ctx.create_bot(base=OB11Bot)
        event = _tou_event()
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
        ctx.should_finished(yinpa_matcher)


@pytest.mark.asyncio(loop_scope="session")
async def test_zha_target_negative_blocked(app: App, fresh_env):
    """榨群友 — 目标也在负值世界 → positive_target_guard 阻断。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, -5.0)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, -3.0)

    from nonebot_plugin_impart_plus.bot.handlers.yinpa import zha_matcher

    # 固定随机选择 → 确保选中 TARGET_ID（负值用户）
    with patch(
        "nonebot_plugin_impart_plus.bot.dependencies.random.choice",
        return_value=TARGET_ID,
    ):
        async with app.test_matcher(zha_matcher) as ctx:
            bot = ctx.create_bot(base=OB11Bot)
            event = _zha_event()
            ctx.receive_event(bot, event)
            # 目标被随机选中后发现是负值 → 阻断
            ctx.should_call_api(
                "get_group_member_list",
                {"group_id": GROUP_ID},
                result=MEMBER_LIST,
            )
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
            ctx.should_finished(zha_matcher)


@pytest.mark.asyncio(loop_scope="session")
async def test_tou_qunzhu_variant(app: App, fresh_env):
    """透群主 — "透群主" 作为子命令可触发。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 10.0)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 10.0)

    from nonebot_plugin_impart_plus.bot.handlers.yinpa import yinpa_owner_matcher

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.yinpa.asyncio.sleep",
        new_callable=AsyncMock,
    ):
        async with app.test_matcher(yinpa_owner_matcher) as ctx:
            bot = ctx.create_bot(base=OB11Bot)
            event = _tou_event("透群主")
            ctx.receive_event(bot, event)
            ctx.should_call_api(
                "get_group_member_list",
                {"group_id": GROUP_ID},
                result=MEMBER_LIST,
            )
            ctx.should_call_send(event, ANY_MSG, result=None)
            ctx.should_call_send(event, ANY_MSG, result=None)


# ══════════════════════════════════════════════════════
# 雌堕事件
# ══════════════════════════════════════════════════════


@pytest.mark.asyncio(loop_scope="session")
async def test_tou_ciduo_trigger(app: App, fresh_env):
    """透群友 — 目标处于 xnn 且当日累计注入 >=500ml → 触发雌堕（长度 -5）。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 10.0)

    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 3.0)  # xnn: 0 < L <= 5
    # 预注入 450ml（差 50ml 就够）→ 本次注入会超过 500ml 阈值
    await dm.insert_ejaculation(TARGET_ID, 450.0)

    from nonebot_plugin_impart_plus.bot.handlers.yinpa import yinpa_matcher

    # 仅 USER + TARGET → _select_member 必然选中 TARGET
    two_person_list = [
        {
            "user_id": USER_ID,
            "nickname": "TestUser",
            "card": "测试用户",
            "role": "member",
            "sex": "male",
        },
        {
            "user_id": TARGET_ID,
            "nickname": "TargetUser",
            "card": "目标用户",
            "role": "member",
            "sex": "male",
        },
    ]

    # 固定注入量为 60ml → 总计 510ml >= 500ml 阈值
    with (
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.yinpa.asyncio.sleep",
            new_callable=AsyncMock,
        ),
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.yinpa.random.uniform",
            return_value=60.0,
        ),
    ):
        async with app.test_matcher(yinpa_matcher) as ctx:
            bot = ctx.create_bot(base=OB11Bot)
            event = _tou_event()
            ctx.receive_event(bot, event)
            ctx.should_call_api(
                "get_group_member_list",
                {"group_id": GROUP_ID},
                result=two_person_list,
            )
            # execute_tou: 菜单 + 结算报告（含雌堕播报）
            ctx.should_call_send(event, ANY_MSG, result=None)
            ctx.should_call_send(event, ANY_MSG, result=None)

    # 雌堕后: 3 - 5 = -2（进入负值世界）
    assert await dm.get_jj_length(TARGET_ID) == pytest.approx(-2.0, abs=0.01)


# ══════════════════════════════════════════════════════
# xnn 变体透
# ══════════════════════════════════════════════════════


@pytest.mark.asyncio(loop_scope="session")
async def test_tou_xnn_reversed(app: App, fresh_env):
    """透群友 — xnn 玩家透群友 → 被反透（目标注入发起者）。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 3.0)  # xnn
    await dm.update_challenge_status(USER_ID)  # 标记 is_near_zero

    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 15.0)  # 正常正值

    # 仅 USER + TARGET → _select_member 必然选中 TARGET
    two_person_list = [
        {
            "user_id": USER_ID,
            "nickname": "TestUser",
            "card": "测试用户",
            "role": "member",
            "sex": "male",
        },
        {
            "user_id": TARGET_ID,
            "nickname": "TargetUser",
            "card": "目标用户",
            "role": "member",
            "sex": "male",
        },
    ]

    from nonebot_plugin_impart_plus.bot.handlers.yinpa import yinpa_matcher

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.yinpa.asyncio.sleep",
        new_callable=AsyncMock,
    ):
        async with app.test_matcher(yinpa_matcher) as ctx:
            bot = ctx.create_bot(base=OB11Bot)
            event = _tou_event()
            ctx.receive_event(bot, event)
            ctx.should_call_api(
                "get_group_member_list",
                {"group_id": GROUP_ID},
                result=two_person_list,
            )
            # 菜单（xnn反转） + 结算报告
            ctx.should_call_send(event, ANY_MSG, result=None)
            ctx.should_call_send(event, ANY_MSG, result=None)


@pytest.mark.asyncio(loop_scope="session")
async def test_tou_xnn_both(app: App, fresh_env):
    """透群友 — 双方都是 xnn → 互透结算。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 3.0)  # xnn
    await dm.update_challenge_status(USER_ID)

    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 4.0)  # xnn
    await dm.update_challenge_status(TARGET_ID)

    # 仅 USER + TARGET, 去掉 owner → _select_member 必然选中 TARGET
    two_person_list = [
        {
            "user_id": USER_ID,
            "nickname": "TestUser",
            "card": "测试用户",
            "role": "member",
            "sex": "male",
        },
        {
            "user_id": TARGET_ID,
            "nickname": "TargetUser",
            "card": "目标用户",
            "role": "member",
            "sex": "male",
        },
    ]

    from nonebot_plugin_impart_plus.bot.handlers.yinpa import yinpa_matcher

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.yinpa.asyncio.sleep",
        new_callable=AsyncMock,
    ):
        async with app.test_matcher(yinpa_matcher) as ctx:
            bot = ctx.create_bot(base=OB11Bot)
            event = _tou_event()
            ctx.receive_event(bot, event)
            ctx.should_call_api(
                "get_group_member_list",
                {"group_id": GROUP_ID},
                result=two_person_list,
            )
            ctx.should_call_send(event, ANY_MSG, result=None)
            ctx.should_call_send(event, ANY_MSG, result=None)


@pytest.mark.asyncio(loop_scope="session")
async def test_tou_xnn_squeeze_female(app: App, fresh_env):
    """透群友 — xnn 透女性目标 → squeeze 结算（榨到腿软）。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 3.0)  # xnn
    await dm.update_challenge_status(USER_ID)

    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 15.0)  # 正值，非 xnn

    female_member_list = [
        {
            "user_id": USER_ID,
            "nickname": "TestUser",
            "card": "测试用户",
            "role": "member",
            "sex": "male",
        },
        {
            "user_id": TARGET_ID,
            "nickname": "TargetUser",
            "card": "目标用户",
            "role": "member",
            "sex": "female",  # 女性
        },
    ]

    from nonebot_plugin_impart_plus.bot.handlers.yinpa import yinpa_matcher

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.yinpa.asyncio.sleep",
        new_callable=AsyncMock,
    ):
        async with app.test_matcher(yinpa_matcher) as ctx:
            bot = ctx.create_bot(base=OB11Bot)
            event = _tou_event()
            ctx.receive_event(bot, event)
            ctx.should_call_api(
                "get_group_member_list",
                {"group_id": GROUP_ID},
                result=female_member_list,
            )
            ctx.should_call_send(event, ANY_MSG, result=None)
            ctx.should_call_send(event, ANY_MSG, result=None)


# ══════════════════════════════════════════════════════
# 目标选择哨兵消息
# ══════════════════════════════════════════════════════


@pytest.mark.asyncio(loop_scope="session")
async def test_tou_self_target_owner(app: App, fresh_env):
    """透群主 — 发起者自己是群主 → '你透你自己?' 终止。"""
    dm, _cd = fresh_env
    # USER_ID 为群主
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 10.0)

    owner_member_list = [
        {
            "user_id": USER_ID,
            "nickname": "TestUser",
            "card": "测试用户",
            "role": "owner",  # 发起者就是群主
            "sex": "male",
        },
        {
            "user_id": TARGET_ID,
            "nickname": "TargetUser",
            "card": "目标用户",
            "role": "member",
            "sex": "male",
        },
    ]

    from nonebot_plugin_impart_plus.bot.handlers.yinpa import yinpa_owner_matcher

    async with app.test_matcher(yinpa_owner_matcher) as ctx:
        bot = ctx.create_bot(base=OB11Bot)
        event = _tou_event("透群主")
        ctx.receive_event(bot, event)
        ctx.should_call_api(
            "get_group_member_list",
            {"group_id": GROUP_ID},
            result=owner_member_list,
        )
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)


@pytest.mark.asyncio(loop_scope="session")
async def test_tou_no_admin_target(app: App, fresh_env):
    """透管理 — 群内无管理员 → '找不到群管理' 终止。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 10.0)

    no_admin_list = [
        {
            "user_id": USER_ID,
            "nickname": "TestUser",
            "card": "测试用户",
            "role": "member",
            "sex": "male",
        },
        {
            "user_id": TARGET_ID,
            "nickname": "TargetUser",
            "card": "目标用户",
            "role": "member",
            "sex": "male",
        },
        {
            "user_id": 22222222,
            "nickname": "Owner",
            "card": "群主大人",
            "role": "owner",
            "sex": "male",
        },
    ]

    from nonebot_plugin_impart_plus.bot.handlers.yinpa import yinpa_admin_matcher

    async with app.test_matcher(yinpa_admin_matcher) as ctx:
        bot = ctx.create_bot(base=OB11Bot)
        event = _tou_event("透管理")
        ctx.receive_event(bot, event)
        ctx.should_call_api(
            "get_group_member_list",
            {"group_id": GROUP_ID},
            result=no_admin_list,
        )
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
