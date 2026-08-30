"""打胶 / 开导 — 端到端 matcher 测试。"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from nonebug import App
from tests.fake import fake_group_message_event_v11

from .conftest import ANY_MSG, GROUP_ID, USER_ID


def _event(msg: str = "打胶"):
    from nonebot.adapters.onebot.v11 import Message

    return fake_group_message_event_v11(
        user_id=USER_ID,
        group_id=GROUP_ID,
        message=Message(msg),
        raw_message=msg,
    )


@pytest.mark.asyncio(loop_scope="session")
async def test_group_not_enabled(app: App, fresh_env):
    """群未开启时直接终止。"""
    dm, _cd = fresh_env
    await dm.set_group_allow(GROUP_ID, allow=False)

    from nonebot_plugin_impart_plus.bot.handlers.dajiao import dajiao_matcher

    async with app.test_matcher(dajiao_matcher) as ctx:
        bot = ctx.create_bot()
        event = _event()
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
        ctx.should_finished(dajiao_matcher)


@pytest.mark.asyncio(loop_scope="session")
async def test_new_user_creation(app: App, fresh_env):
    """新用户首次打胶 → 创建角色（长度 10）。"""
    dm, _cd = fresh_env

    from nonebot_plugin_impart_plus.bot.handlers.dajiao import dajiao_matcher

    async with app.test_matcher(dajiao_matcher) as ctx:
        bot = ctx.create_bot()
        event = _event()
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
        ctx.should_finished(dajiao_matcher)

    assert await dm.is_in_table(USER_ID)
    assert await dm.get_jj_length(USER_ID) == 10.0


@pytest.mark.asyncio(loop_scope="session")
async def test_normal_dajiao_changes_length(app: App, fresh_env):
    """已有用户正常打胶 → 长度发生变化。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)

    from nonebot_plugin_impart_plus.bot.handlers.dajiao import dajiao_matcher

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.dajiao.get_random_num",
        return_value=3.0,
    ):
        async with app.test_matcher(dajiao_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
            ctx.should_finished(dajiao_matcher)

    assert await dm.get_jj_length(USER_ID) == pytest.approx(13.0, abs=0.01)


@pytest.mark.asyncio(loop_scope="session")
async def test_cd_blocks_second_dajiao(app: App, fresh_env):
    """打胶一次后 CD 内再次打胶被拒。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)

    from nonebot_plugin_impart_plus.bot.handlers.dajiao import dajiao_matcher

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.dajiao.get_random_num",
        return_value=1.0,
    ):
        async with app.test_matcher(dajiao_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
            ctx.should_finished(dajiao_matcher)

        async with app.test_matcher(dajiao_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
            ctx.should_finished(dajiao_matcher)

    assert await dm.get_jj_length(USER_ID) == pytest.approx(11.0, abs=0.01)


@pytest.mark.asyncio(loop_scope="session")
async def test_negative_world_blocks_dajiao(app: App, fresh_env):
    """负值玩家打胶 → 世界阻断。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, -5.0)

    from nonebot_plugin_impart_plus.bot.handlers.dajiao import dajiao_matcher

    async with app.test_matcher(dajiao_matcher) as ctx:
        bot = ctx.create_bot()
        event = _event()
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
        ctx.should_finished(dajiao_matcher)

    assert await dm.get_jj_length(USER_ID) == pytest.approx(-5.0, abs=0.01)


@pytest.mark.asyncio(loop_scope="session")
async def test_challenge_trigger_at_25(app: App, fresh_env):
    """长度从 <25 跨越到 >=25 时触发挑战。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 23.0)

    from nonebot_plugin_impart_plus.bot.handlers.dajiao import dajiao_matcher

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.dajiao.get_random_num",
        return_value=3.0,
    ):
        async with app.test_matcher(dajiao_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
            ctx.should_finished(dajiao_matcher)

    assert await dm.get_jj_length(USER_ID) == pytest.approx(26.0, abs=0.01)


@pytest.mark.asyncio(loop_scope="session")
async def test_kaidao_alias(app: App, fresh_env):
    """开导 = 打胶别名。"""
    dm, _cd = fresh_env

    from nonebot_plugin_impart_plus.bot.handlers.dajiao import dajiao_matcher

    async with app.test_matcher(dajiao_matcher) as ctx:
        bot = ctx.create_bot()
        event = _event("开导")
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
        ctx.should_finished(dajiao_matcher)

    assert await dm.is_in_table(USER_ID)


@pytest.mark.asyncio(loop_scope="session")
async def test_zero_length_blocks_dajiao(app: App, fresh_env):
    """长度恰好为 0（零归负值）→ 负值世界 → 阻断打胶。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 0.0)

    from nonebot_plugin_impart_plus.bot.handlers.dajiao import dajiao_matcher

    async with app.test_matcher(dajiao_matcher) as ctx:
        bot = ctx.create_bot()
        event = _event()
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
        ctx.should_finished(dajiao_matcher)

    # 长度不变
    assert await dm.get_jj_length(USER_ID) == pytest.approx(0.0, abs=0.01)


@pytest.mark.asyncio(loop_scope="session")
async def test_is_challenging_blocks_dajiao(app: App, fresh_env):
    """已在挑战中 → IS_CHALLENGING → 打胶不增长。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 27.0)
    # 首次 update_challenge_status 将 is_challenging 设为 True
    await dm.update_challenge_status(USER_ID)

    from nonebot_plugin_impart_plus.bot.handlers.dajiao import dajiao_matcher

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.dajiao.get_random_num",
        return_value=1.0,
    ):
        async with app.test_matcher(dajiao_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
            ctx.should_finished(dajiao_matcher)

    # 长度不变（挑战中）
    assert await dm.get_jj_length(USER_ID) == pytest.approx(27.0, abs=0.01)


@pytest.mark.asyncio(loop_scope="session")
async def test_dajiao_kaikou_share_cd(app: App, fresh_env):
    """打胶 和 开扣 共享 DJ CD：打胶后开扣被挡。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 10.0)

    from nonebot_plugin_impart_plus.bot.handlers.dajiao import dajiao_matcher

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.dajiao.get_random_num",
        return_value=1.0,
    ):
        async with app.test_matcher(dajiao_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
            ctx.should_finished(dajiao_matcher)

    # 打胶消耗了 DJ CD，现在用开扣
    await dm.set_jj_length_absolute(USER_ID, -5.0)
    from nonebot.adapters.onebot.v11 import Message as V11Message

    from nonebot_plugin_impart_plus.bot.handlers.kaikou import kaikou_matcher

    kaikou_event = fake_group_message_event_v11(
        user_id=USER_ID,
        group_id=GROUP_ID,
        message=V11Message("开扣"),
        raw_message="开扣",
    )

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.kaikou.get_random_num",
        return_value=1.0,
    ):
        async with app.test_matcher(kaikou_matcher) as ctx:
            bot = ctx.create_bot()
            ctx.receive_event(bot, kaikou_event)
            ctx.should_call_send(kaikou_event, ANY_MSG, result=None, at_sender=True)
            ctx.should_finished(kaikou_matcher)

    # 开扣被 CD 挡住，深度不变
    assert await dm.get_jj_length(USER_ID) == pytest.approx(-5.0, abs=0.01)
