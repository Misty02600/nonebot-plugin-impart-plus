"""开扣 / 挖矿 — 端到端 matcher 测试。"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from nonebug import App
from tests.fake import fake_group_message_event_v11

from .conftest import ANY_MSG, GROUP_ID, USER_ID


def _event(msg: str = "开扣"):
    from nonebot.adapters.onebot.v11 import Message

    return fake_group_message_event_v11(
        user_id=USER_ID,
        group_id=GROUP_ID,
        message=Message(msg),
        raw_message=msg,
    )


@pytest.mark.asyncio(loop_scope="session")
async def test_positive_world_blocks_kaikou(app: App, fresh_env):
    """正值玩家使用开扣 → 阵营阻断。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 10.0)

    from nonebot_plugin_impart_plus.bot.handlers.kaikou import kaikou_matcher

    async with app.test_matcher(kaikou_matcher) as ctx:
        bot = ctx.create_bot()
        event = _event()
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
        ctx.should_finished(kaikou_matcher)

    # 长度不变
    assert await dm.get_jj_length(USER_ID) == pytest.approx(10.0, abs=0.01)


@pytest.mark.asyncio(loop_scope="session")
async def test_new_user_blocks_kaikou(app: App, fresh_env):
    """新玩家（未注册）开扣 → 自动注册 + 阵营阻断。"""
    dm, _cd = fresh_env

    from nonebot_plugin_impart_plus.bot.handlers.kaikou import kaikou_matcher

    async with app.test_matcher(kaikou_matcher) as ctx:
        bot = ctx.create_bot()
        event = _event()
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
        ctx.should_finished(kaikou_matcher)

    # 新用户被创建为正值（10），但操作不生效
    assert await dm.is_in_table(USER_ID)
    assert await dm.get_jj_length(USER_ID) == pytest.approx(10.0, abs=0.01)


@pytest.mark.asyncio(loop_scope="session")
async def test_normal_kaikou_increases_depth(app: App, fresh_env):
    """负值玩家正常开扣 → 深度增加。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, -5.0)

    from nonebot_plugin_impart_plus.bot.handlers.kaikou import kaikou_matcher

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.kaikou.get_random_num",
        return_value=3.0,
    ):
        async with app.test_matcher(kaikou_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
            ctx.should_finished(kaikou_matcher)

    # -5 + (-3) = -8 → depth = 8
    assert await dm.get_jj_length(USER_ID) == pytest.approx(-8.0, abs=0.01)


@pytest.mark.asyncio(loop_scope="session")
async def test_cd_blocks_second_kaikou(app: App, fresh_env):
    """开扣一次后 CD 内再次操作被拒。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, -5.0)

    from nonebot_plugin_impart_plus.bot.handlers.kaikou import kaikou_matcher

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.kaikou.get_random_num",
        return_value=1.0,
    ):
        async with app.test_matcher(kaikou_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
            ctx.should_finished(kaikou_matcher)

        # 第二次应被 CD 挡住
        async with app.test_matcher(kaikou_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
            ctx.should_finished(kaikou_matcher)

    # 只发生一次变化: -5 + (-1) = -6
    assert await dm.get_jj_length(USER_ID) == pytest.approx(-6.0, abs=0.01)


@pytest.mark.asyncio(loop_scope="session")
async def test_kuangkuang_alias(app: App, fresh_env):
    """挖矿 = 开扣别名，验证可正常触发。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, -3.0)

    from nonebot_plugin_impart_plus.bot.handlers.kaikou import kaikou_matcher

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.kaikou.get_random_num",
        return_value=2.0,
    ):
        async with app.test_matcher(kaikou_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event("挖矿")
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
            ctx.should_finished(kaikou_matcher)

    assert await dm.get_jj_length(USER_ID) == pytest.approx(-5.0, abs=0.01)


@pytest.mark.asyncio(loop_scope="session")
async def test_challenge_trigger_at_depth_25(app: App, fresh_env):
    """深度从 <25 跨越到 >=25 时触发挑战。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, -23.0)

    from nonebot_plugin_impart_plus.bot.handlers.kaikou import kaikou_matcher

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.kaikou.get_random_num",
        return_value=3.0,
    ):
        async with app.test_matcher(kaikou_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
            ctx.should_finished(kaikou_matcher)

    # -23 + (-3) = -26, depth = 26 >= 25
    assert await dm.get_jj_length(USER_ID) == pytest.approx(-26.0, abs=0.01)


@pytest.mark.asyncio(loop_scope="session")
async def test_is_challenging_blocks_kaikou(app: App, fresh_env):
    """已在挑战中 → IS_CHALLENGING → 开扣不增深。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, -27.0)
    # 触发挑战状态
    await dm.update_challenge_status(USER_ID)

    from nonebot_plugin_impart_plus.bot.handlers.kaikou import kaikou_matcher

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.kaikou.get_random_num",
        return_value=2.0,
    ):
        async with app.test_matcher(kaikou_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
            ctx.should_finished(kaikou_matcher)

    # 深度不变（挑战中）
    assert await dm.get_jj_length(USER_ID) == pytest.approx(-27.0, abs=0.01)
