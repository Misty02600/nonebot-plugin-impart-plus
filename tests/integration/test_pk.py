"""PK / 击剑 / 磨豆腐 — 端到端 matcher 测试。"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from nonebug import App
from tests.fake import fake_group_message_event_v11

from .conftest import ANY_MSG, GROUP_ID, TARGET_ID, USER_ID


def _event(msg: str = "/pk", at_qq: str = str(TARGET_ID)):
    """构造带 @ 的 PK 事件。"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    segments = MessageSegment.text(msg) + MessageSegment.at(at_qq)
    return fake_group_message_event_v11(
        user_id=USER_ID,
        group_id=GROUP_ID,
        message=Message(segments),
        raw_message=msg,
    )


# ── pk / 对决（通用 PK）──────────────────────────────


@pytest.mark.asyncio(loop_scope="session")
async def test_pk_new_users_created(app: App, fresh_env):
    """PK — 双方都不存在时自动创建。"""
    dm, _cd = fresh_env

    from nonebot_plugin_impart_plus.bot.handlers.pk import pk_shared_matcher

    async with app.test_matcher(pk_shared_matcher) as ctx:
        bot = ctx.create_bot()
        event = _event()
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    assert await dm.is_in_table(USER_ID)
    assert await dm.is_in_table(TARGET_ID)


@pytest.mark.asyncio(loop_scope="session")
async def test_pk_self_rejected(app: App, fresh_env):
    """PK — @自己 → 拒绝。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)

    from nonebot_plugin_impart_plus.bot.handlers.pk import pk_shared_matcher

    async with app.test_matcher(pk_shared_matcher) as ctx:
        bot = ctx.create_bot()
        event = _event(at_qq=str(USER_ID))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)


@pytest.mark.asyncio(loop_scope="session")
async def test_pk_cross_camp_rejected(app: App, fresh_env):
    """PK — 正负阵营不同 → 阻断。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 10.0)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, -5.0)

    from nonebot_plugin_impart_plus.bot.handlers.pk import pk_shared_matcher

    async with app.test_matcher(pk_shared_matcher) as ctx:
        bot = ctx.create_bot()
        event = _event()
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)


@pytest.mark.asyncio(loop_scope="session")
async def test_positive_pk_win(app: App, fresh_env):
    """正值 PK 胜利 → 赢家长度增加，输家减少。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 15.0)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 12.0)

    from nonebot_plugin_impart_plus.bot.handlers.pk import pk_shared_matcher

    with (
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.random.random",
            return_value=0.01,  # 远小于 base prob → 必赢
        ),
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.get_random_num",
            return_value=4.0,
        ),
    ):
        async with app.test_matcher(pk_shared_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    # 赢家 +2 (4/2)，输家 -4
    assert await dm.get_jj_length(USER_ID) == pytest.approx(17.0, abs=0.01)
    assert await dm.get_jj_length(TARGET_ID) == pytest.approx(8.0, abs=0.5)


@pytest.mark.asyncio(loop_scope="session")
async def test_positive_pk_lose(app: App, fresh_env):
    """正值 PK 失败 → 自己长度减少，对方增加。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 15.0)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 12.0)

    from nonebot_plugin_impart_plus.bot.handlers.pk import pk_shared_matcher

    with (
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.random.random",
            return_value=0.99,  # 远大于任何 prob → 必输
        ),
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.get_random_num",
            return_value=4.0,
        ),
    ):
        async with app.test_matcher(pk_shared_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    # 输家 -4, 赢家 +2
    assert await dm.get_jj_length(USER_ID) == pytest.approx(11.0, abs=0.5)
    assert await dm.get_jj_length(TARGET_ID) == pytest.approx(14.0, abs=0.01)


@pytest.mark.asyncio(loop_scope="session")
async def test_pk_cd_blocks(app: App, fresh_env):
    """PK — CD 内无法二次操作。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 15.0)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 12.0)

    from nonebot_plugin_impart_plus.bot.handlers.pk import pk_shared_matcher

    with (
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.random.random",
            return_value=0.01,
        ),
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.get_random_num",
            return_value=2.0,
        ),
    ):
        async with app.test_matcher(pk_shared_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

        # 第二次被 CD 挡住
        async with app.test_matcher(pk_shared_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    # 只发生一次变化
    user_len = await dm.get_jj_length(USER_ID)
    target_len = await dm.get_jj_length(TARGET_ID)
    assert user_len == pytest.approx(16.0, abs=0.01)  # +1 (2/2)
    assert target_len == pytest.approx(10.0, abs=0.5)  # -2


# ── 击剑 ────────────────────────────────────────────


@pytest.mark.asyncio(loop_scope="session")
async def test_jijian_negative_blocked(app: App, fresh_env):
    """击剑 — 负值玩家被阵营守卫阻断。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, -10.0)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, -8.0)

    from nonebot_plugin_impart_plus.bot.handlers.pk import jijian_matcher

    async with app.test_matcher(jijian_matcher) as ctx:
        bot = ctx.create_bot()
        event = _event("/击剑")
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)


# ── 磨豆腐 ──────────────────────────────────────────


@pytest.mark.asyncio(loop_scope="session")
async def test_modofu_positive_blocked(app: App, fresh_env):
    """磨豆腐 — 正值玩家被阵营守卫阻断。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 10.0)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 12.0)

    from nonebot_plugin_impart_plus.bot.handlers.pk import modofu_matcher

    async with app.test_matcher(modofu_matcher) as ctx:
        bot = ctx.create_bot()
        event = _event("/磨豆腐")
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)


@pytest.mark.asyncio(loop_scope="session")
async def test_modofu_negative_pk(app: App, fresh_env):
    """磨豆腐 — 负值 PK 正常执行。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, -10.0)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, -8.0)

    from nonebot_plugin_impart_plus.bot.handlers.pk import modofu_matcher

    with (
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.random.random",
            return_value=0.01,  # 必赢
        ),
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.get_random_num",
            return_value=4.0,
        ),
    ):
        async with app.test_matcher(modofu_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event("/磨豆腐")
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    # 负值 PK: 赢家 length_gain = -(4/2) = -2 → -10 + (-2) = -12
    # 输家 length_loss = -4 → -(-4) = +4 → -8 + 4 = -4
    assert await dm.get_jj_length(USER_ID) == pytest.approx(-12.0, abs=0.01)
    assert await dm.get_jj_length(TARGET_ID) == pytest.approx(-4.0, abs=0.01)


@pytest.mark.asyncio(loop_scope="session")
async def test_modofu_loser_no_flip_to_positive(app: App, fresh_env):
    """磨豆腐 — 败者不得翻正：钳制到 -0.01。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, -10.0)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, -1.0)  # 很浅

    from nonebot_plugin_impart_plus.bot.handlers.pk import modofu_matcher

    with (
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.random.random",
            return_value=0.01,  # USER_ID 赢，TARGET_ID 输
        ),
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.get_random_num",
            return_value=6.0,  # 败者变浅 +6 → -1 + 6 = 5 > 0
        ),
    ):
        async with app.test_matcher(modofu_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event("/磨豆腐")
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    # 败者被钳制到 -0.01
    assert await dm.get_jj_length(TARGET_ID) == pytest.approx(-0.01, abs=0.001)


@pytest.mark.asyncio(loop_scope="session")
async def test_pk_duijue_alias(app: App, fresh_env):
    """pk — "对决" 别名可触发。"""
    dm, _cd = fresh_env

    from nonebot_plugin_impart_plus.bot.handlers.pk import pk_shared_matcher

    async with app.test_matcher(pk_shared_matcher) as ctx:
        bot = ctx.create_bot()
        event = _event("/对决")
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    assert await dm.is_in_table(USER_ID)
    assert await dm.is_in_table(TARGET_ID)


@pytest.mark.asyncio(loop_scope="session")
async def test_pk_one_user_not_exists(app: App, fresh_env):
    """PK — 仅一方存在 → 自动创建另一方 → 首次消息。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 15.0)
    # TARGET_ID 不存在

    from nonebot_plugin_impart_plus.bot.handlers.pk import pk_shared_matcher

    async with app.test_matcher(pk_shared_matcher) as ctx:
        bot = ctx.create_bot()
        event = _event()
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    assert await dm.is_in_table(TARGET_ID)
    # TARGET_ID 被自动创建为默认长度 10
    assert await dm.get_jj_length(TARGET_ID) == pytest.approx(10.0, abs=0.01)


@pytest.mark.asyncio(loop_scope="session")
async def test_xnn_debuff_halves_win_rate(app: App, fresh_env):
    """正值 PK — xnn 区间攻击方胜率减半。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 3.0)  # xnn: 0 < L <= 5
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 15.0)

    from nonebot_plugin_impart_plus.bot.handlers.pk import pk_shared_matcher

    # 基础胜率 0.5 → xnn 减半 → 0.25, 归一化: 0.25/(0.25+0.5)≈0.333, random=0.40 应输
    with (
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.random.random",
            return_value=0.40,
        ),
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.get_random_num",
            return_value=4.0,
        ),
    ):
        async with app.test_matcher(pk_shared_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    # USER_ID 输了（0.40 > 0.333），xnn 败方损失 ×1.5 = 4 × 1.5 = 6
    user_len = await dm.get_jj_length(USER_ID)
    # 3 - 6 < 0 → clamp_xnn_floor: 原 state is_xnn=True, new_length < 0.01 → 0.01
    assert user_len == pytest.approx(0.01, abs=0.001)


@pytest.mark.asyncio(loop_scope="session")
async def test_xnn_clamp_floor(app: App, fresh_env):
    """正值 PK — xnn 败者不低于 0.01。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 2.0)  # xnn
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 10.0)

    from nonebot_plugin_impart_plus.bot.handlers.pk import pk_shared_matcher

    # USER_ID wins (0.01 < 0.25)
    with (
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.random.random",
            return_value=0.01,
        ),
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.get_random_num",
            return_value=4.0,
        ),
    ):
        async with app.test_matcher(pk_shared_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    # USER_ID 赢了: xnn 爆冷 bonus=max(1,0.5/0.25)=2, gain=4×0.5×2=4 → 2+4=6.0
    assert await dm.get_jj_length(USER_ID) == pytest.approx(6.0, abs=0.01)
    # TARGET_ID 输了: 10 - 4 = 6 (TARGET not xnn, no amplification)
    assert await dm.get_jj_length(TARGET_ID) == pytest.approx(6.0, abs=0.5)


@pytest.mark.asyncio(loop_scope="session")
async def test_negative_pk_via_shared_matcher(app: App, fresh_env):
    """pk/对决 — 双方都是负值时自动路由到负值 PK 逻辑。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, -10.0)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, -8.0)

    from nonebot_plugin_impart_plus.bot.handlers.pk import pk_shared_matcher

    with (
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.random.random",
            return_value=0.01,  # 必赢
        ),
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.get_random_num",
            return_value=4.0,
        ),
    ):
        async with app.test_matcher(pk_shared_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    # 负值 PK: 赢家 -10 + (-(4/2)) = -12, 输家 -8 + 4 = -4
    assert await dm.get_jj_length(USER_ID) == pytest.approx(-12.0, abs=0.01)
    assert await dm.get_jj_length(TARGET_ID) == pytest.approx(-4.0, abs=0.01)


@pytest.mark.asyncio(loop_scope="session")
async def test_mo_alias(app: App, fresh_env):
    """磨豆腐 — "磨" 别名可触发。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, -10.0)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, -8.0)

    from nonebot_plugin_impart_plus.bot.handlers.pk import modofu_matcher

    with (
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.random.random",
            return_value=0.01,
        ),
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.get_random_num",
            return_value=2.0,
        ),
    ):
        async with app.test_matcher(modofu_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event("/磨")
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    # 赢家加深: -10 + (-(2/2)) = -11
    assert await dm.get_jj_length(USER_ID) == pytest.approx(-11.0, abs=0.01)


# ══════════════════════════════════════════════════════
# 正值 PK 挑战系统
# ══════════════════════════════════════════════════════


@pytest.mark.asyncio(loop_scope="session")
async def test_positive_pk_self_challenge_trigger(app: App, fresh_env):
    """正值 PK — 赢家长度从 <25 跨越到 >=25 → 触发挑战（概率×0.8，后续打胶/嗦锁定）。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 24.0)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 15.0)

    from nonebot_plugin_impart_plus.bot.handlers.pk import pk_shared_matcher

    with (
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.random.random",
            return_value=0.01,  # 必赢
        ),
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.get_random_num",
            return_value=4.0,
        ),
    ):
        async with app.test_matcher(pk_shared_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    # gain = 4*0.5 = 2, USER: 24+2 = 26 (触发挑战，但无 length penalty)
    assert await dm.get_jj_length(USER_ID) == pytest.approx(26.0, abs=0.01)

    # 验证后续打胶被锁：IS_CHALLENGING
    from nonebot_plugin_impart_plus.core.game import ChallengeStatus

    status = await dm.update_challenge_status(USER_ID)
    assert status == ChallengeStatus.IS_CHALLENGING


@pytest.mark.asyncio(loop_scope="session")
async def test_positive_pk_self_challenge_success(app: App, fresh_env):
    """正值 PK — 挑战中赢家长度达 30 → 挑战成功，授予牛子神称号。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 28.0)
    # 进入挑战状态
    await dm.update_challenge_status(USER_ID)

    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 15.0)

    from nonebot_plugin_impart_plus.bot.handlers.pk import pk_shared_matcher

    with (
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.random.random",
            return_value=0.01,
        ),
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.get_random_num",
            return_value=4.0,  # 挑战 prob*=0.8→0.4, bonus=0.5/0.4=1.25, gain=4*0.5*1.25=2.5, 28+2.5=30.5
        ),
    ):
        async with app.test_matcher(pk_shared_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    # 30.5，挑战成功后无额外 penalty
    assert await dm.get_jj_length(USER_ID) == pytest.approx(30.5, abs=0.01)

    # 验证挑战已完成：打胶应恢复可用（不再 IS_CHALLENGING）
    from nonebot_plugin_impart_plus.core.game import ChallengeStatus

    status = await dm.update_challenge_status(USER_ID)
    assert status != ChallengeStatus.IS_CHALLENGING


@pytest.mark.asyncio(loop_scope="session")
async def test_positive_pk_self_challenge_failed(app: App, fresh_env):
    """正值 PK — 挑战中输家长度跌回 <25 → 挑战失败，额外 -5 惩罚。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 26.0)
    await dm.update_challenge_status(USER_ID)  # is_challenging = True

    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 15.0)

    from nonebot_plugin_impart_plus.bot.handlers.pk import pk_shared_matcher

    with (
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.random.random",
            return_value=0.99,  # 必输
        ),
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.get_random_num",
            return_value=4.0,  # loss = 4, USER: 26-4 = 22 → <25, 再 -5 = 17
        ),
    ):
        async with app.test_matcher(pk_shared_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    # 26 - 4 = 22 (挑战失败触发)，penalty -5 → 17
    assert await dm.get_jj_length(USER_ID) == pytest.approx(17.0, abs=0.5)


@pytest.mark.asyncio(loop_scope="session")
async def test_positive_pk_self_fall_from_god(app: App, fresh_env):
    """正值 PK — 已完成挑战（牛子神）输掉后长度跌回 <25 → 跌落神坛，额外 -5。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    # 先让 USER 完成挑战
    await dm.set_jj_length_absolute(USER_ID, 31.0)
    await dm.update_challenge_status(USER_ID)  # challenge_completed = True
    # 然后回退到 26（仍在完成区间内）
    await dm.set_jj_length_absolute(USER_ID, 26.0)

    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 15.0)

    from nonebot_plugin_impart_plus.bot.handlers.pk import pk_shared_matcher

    with (
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.random.random",
            return_value=0.99,  # 必输
        ),
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.get_random_num",
            return_value=4.0,  # loss = 4, USER: 26-4 = 22 → <25, penalty -5 → 17
        ),
    ):
        async with app.test_matcher(pk_shared_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    # 26 - 4 = 22 (跌落触发)，penalty -5 → 17
    assert await dm.get_jj_length(USER_ID) == pytest.approx(17.0, abs=0.5)


@pytest.mark.asyncio(loop_scope="session")
async def test_positive_pk_opp_challenge_trigger(app: App, fresh_env):
    """正值 PK — 对方因我方失败而长度超 25 → 触发对方挑战。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 15.0)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 24.0)

    from nonebot_plugin_impart_plus.bot.handlers.pk import pk_shared_matcher

    with (
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.random.random",
            return_value=0.99,  # USER 必输 → TARGET 赢
        ),
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.get_random_num",
            return_value=4.0,  # TARGET gain = 4*0.5 = 2, TARGET: 24+2 = 26
        ),
    ):
        async with app.test_matcher(pk_shared_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    assert await dm.get_jj_length(TARGET_ID) == pytest.approx(26.0, abs=0.01)

    # 对方进入挑战状态
    from nonebot_plugin_impart_plus.core.game import ChallengeStatus

    status = await dm.update_challenge_status(TARGET_ID)
    assert status == ChallengeStatus.IS_CHALLENGING


@pytest.mark.asyncio(loop_scope="session")
async def test_positive_pk_opp_challenge_failed(app: App, fresh_env):
    """正值 PK — 我方赢导致对方（挑战中）长度跌回 <25 → 对方挑战失败，-5。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 15.0)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 26.0)
    await dm.update_challenge_status(TARGET_ID)  # TARGET is_challenging = True

    from nonebot_plugin_impart_plus.bot.handlers.pk import pk_shared_matcher

    with (
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.random.random",
            return_value=0.01,  # USER 必赢 → TARGET 输
        ),
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.get_random_num",
            return_value=4.0,  # TARGET loss = 4, TARGET: 26-4 = 22 → 失败, -5 → 17
        ),
    ):
        async with app.test_matcher(pk_shared_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    # TARGET: 26-4=22, challenge_failed → penalty -5 → 17
    assert await dm.get_jj_length(TARGET_ID) == pytest.approx(17.0, abs=0.5)


# ══════════════════════════════════════════════════════
# 负值 PK 挑战系统
# ══════════════════════════════════════════════════════


@pytest.mark.asyncio(loop_scope="session")
async def test_negative_pk_self_challenge_trigger(app: App, fresh_env):
    """负值 PK — 赢家深度从 <25 跨越到 >=25 → 触发深渊试炼。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, -24.0)  # depth=24
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, -15.0)

    from nonebot_plugin_impart_plus.bot.handlers.pk import modofu_matcher

    with (
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.random.random",
            return_value=0.01,  # 必赢
        ),
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.get_random_num",
            return_value=4.0,  # gain = -(4*0.5) = -2, USER: -24+(-2) = -26, depth=26
        ),
    ):
        async with app.test_matcher(modofu_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event("/磨豆腐")
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    assert await dm.get_jj_length(USER_ID) == pytest.approx(-26.0, abs=0.01)

    from nonebot_plugin_impart_plus.core.game import ChallengeStatus

    status = await dm.update_challenge_status(USER_ID)
    assert status == ChallengeStatus.IS_CHALLENGING


@pytest.mark.asyncio(loop_scope="session")
async def test_negative_pk_self_challenge_success(app: App, fresh_env):
    """负值 PK — 挑战中赢家深度达 30 → 深渊挑战成功，授予深渊之主。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, -28.0)
    await dm.update_challenge_status(USER_ID)  # is_challenging = True

    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, -15.0)

    from nonebot_plugin_impart_plus.bot.handlers.pk import modofu_matcher

    with (
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.random.random",
            return_value=0.01,
        ),
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.get_random_num",
            return_value=4.0,  # 挑战 prob*=0.8→0.4, bonus=1.25, gain=2.5, -28-2.5=-30.5
        ),
    ):
        async with app.test_matcher(modofu_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event("/磨豆腐")
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    assert await dm.get_jj_length(USER_ID) == pytest.approx(-30.5, abs=0.01)

    from nonebot_plugin_impart_plus.core.game import ChallengeStatus

    status = await dm.update_challenge_status(USER_ID)
    assert status != ChallengeStatus.IS_CHALLENGING


@pytest.mark.asyncio(loop_scope="session")
async def test_negative_pk_self_challenge_failed(app: App, fresh_env):
    """负值 PK — 挑战中输家深度跌回 <25 → 挑战失败，惩罚 +5（深度减少）。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, -26.0)
    await dm.update_challenge_status(USER_ID)  # is_challenging = True

    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, -15.0)

    from nonebot_plugin_impart_plus.bot.handlers.pk import modofu_matcher

    with (
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.random.random",
            return_value=0.99,  # USER 必输
        ),
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.get_random_num",
            return_value=4.0,  # 变浅: -(-4) = +4, USER: -26+4 = -22, depth=22 < 25
        ),
    ):
        async with app.test_matcher(modofu_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event("/磨豆腐")
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    # -26+4=-22, 挑战失败 penalty=+5 (负值翻转), -22+5=-17
    assert await dm.get_jj_length(USER_ID) == pytest.approx(-17.0, abs=0.5)


@pytest.mark.asyncio(loop_scope="session")
async def test_negative_pk_self_fall_from_abyss(app: App, fresh_env):
    """负值 PK — 深渊之主输掉后深度跌回 <25 → 跌落深渊，惩罚 +5。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, -31.0)
    await dm.update_challenge_status(USER_ID)  # challenge_completed = True
    await dm.set_jj_length_absolute(USER_ID, -26.0)

    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, -15.0)

    from nonebot_plugin_impart_plus.bot.handlers.pk import modofu_matcher

    with (
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.random.random",
            return_value=0.99,
        ),
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.get_random_num",
            return_value=4.0,  # USER: -26+4=-22, 跌落触发 +5 → -17
        ),
    ):
        async with app.test_matcher(modofu_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event("/磨豆腐")
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    assert await dm.get_jj_length(USER_ID) == pytest.approx(-17.0, abs=0.5)


# ══════════════════════════════════════════════════════
# xnn 状态通知（正值 PK）
# ══════════════════════════════════════════════════════


@pytest.mark.asyncio(loop_scope="session")
async def test_positive_pk_xnn_enter_on_loss(app: App, fresh_env):
    """正值 PK — 输家长度跌入 (0, 5] → 进入 xnn 状态，消息含 xnn 通知。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 7.0)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 15.0)

    from nonebot_plugin_impart_plus.bot.handlers.pk import pk_shared_matcher

    with (
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.random.random",
            return_value=0.99,  # USER 必输
        ),
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.get_random_num",
            return_value=4.0,  # USER: 7-4 = 3, 属于 xnn 区间 (0,5]
        ),
    ):
        async with app.test_matcher(pk_shared_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    user_len = await dm.get_jj_length(USER_ID)
    assert 0 < user_len <= 5  # 应处于 xnn 区间


@pytest.mark.asyncio(loop_scope="session")
async def test_positive_pk_xnn_self_exit_on_win(app: App, fresh_env):
    """正值 PK — xnn 玩家赢后长度超过 5 → 退出 xnn 状态。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 3.0)
    # 先标记 xnn
    await dm.update_challenge_status(USER_ID)

    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 15.0)

    from nonebot_plugin_impart_plus.bot.handlers.pk import pk_shared_matcher

    # xnn 胜率减半 0.5*0.5=0.25, 归一化 0.25/(0.25+0.5)≈0.333
    # bonus = max(1, 0.5/0.25) = 2, gain = 4*0.5*2 = 4
    with (
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.random.random",
            return_value=0.01,  # USER 必赢
        ),
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.get_random_num",
            return_value=4.0,  # gain=4, USER: 3+4 = 7 (>5, 退出 xnn)
        ),
    ):
        async with app.test_matcher(pk_shared_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    user_len = await dm.get_jj_length(USER_ID)
    assert user_len > 5  # 已退出 xnn


@pytest.mark.asyncio(loop_scope="session")
async def test_positive_pk_opp_xnn_enter(app: App, fresh_env):
    """正值 PK — 对方因失败长度跌入 (0, 5] → 对方进入 xnn。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 15.0)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 7.0)

    from nonebot_plugin_impart_plus.bot.handlers.pk import pk_shared_matcher

    with (
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.random.random",
            return_value=0.01,  # USER 必赢 → TARGET 输
        ),
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.get_random_num",
            return_value=4.0,  # TARGET: 7-4 = 3, xnn 区间
        ),
    ):
        async with app.test_matcher(pk_shared_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    target_len = await dm.get_jj_length(TARGET_ID)
    assert 0 < target_len <= 5  # 对方进入 xnn


# ══════════════════════════════════════════════════════
# 对方挑战/xnn 补充边界测试
# ══════════════════════════════════════════════════════


@pytest.mark.asyncio(loop_scope="session")
async def test_positive_pk_opp_fall_from_god(app: App, fresh_env):
    """正值 PK — 对方已完成挑战但长度跌回 <25 → 跌落神坛 -5。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 15.0)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 31.0)
    # TARGET 完成过挑战
    await dm.update_challenge_status(TARGET_ID)  # CHALLENGE_COMPLETED

    from nonebot_plugin_impart_plus.bot.handlers.pk import pk_shared_matcher

    with (
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.random.random",
            return_value=0.01,  # USER 必赢 → TARGET 输
        ),
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.get_random_num",
            return_value=8.0,  # TARGET: 31-8 = 23 (<25) → COMPLETED_REDUCE → -5 → 18
        ),
    ):
        async with app.test_matcher(pk_shared_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    target_len = await dm.get_jj_length(TARGET_ID)
    assert target_len == pytest.approx(18.0, abs=0.5)


@pytest.mark.asyncio(loop_scope="session")
async def test_positive_pk_opp_challenge_success(app: App, fresh_env):
    """正值 PK — 对方挑战中且因我方失败长度超 30 → 对方挑战成功。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 15.0)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 28.0)
    await dm.update_challenge_status(TARGET_ID)  # TARGET is_challenging = True

    from nonebot_plugin_impart_plus.bot.handlers.pk import pk_shared_matcher

    with (
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.random.random",
            return_value=0.99,  # USER 必输 → TARGET 赢
        ),
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.get_random_num",
            return_value=8.0,  # TARGET gain = 8*0.5 = 4, TARGET: 28+4 = 32 (>=30)
        ),
    ):
        async with app.test_matcher(pk_shared_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    target_len = await dm.get_jj_length(TARGET_ID)
    assert target_len >= 30


@pytest.mark.asyncio(loop_scope="session")
async def test_positive_pk_opp_xnn_exit(app: App, fresh_env):
    """正值 PK — 对方为 xnn 且赢后长度超 5 → 退出 xnn。"""
    dm, _cd = fresh_env
    await dm.add_new_user(USER_ID)
    await dm.set_jj_length_absolute(USER_ID, 15.0)
    await dm.add_new_user(TARGET_ID)
    await dm.set_jj_length_absolute(TARGET_ID, 3.0)
    await dm.update_challenge_status(TARGET_ID)  # 标记 xnn

    from nonebot_plugin_impart_plus.bot.handlers.pk import pk_shared_matcher

    with (
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.random.random",
            return_value=0.99,  # USER 必输 → TARGET 赢
        ),
        patch(
            "nonebot_plugin_impart_plus.bot.handlers.pk.get_random_num",
            return_value=8.0,  # TARGET: xnn bonus=max(1,0.5/0.25)=2, gain=8*0.5*2=8
        ),
    ):
        async with app.test_matcher(pk_shared_matcher) as ctx:
            bot = ctx.create_bot()
            event = _event()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, ANY_MSG, result=None, at_sender=True)

    target_len = await dm.get_jj_length(TARGET_ID)
    assert target_len > 5  # 已退出 xnn
