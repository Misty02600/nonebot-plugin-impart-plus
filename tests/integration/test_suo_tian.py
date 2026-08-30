"""嗦牛子 / 舔小学 — 端到端 matcher 测试。"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from nonebug import App
from tests.fake import fake_group_message_event_v11

from .conftest import ANY_MSG, GROUP_ID, TARGET_ID, USER_ID


def _suo_event(msg: str = "/嗦牛子", at_qq: str | None = None):
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


def _tian_event(msg: str = "/舔小学", at_qq: str | None = None):
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


# ── 嗦牛子 ──────────────────────────────────────────


@pytest.mark.asyncio(loop_scope="session")
async def test_suo_creates_new_target(app: App, fresh_env):
    """嗦牛子 — 目标不存在时自动创建。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)

    from nonebot_plugin_impart_plus.bot.handlers.suo import suo_matcher

    async with app.test_matcher(suo_matcher) as ctx:
        bot = ctx.create_bot()
        event = _suo_event(at_qq=str(TARGET_ID))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
        ctx.should_finished(suo_matcher)

    assert await dm.is_in_table(TARGET_ID)
    assert await dm.get_jj_length(TARGET_ID) == pytest.approx(10.0, abs=0.01)


@pytest.mark.asyncio(loop_scope="session")
async def test_suo_normal_increases_length(app: App, fresh_env):
    """嗦牛子 — 目标为正值 → 长度增加。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 10.0)

    from nonebot_plugin_impart_plus.bot.handlers.suo import suo_matcher

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.suo.get_random_num",
        return_value=4.0,
    ):
        async with app.test_matcher(suo_matcher) as ctx:
            bot = ctx.create_bot()
            event = _suo_event(at_qq=str(TARGET_ID))
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
            ctx.should_finished(suo_matcher)

    assert await dm.get_jj_length(TARGET_ID) == pytest.approx(14.0, abs=0.01)


@pytest.mark.asyncio(loop_scope="session")
async def test_suo_negative_target_blocked(app: App, fresh_env):
    """嗦牛子 — 目标为负值 → 被阻断。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, -5.0)

    from nonebot_plugin_impart_plus.bot.handlers.suo import suo_matcher

    async with app.test_matcher(suo_matcher) as ctx:
        bot = ctx.create_bot()
        event = _suo_event(at_qq=str(TARGET_ID))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
        ctx.should_finished(suo_matcher)

    # 长度不变
    assert await dm.get_jj_length(TARGET_ID) == pytest.approx(-5.0, abs=0.01)


@pytest.mark.asyncio(loop_scope="session")
async def test_suo_self_no_at(app: App, fresh_env):
    """嗦牛子 — 不 @人 → 嗦自己 → 新用户创建。"""
    dm, _cd = fresh_env

    from nonebot_plugin_impart_plus.bot.handlers.suo import suo_matcher

    async with app.test_matcher(suo_matcher) as ctx:
        bot = ctx.create_bot()
        event = _suo_event()  # 无 @
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
        ctx.should_finished(suo_matcher)

    assert await dm.is_in_table(USER_ID)


@pytest.mark.asyncio(loop_scope="session")
async def test_suo_cd_blocks(app: App, fresh_env):
    """嗦牛子 — CD 内无法二次操作。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 10.0)

    from nonebot_plugin_impart_plus.bot.handlers.suo import suo_matcher

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.suo.get_random_num",
        return_value=2.0,
    ):
        async with app.test_matcher(suo_matcher) as ctx:
            bot = ctx.create_bot()
            event = _suo_event(at_qq=str(TARGET_ID))
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
            ctx.should_finished(suo_matcher)

        async with app.test_matcher(suo_matcher) as ctx:
            bot = ctx.create_bot()
            event = _suo_event(at_qq=str(TARGET_ID))
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
            ctx.should_finished(suo_matcher)

    # 只有第一次生效: 10 + 2 = 12
    assert await dm.get_jj_length(TARGET_ID) == pytest.approx(12.0, abs=0.01)


# ── 舔小学 ──────────────────────────────────────────


@pytest.mark.asyncio(loop_scope="session")
async def test_tian_positive_target_blocked(app: App, fresh_env):
    """舔小学 — 目标为正值 → 不能舔。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 10.0)

    from nonebot_plugin_impart_plus.bot.handlers.tian import tian_matcher

    async with app.test_matcher(tian_matcher) as ctx:
        bot = ctx.create_bot()
        event = _tian_event(at_qq=str(TARGET_ID))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
        ctx.should_finished(tian_matcher)

    assert await dm.get_jj_length(TARGET_ID) == pytest.approx(10.0, abs=0.01)


@pytest.mark.asyncio(loop_scope="session")
async def test_tian_normal_increases_depth(app: App, fresh_env):
    """舔小学 — 目标为负值 → 深度增加。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, -8.0)

    from nonebot_plugin_impart_plus.bot.handlers.tian import tian_matcher

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.tian.get_random_num",
        return_value=3.0,
    ):
        async with app.test_matcher(tian_matcher) as ctx:
            bot = ctx.create_bot()
            event = _tian_event(at_qq=str(TARGET_ID))
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
            ctx.should_finished(tian_matcher)

    # -8 + (-3) = -11
    assert await dm.get_jj_length(TARGET_ID) == pytest.approx(-11.0, abs=0.01)


@pytest.mark.asyncio(loop_scope="session")
async def test_tian_suo_share_cd(app: App, fresh_env):
    """舔小学 和 嗦牛子 共享 CD。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, -10.0)

    from nonebot_plugin_impart_plus.bot.handlers.suo import suo_matcher
    from nonebot_plugin_impart_plus.bot.handlers.tian import tian_matcher

    # 先嗦（目标负值会被block但 CD 仍在 suo handler 的 check 之后，
    # 实际上 suo 负值目标被挡不会记 CD，因为 cd.record_suo 在目标校验之后）
    # 换个思路：先对正值目标嗦，消耗 CD，再舔会被挡
    target2 = 22222222
    await dm.add_new_user(target2)
    await dm.set_jj_length_absolute(target2, 10.0)

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.suo.get_random_num",
        return_value=1.0,
    ):
        async with app.test_matcher(suo_matcher) as ctx:
            bot = ctx.create_bot()
            event = _suo_event(at_qq=str(target2))
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
            ctx.should_finished(suo_matcher)

    # 嗦成功消耗了 CD，现在舔应该被 CD 挡住
    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.tian.get_random_num",
        return_value=2.0,
    ):
        async with app.test_matcher(tian_matcher) as ctx:
            bot = ctx.create_bot()
            event = _tian_event(at_qq=str(TARGET_ID))
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
            ctx.should_finished(tian_matcher)

    # TARGET_ID 未发生变化（被 CD 挡住）
    assert await dm.get_jj_length(TARGET_ID) == pytest.approx(-10.0, abs=0.01)


@pytest.mark.asyncio(loop_scope="session")
async def test_suo_negative_target_does_not_consume_cd(app: App, fresh_env):
    """嗦牛子 — 目标为负值被阻断时 不消耗 CD（cd.record_suo 在校验之后）。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, -5.0)

    from nonebot_plugin_impart_plus.bot.handlers.suo import suo_matcher

    # 第一次：目标为负，被阻断，不应消耗 CD
    async with app.test_matcher(suo_matcher) as ctx:
        bot = ctx.create_bot()
        event = _suo_event(at_qq=str(TARGET_ID))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
        ctx.should_finished(suo_matcher)

    # 第二次：换正值目标 → 应该不被 CD 挡住
    target2 = 33333333
    await dm.add_new_user(target2)
    await dm.set_jj_length_absolute(target2, 10.0)

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.suo.get_random_num",
        return_value=2.0,
    ):
        async with app.test_matcher(suo_matcher) as ctx:
            bot = ctx.create_bot()
            event = _suo_event(at_qq=str(target2))
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
            ctx.should_finished(suo_matcher)

    # 成功嗦了 target2
    assert await dm.get_jj_length(target2) == pytest.approx(12.0, abs=0.01)


@pytest.mark.asyncio(loop_scope="session")
async def test_suo_alias_suo_command(app: App, fresh_env):
    """嗦牛子 — "/suo" 别名可触发。"""
    dm, _cd = fresh_env

    from nonebot_plugin_impart_plus.bot.handlers.suo import suo_matcher

    async with app.test_matcher(suo_matcher) as ctx:
        bot = ctx.create_bot()
        event = _suo_event("/suo")
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
        ctx.should_finished(suo_matcher)

    assert await dm.is_in_table(USER_ID)


@pytest.mark.asyncio(loop_scope="session")
async def test_tian_new_target_not_exists_blocked(app: App, fresh_env):
    """舔小学 — 目标不存在 → 自动创建（正值）→ 不能舔。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)

    from nonebot_plugin_impart_plus.bot.handlers.tian import tian_matcher

    async with app.test_matcher(tian_matcher) as ctx:
        bot = ctx.create_bot()
        event = _tian_event(at_qq=str(TARGET_ID))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
        ctx.should_finished(tian_matcher)

    # 目标被自动创建为正值（10），但舔操作被阻断
    assert await dm.is_in_table(TARGET_ID)
    assert await dm.get_jj_length(TARGET_ID) == pytest.approx(10.0, abs=0.01)


@pytest.mark.asyncio(loop_scope="session")
async def test_tian_new_target_no_cd_consumed(app: App, fresh_env):
    """舔小学 — 目标不存在被阻断时 不消耗 CD（cd.record_suo 在校验之后）。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)

    from nonebot_plugin_impart_plus.bot.handlers.tian import tian_matcher

    # 目标不存在 → 被阻断
    async with app.test_matcher(tian_matcher) as ctx:
        bot = ctx.create_bot()
        event = _tian_event(at_qq=str(TARGET_ID))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
        ctx.should_finished(tian_matcher)

    # 再把目标改为负值，舔应该不被 CD 阻挡
    await dm.set_jj_length_absolute(TARGET_ID, -5.0)

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.tian.get_random_num",
        return_value=1.0,
    ):
        async with app.test_matcher(tian_matcher) as ctx:
            bot = ctx.create_bot()
            event = _tian_event(at_qq=str(TARGET_ID))
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
            ctx.should_finished(tian_matcher)

    # 成功舔了：-5 + (-1) = -6
    assert await dm.get_jj_length(TARGET_ID) == pytest.approx(-6.0, abs=0.01)


@pytest.mark.asyncio(loop_scope="session")
async def test_tian_challenge_trigger_at_depth_25(app: App, fresh_env):
    """舔小学 — 目标深度从 <25 跨越到 >=25 时触发挑战。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, -23.0)

    from nonebot_plugin_impart_plus.bot.handlers.tian import tian_matcher

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.tian.get_random_num",
        return_value=3.0,
    ):
        async with app.test_matcher(tian_matcher) as ctx:
            bot = ctx.create_bot()
            event = _tian_event(at_qq=str(TARGET_ID))
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
            ctx.should_finished(tian_matcher)

    # -23 + (-3) = -26, depth = 26 >= 25
    assert await dm.get_jj_length(TARGET_ID) == pytest.approx(-26.0, abs=0.01)


# ══════════════════════════════════════════════════════
# 挑战状态边界 — 嗦
# ══════════════════════════════════════════════════════


@pytest.mark.asyncio(loop_scope="session")
async def test_suo_target_is_challenging(app: App, fresh_env):
    """嗦牛子 — 目标正在挑战中 (is_challenging=True) → 被拦截。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 27.0)
    # 首次 update_challenge_status → is_challenging = True
    await dm.update_challenge_status(TARGET_ID)

    from nonebot_plugin_impart_plus.bot.handlers.suo import suo_matcher

    async with app.test_matcher(suo_matcher) as ctx:
        bot = ctx.create_bot()
        event = _suo_event(at_qq=str(TARGET_ID))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
        ctx.should_finished(suo_matcher)

    # 长度不变（被拦截，没有嗦到）
    assert await dm.get_jj_length(TARGET_ID) == pytest.approx(27.0, abs=0.01)


@pytest.mark.asyncio(loop_scope="session")
async def test_suo_triggers_challenge(app: App, fresh_env):
    """嗦牛子 — 目标长度从 <25 跨越到 >=25 时触发挑战。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 23.0)

    from nonebot_plugin_impart_plus.bot.handlers.suo import suo_matcher

    with patch(
        "nonebot_plugin_impart_plus.bot.handlers.suo.get_random_num",
        return_value=3.0,
    ):
        async with app.test_matcher(suo_matcher) as ctx:
            bot = ctx.create_bot()
            event = _suo_event(at_qq=str(TARGET_ID))
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
            ctx.should_finished(suo_matcher)

    # 23 + 3 = 26 >= 25 → 触发挑战
    assert await dm.get_jj_length(TARGET_ID) == pytest.approx(26.0, abs=0.01)


# ══════════════════════════════════════════════════════
# 挑战状态边界 — 舔
# ══════════════════════════════════════════════════════


@pytest.mark.asyncio(loop_scope="session")
async def test_tian_target_is_challenging(app: App, fresh_env):
    """舔小学 — 目标正在挑战中 (is_challenging=True) → 被拦截。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, -27.0)  # 负值世界
    await dm.update_challenge_status(TARGET_ID)  # is_challenging = True

    from nonebot_plugin_impart_plus.bot.handlers.tian import tian_matcher

    async with app.test_matcher(tian_matcher) as ctx:
        bot = ctx.create_bot()
        event = _tian_event(at_qq=str(TARGET_ID))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)
        ctx.should_finished(tian_matcher)

    # 长度不变（被拦截）
    assert await dm.get_jj_length(TARGET_ID) == pytest.approx(-27.0, abs=0.01)
