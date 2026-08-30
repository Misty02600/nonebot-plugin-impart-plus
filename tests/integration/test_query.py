"""查询 — 端到端 matcher 测试。"""

from __future__ import annotations

import pytest
from nonebug import App
from tests.fake import fake_group_message_event_v11

from .conftest import ANY_MSG, GROUP_ID, TARGET_ID, USER_ID


def _event(msg: str = "/查询", at_qq: str | None = None):
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    segments = MessageSegment.text(msg)
    if at_qq:
        segments = MessageSegment.text(msg) + MessageSegment.at(at_qq)
    return fake_group_message_event_v11(
        user_id=USER_ID,
        group_id=GROUP_ID,
        message=Message(segments),
        raw_message=msg,
    )


@pytest.mark.asyncio(loop_scope="session")
async def test_query_new_user(app: App, fresh_env):
    """查询 — 新用户自动创建并返回结果。"""
    dm, _cd = fresh_env

    from nonebot_plugin_impart_plus.bot.handlers.query import query_matcher

    async with app.test_matcher(query_matcher) as ctx:
        bot = ctx.create_bot()
        event = _event()
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    assert await dm.is_in_table(USER_ID)
    assert await dm.get_jj_length(USER_ID) == pytest.approx(10.0, abs=0.01)


@pytest.mark.asyncio(loop_scope="session")
async def test_query_god_title(app: App, fresh_env):
    """查询 — 长度 >= 30 显示牛子神。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 35.0)

    from nonebot_plugin_impart_plus.bot.handlers.query import query_matcher

    async with app.test_matcher(query_matcher) as ctx:
        bot = ctx.create_bot()
        event = _event()
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)


@pytest.mark.asyncio(loop_scope="session")
async def test_query_normal(app: App, fresh_env):
    """查询 — 5 < 长度 < 30 显示普通。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 15.0)

    from nonebot_plugin_impart_plus.bot.handlers.query import query_matcher

    async with app.test_matcher(query_matcher) as ctx:
        bot = ctx.create_bot()
        event = _event()
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)


@pytest.mark.asyncio(loop_scope="session")
async def test_query_near_girl(app: App, fresh_env):
    """查询 — 0 < 长度 <= 5 显示 near girl。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 3.0)

    from nonebot_plugin_impart_plus.bot.handlers.query import query_matcher

    async with app.test_matcher(query_matcher) as ctx:
        bot = ctx.create_bot()
        event = _event()
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)


@pytest.mark.asyncio(loop_scope="session")
async def test_query_abyss_lord(app: App, fresh_env):
    """查询 — 深度 >= 30 显示深渊领主。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, -35.0)

    from nonebot_plugin_impart_plus.bot.handlers.query import query_matcher

    async with app.test_matcher(query_matcher) as ctx:
        bot = ctx.create_bot()
        event = _event()
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)


@pytest.mark.asyncio(loop_scope="session")
async def test_query_girl(app: App, fresh_env):
    """查询 — 负值且深度 < 30 显示女孩子。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, -10.0)

    from nonebot_plugin_impart_plus.bot.handlers.query import query_matcher

    async with app.test_matcher(query_matcher) as ctx:
        bot = ctx.create_bot()
        event = _event()
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)


@pytest.mark.asyncio(loop_scope="session")
async def test_query_at_target(app: App, fresh_env):
    """查询 — @目标 → 显示目标数据。"""
    dm, _cd = fresh_env
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 20.0)

    from nonebot_plugin_impart_plus.bot.handlers.query import query_matcher

    async with app.test_matcher(query_matcher) as ctx:
        bot = ctx.create_bot()
        event = _event(at_qq=str(TARGET_ID))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)


@pytest.mark.asyncio(loop_scope="session")
async def test_query_exact_boundary_zero(app: App, fresh_env):
    """查询 — 长度 = 0（零归负值）→ 负值查询。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 0.0)

    from nonebot_plugin_impart_plus.bot.handlers.query import query_matcher

    async with app.test_matcher(query_matcher) as ctx:
        bot = ctx.create_bot()
        event = _event()
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)


@pytest.mark.asyncio(loop_scope="session")
async def test_query_exact_boundary_5(app: App, fresh_env):
    """查询 — 长度 = 5 → near_girl 区间（0 < length <= 5）。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 5.0)

    from nonebot_plugin_impart_plus.bot.handlers.query import query_matcher

    async with app.test_matcher(query_matcher) as ctx:
        bot = ctx.create_bot()
        event = _event()
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)


@pytest.mark.asyncio(loop_scope="session")
async def test_query_exact_boundary_30(app: App, fresh_env):
    """查询 — 长度 = 30（恰好 god 阈值）→ 牛子神。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 30.0)

    from nonebot_plugin_impart_plus.bot.handlers.query import query_matcher

    async with app.test_matcher(query_matcher) as ctx:
        bot = ctx.create_bot()
        event = _event()
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)


@pytest.mark.asyncio(loop_scope="session")
async def test_query_exact_boundary_neg_30(app: App, fresh_env):
    """查询 — 深度 = 30（恰好 abyss_lord 阈值）→ 深渊领主。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, -30.0)

    from nonebot_plugin_impart_plus.bot.handlers.query import query_matcher

    async with app.test_matcher(query_matcher) as ctx:
        bot = ctx.create_bot()
        event = _event()
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
