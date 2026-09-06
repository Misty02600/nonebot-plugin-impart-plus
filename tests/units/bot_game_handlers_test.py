from typing import cast

import pytest
from nonebot.exception import FinishedException
from nonebot.matcher import Matcher

from .bot_test_utils import (
    FinishingMatcherStub,
    MatcherStub,
    make_ref_context,
    make_scene_ref,
    make_user_ref,
)


def test_user_at_target_accepts_only_user_mentions() -> None:
    from nonebot.exception import SkippedException
    from nonebot_plugin_alconna import At

    from nonebot_plugin_impart_plus.bot.handlers.shared import user_at_target

    assert user_at_target(At("user", "member-openid")) == "member-openid"
    with pytest.raises(SkippedException):
        user_at_target(At("role", "moderator"))


async def test_growth_handler_uses_uninfo_identity(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_uniref import SceneRef, UserRef

    from nonebot_plugin_impart_plus.bot.handlers import game
    from nonebot_plugin_impart_plus.bot.matchers import SELF_GROW_COMMAND
    from nonebot_plugin_impart_plus.impart.app import GrowthOutcome, GrowthOutcomeType
    from nonebot_plugin_impart_plus.impart.core import GrowthMode

    calls: list[tuple[SceneRef, UserRef, GrowthMode]] = []

    async def grow_self(
        scene_ref: SceneRef,
        user_ref: UserRef,
        mode: GrowthMode,
    ) -> GrowthOutcome:
        calls.append((scene_ref, user_ref, mode))
        return GrowthOutcome(
            GrowthOutcomeType.COMPLETED,
            amount=1.25,
            new_length=11.25,
        )

    monkeypatch.setattr(game.game_app, "grow_self", grow_self)
    matcher = MatcherStub()

    await game.grow_self(
        cast(Matcher, matcher),
        make_ref_context(scene_id="12345"),
        SELF_GROW_COMMAND.parse("打胶"),
    )

    assert calls == [(make_scene_ref("12345"), make_user_ref(), GrowthMode.LENGTH)]
    assert len(matcher.messages) == 1
    assert matcher.messages[0].startswith("开导结束喵")
    assert "导长了1.25cm" in matcher.messages[0]
    assert "目前长度为11.25cm" in matcher.messages[0]

    async def reject_growth(
        _: SceneRef,
        __: UserRef,
        mode: GrowthMode,
    ) -> GrowthOutcome:
        assert mode is GrowthMode.LENGTH
        return GrowthOutcome(GrowthOutcomeType.WRONG_STATE)

    monkeypatch.setattr(game.game_app, "grow_self", reject_growth)
    rejected_matcher = FinishingMatcherStub()
    with pytest.raises(FinishedException):
        await game.grow_self(
            cast(Matcher, rejected_matcher),
            make_ref_context(scene_id="12345"),
            SELF_GROW_COMMAND.parse("打胶"),
        )
    assert rejected_matcher.messages[0].startswith("你没有")
    assert rejected_matcher.messages[0].endswith("喵，打不了胶喵")


async def test_depth_growth_handler_uses_depth_copy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_uniref import SceneRef, UserRef

    from nonebot_plugin_impart_plus.bot.handlers import game
    from nonebot_plugin_impart_plus.bot.matchers import SELF_GROW_COMMAND
    from nonebot_plugin_impart_plus.impart.app import GrowthOutcome, GrowthOutcomeType
    from nonebot_plugin_impart_plus.impart.core import GrowthMode

    calls: list[tuple[SceneRef, UserRef, GrowthMode]] = []

    async def grow_self(
        scene_ref: SceneRef,
        user_ref: UserRef,
        mode: GrowthMode,
    ) -> GrowthOutcome:
        calls.append((scene_ref, user_ref, mode))
        return GrowthOutcome(
            GrowthOutcomeType.COMPLETED,
            amount=1.25,
            new_length=-3.25,
        )

    monkeypatch.setattr(game.game_app, "grow_self", grow_self)
    matcher = FinishingMatcherStub()

    with pytest.raises(FinishedException):
        await game.grow_self(
            cast(Matcher, matcher),
            make_ref_context(scene_id="12345"),
            SELF_GROW_COMMAND.parse("开扣"),
        )

    assert calls == [(make_scene_ref("12345"), make_user_ref(), GrowthMode.DEPTH)]
    assert matcher.messages == [
        "挖矿结束喵, 你的小学很满意喵, 扣深了1.25cm喵, 目前深度为3.25cm喵"
    ]

    async def reject_growth(
        _: SceneRef,
        __: UserRef,
        mode: GrowthMode,
    ) -> GrowthOutcome:
        assert mode is GrowthMode.DEPTH
        return GrowthOutcome(GrowthOutcomeType.WRONG_STATE)

    monkeypatch.setattr(game.game_app, "grow_self", reject_growth)
    rejected_matcher = FinishingMatcherStub()
    with pytest.raises(FinishedException):
        await game.grow_self(
            cast(Matcher, rejected_matcher),
            make_ref_context(scene_id="12345"),
            SELF_GROW_COMMAND.parse("开扣"),
        )
    assert rejected_matcher.messages == ["你没有小学喵，挖不了矿喵"]


async def test_pk_handler_requires_and_uses_mention(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_alconna import At, Match
    from nonebot_plugin_uniref import SceneRef, UserRef

    from nonebot_plugin_impart_plus.bot.handlers import game
    from nonebot_plugin_impart_plus.impart.app import (
        PkOutcome,
        PkOutcomeType,
        PkPreparation,
    )

    calls: list[tuple[SceneRef, UserRef, tuple[UserRef, ...]]] = []

    async def prepare_pk(_: SceneRef, __: UserRef) -> PkPreparation:
        return PkPreparation(True, 1)

    async def execute_pk(
        scene_ref: SceneRef,
        attacker_ref: UserRef,
        defender_refs: tuple[UserRef, ...],
    ) -> PkOutcome:
        calls.append((scene_ref, attacker_ref, defender_refs))
        if not defender_refs:
            return PkOutcome(PkOutcomeType.MISSING_TARGET)
        return PkOutcome(
            PkOutcomeType.USERS_CREATED,
            created_users=(attacker_ref, *defender_refs),
        )

    monkeypatch.setattr(game.game_app, "prepare_pk", prepare_pk)
    monkeypatch.setattr(game.game_app, "execute_pk", execute_pk)
    matcher = FinishingMatcherStub()
    with pytest.raises(FinishedException):
        await game.pk(
            cast(Matcher, matcher),
            make_ref_context(scene_id="12345"),
            Match((At("user", "67890"), At("user", "12345")), True),
        )

    assert calls == [
        (
            make_scene_ref("12345"),
            make_user_ref(),
            (make_user_ref("67890"),),
        )
    ]
    assert len(matcher.messages) == 1
    assert matcher.messages[0].startswith("你们还没有")
    assert "目前长度都是10cm喵" in matcher.messages[0]

    missing_matcher = FinishingMatcherStub()
    with pytest.raises(FinishedException):
        await game.pk(
            cast(Matcher, missing_matcher),
            make_ref_context(scene_id="12345"),
            Match((At("user", "unused"),), False),
        )
    assert len(calls) == 1
    assert missing_matcher.messages == ["请艾特你要pk的目标"]


async def test_pk_handler_selects_unlocked_window_without_backfill(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_alconna import At, Match
    from nonebot_plugin_uniref import SceneRef, UserRef

    from nonebot_plugin_impart_plus.bot.handlers import game
    from nonebot_plugin_impart_plus.impart.app import (
        PkOutcome,
        PkOutcomeType,
        PkPreparation,
    )

    max_targets = 2
    calls: list[tuple[UserRef, ...]] = []

    async def prepare_pk(_: SceneRef, __: UserRef) -> PkPreparation:
        return PkPreparation(True, max_targets)

    async def execute_pk(
        _: SceneRef,
        __: UserRef,
        target_refs: tuple[UserRef, ...],
    ) -> PkOutcome:
        calls.append(target_refs)
        return PkOutcome(PkOutcomeType.WORLD_MISMATCH)

    monkeypatch.setattr(game.game_app, "prepare_pk", prepare_pk)
    monkeypatch.setattr(game.game_app, "execute_pk", execute_pk)

    for targets in (
        (At("user", "1"), At("user", "1"), At("user", "2")),
        (At("user", "1"), At("user", "2"), At("user", "3")),
    ):
        with pytest.raises(FinishedException):
            await game.pk(
                cast(Matcher, FinishingMatcherStub()),
                make_ref_context(),
                Match(targets, True),
            )

    max_targets = 1
    with pytest.raises(FinishedException):
        await game.pk(
            cast(Matcher, FinishingMatcherStub()),
            make_ref_context(),
            Match((At("user", "1"), At("role", "ignored")), True),
        )

    assert calls == [
        (make_user_ref("1"),),
        (make_user_ref("1"), make_user_ref("2")),
        (make_user_ref("1"),),
    ]

    from nonebot.exception import SkippedException

    for max_targets in (3, 4):
        targets = tuple(At("user", str(index)) for index in range(max_targets))
        for selected, expected in (
            (
                (*targets, At("role", "ignored")),
                tuple(make_user_ref(str(i)) for i in range(max_targets)),
            ),
            (
                (targets[0], *targets),
                tuple(make_user_ref(str(i)) for i in range(max_targets - 1)),
            ),
        ):
            with pytest.raises(FinishedException):
                await game.pk(
                    cast(Matcher, FinishingMatcherStub()),
                    make_ref_context(),
                    Match(selected, True),
                )
            assert calls[-1] == expected
        count = len(calls)
        with pytest.raises(SkippedException):
            await game.pk(
                cast(Matcher, FinishingMatcherStub()),
                make_ref_context(),
                Match((At("role", "selected"), *targets), True),
            )
        assert len(calls) == count


async def test_pk_handler_renders_world_specific_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_alconna import At, Match
    from nonebot_plugin_uniref import SceneRef, UserRef

    from nonebot_plugin_impart_plus.bot.handlers import game
    from nonebot_plugin_impart_plus.impart.app import (
        PkOutcome,
        PkOutcomeType,
        PkPreparation,
        PkTargetOutcome,
    )
    from nonebot_plugin_impart_plus.impart.core import CHALLENGE_TIERS, GrowthMode

    current_mode = GrowthMode.LENGTH

    async def prepare_pk(_: SceneRef, __: UserRef) -> PkPreparation:
        return PkPreparation(True, 1)

    async def execute_pk(
        _: SceneRef,
        __: UserRef,
        ___: tuple[UserRef, ...],
    ) -> PkOutcome:
        return PkOutcome(PkOutcomeType.WORLD_MISMATCH, mode=current_mode)

    monkeypatch.setattr(game.game_app, "prepare_pk", prepare_pk)
    monkeypatch.setattr(game.game_app, "execute_pk", execute_pk)
    monkeypatch.setattr(game, "choice", lambda _: "牛牛")
    mismatch_messages: list[str] = []
    for mode in (GrowthMode.LENGTH, GrowthMode.DEPTH):
        current_mode = mode
        matcher = FinishingMatcherStub()
        with pytest.raises(FinishedException):
            await game.pk(
                cast(Matcher, matcher),
                make_ref_context(scene_id="12345"),
                Match((At("user", "67890"),), True),
            )
        mismatch_messages.extend(matcher.messages)

    assert mismatch_messages[0] == "你只能和有牛牛的人pk！"
    assert mismatch_messages[1] == "你只能和有小学的人pk！"

    outcomes = (
        PkOutcome(
            PkOutcomeType.COMPLETED,
            mode=GrowthMode.LENGTH,
            won=True,
            attacker_change=0.75,
            targets=(PkTargetOutcome(-1.5),),
            attacker_probability=0.49,
        ),
        PkOutcome(
            PkOutcomeType.COMPLETED,
            mode=GrowthMode.DEPTH,
            won=True,
            attacker_change=-0.75,
            targets=(
                PkTargetOutcome(
                    1.5,
                    "challenge_failed_high_win",
                    CHALLENGE_TIERS[1],
                ),
            ),
            attacker_status="challenge_started_low_win",
            attacker_challenge=CHALLENGE_TIERS[1],
            attacker_probability=0.49,
        ),
        PkOutcome(
            PkOutcomeType.COMPLETED,
            mode=GrowthMode.DEPTH,
            won=False,
            attacker_change=1.5,
            targets=(
                PkTargetOutcome(
                    -0.75,
                    "challenge_success_high_win",
                    CHALLENGE_TIERS[2],
                ),
            ),
            attacker_status="challenge_completed_reduce",
            attacker_challenge=CHALLENGE_TIERS[2],
            attacker_probability=0.51,
        ),
    )
    result_messages: list[str] = []
    for handler, outcome in zip(
        (game._handle_pk_win, game._handle_pk_win, game._handle_pk_loss),
        outcomes,
        strict=True,
    ):
        matcher = FinishingMatcherStub()
        with pytest.raises(FinishedException):
            await handler(cast(Matcher, matcher), outcome)
        result_messages.extend(matcher.messages)

    assert result_messages[0] == (
        "对决胜利喵, 你的牛牛增加了0.75cm喵, 对面则在你的阴影笼罩下减小了1.5cm喵"
        "\n你的胜率现在为49%喵"
    )
    assert result_messages[1].startswith(
        "对决胜利喵, 你的小学加深了0.75cm喵, 对面则在你小学的深暗压迫下变浅了1.5cm喵"
    )
    assert "已为你开启🕳️“深渊试炼”🕳️" in result_messages[1]
    assert "TA的深渊挑战失败" in result_messages[1]
    assert "深度超过300cm" in result_messages[1]
    assert "深度提升至320cm" in result_messages[1]
    assert "TA的小学深度变浅了20cm喵" in result_messages[1]
    assert result_messages[1].endswith("你的胜率现在为49%喵")
    assert result_messages[2].startswith(
        "对决失败喵, 在对面小学的深暗压迫下你的小学变浅了1.5cm喵, 对面加深了0.75cm喵"
    )
    assert "你被深渊拒绝了" in result_messages[2]
    assert "失去了称号「深淵の主」" in result_messages[2]
    assert "变浅了50cm" in result_messages[2]
    assert "深度超过1050cm" in result_messages[2]
    assert "帮助TA完成深渊挑战" in result_messages[2]
    assert "授予TA🎊“深淵の主”🎊称号" in result_messages[2]
    assert result_messages[2].endswith("你的胜率现在为51%喵")

    dual = PkOutcome(
        PkOutcomeType.COMPLETED,
        mode=GrowthMode.LENGTH,
        won=True,
        attacker_change=1.2,
        targets=(
            PkTargetOutcome(-0.6),
            PkTargetOutcome(-0.3),
        ),
        attacker_probability=0.49,
    )
    dual_matcher = FinishingMatcherStub()
    with pytest.raises(FinishedException):
        await game._handle_pk_win(cast(Matcher, dual_matcher), dual)
    assert "目标1则在你的阴影笼罩下减小了0.6cm喵" in dual_matcher.messages[0]
    assert "目标2则在你的阴影笼罩下减小了0.3cm喵" in dual_matcher.messages[0]


async def test_game_reply_notifies_actual_unlocked_member_after_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from unittest.mock import AsyncMock

    from nonebot_plugin_alconna import At, UniMessage

    from nonebot_plugin_impart_plus.bot.handlers import game
    from nonebot_plugin_impart_plus.bot.matchers import SELF_GROW_COMMAND
    from nonebot_plugin_impart_plus.impart.app import (
        GrowthOutcome,
        GrowthOutcomeType,
        PkOutcome,
        PkOutcomeType,
        PkTargetOutcome,
    )
    from nonebot_plugin_impart_plus.impart.core import CHALLENGE_TIERS, GrowthMode

    for mode, won, members in (
        (GrowthMode.LENGTH, True, {make_user_ref(): 1}),
        (GrowthMode.LENGTH, False, {make_user_ref("2"): 2, make_user_ref("3"): 3}),
        (GrowthMode.DEPTH, True, {make_user_ref(): 1}),
        (GrowthMode.DEPTH, False, {make_user_ref("2"): 2, make_user_ref("3"): 3}),
    ):
        outcome = PkOutcome(
            PkOutcomeType.COMPLETED,
            mode=mode,
            won=won,
            attacker_change=0.5 if won else -2.0,
            attacker_status="challenge_success_high_win" if won else "",
            attacker_challenge=CHALLENGE_TIERS[0] if won else None,
            targets=tuple(
                PkTargetOutcome(
                    -2.0 if won else 0.25 * tier,
                    "" if won else "challenge_success_high_win",
                    None if won else CHALLENGE_TIERS[tier - 1],
                )
                for tier in members.values()
            ),
            attacker_probability=0.4875 if won else 0.51,
            unlocked_users=members,
        )
        matcher = FinishingMatcherStub()
        handler = game._handle_pk_win if won else game._handle_pk_loss
        with pytest.raises(FinishedException):
            await handler(cast(Matcher, matcher), outcome)
        assert len(matcher.raw_messages) == len(members) + 1
        assert "对决" in matcher.messages[0]
        for (member, tier), notification, options in zip(
            members.items(),
            matcher.raw_messages[1:],
            matcher.options[1:],
            strict=True,
        ):
            assert isinstance(notification, UniMessage)
            assert notification[0] == At("user", member.id)
            dimension = "深度" if mode is GrowthMode.DEPTH else "长度"
            growth = "将翻倍" if tier == 1 else f"将提升至{tier + 1}倍"
            assert f"你的任何基础{dimension}变动{growth}！" in str(notification)
            count = ("两", "三", "四")[tier - 1]
            assert f"PK现在最多可以指定{count}个目标了！" in str(notification)
            assert ("现在可以使用指令「夺舍」了！" in str(notification)) == (
                mode is GrowthMode.DEPTH and tier == 1
            )
            assert "at_sender" not in options

    monkeypatch.setattr(
        game.game_app,
        "grow_self",
        AsyncMock(
            return_value=GrowthOutcome(
                GrowthOutcomeType.COOLING_DOWN,
                remaining=10.0,
            )
        ),
    )
    matcher = FinishingMatcherStub()
    with pytest.raises(FinishedException):
        await game.grow_self(
            cast(Matcher, matcher), make_ref_context(), SELF_GROW_COMMAND.parse("开扣")
        )
    assert len(matcher.messages) == 1
    assert "请等待10.0秒" in matcher.messages[0]

    failing_matcher = FinishingMatcherStub()
    monkeypatch.setattr(
        failing_matcher, "send", AsyncMock(side_effect=RuntimeError("send failed"))
    )
    with pytest.raises(RuntimeError, match="send failed"):
        await game._finish_game_reply(
            cast(Matcher, failing_matcher),
            "result",
            unlocked_users={make_user_ref(): 1},
            mode=GrowthMode.DEPTH,
        )
    assert failing_matcher.messages == []


async def test_target_growth_handler_requires_target_and_uses_mode(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_alconna import At, Match
    from nonebot_plugin_uniref import SceneRef, UserRef

    from nonebot_plugin_impart_plus.bot.handlers import game
    from nonebot_plugin_impart_plus.bot.matchers import TARGET_GROW_COMMAND
    from nonebot_plugin_impart_plus.impart.app import GrowthOutcome, GrowthOutcomeType
    from nonebot_plugin_impart_plus.impart.core import GrowthMode

    calls: list[tuple[SceneRef, UserRef, UserRef | None, GrowthMode]] = []

    async def grow_target(
        scene_ref: SceneRef,
        user_ref: UserRef,
        target_ref: UserRef | None,
        mode: GrowthMode,
    ) -> GrowthOutcome:
        calls.append((scene_ref, user_ref, target_ref, mode))
        if target_ref is None:
            return GrowthOutcome(GrowthOutcomeType.MISSING_TARGET)
        if target_ref == user_ref:
            return GrowthOutcome(GrowthOutcomeType.SELF_TARGET)
        return GrowthOutcome(
            GrowthOutcomeType.COMPLETED,
            amount=1.5,
            new_length=-3.5,
        )

    monkeypatch.setattr(game.game_app, "grow_target", grow_target)

    for command in ("嗦", "舔"):
        missing_matcher = FinishingMatcherStub()
        with pytest.raises(FinishedException):
            await game.grow_target(
                cast(Matcher, missing_matcher),
                make_ref_context(scene_id="12345"),
                TARGET_GROW_COMMAND.parse(command),
                Match((At("user", "unused"),), False),
            )
        assert missing_matcher.messages == [f"请艾特你要{command}的目标"]

    self_messages: list[str] = []
    for command in ("嗦", "舔"):
        matcher = FinishingMatcherStub()
        with pytest.raises(FinishedException):
            await game.grow_target(
                cast(Matcher, matcher),
                make_ref_context(scene_id="12345"),
                TARGET_GROW_COMMAND.parse(command),
                Match((At("user", "10001"),), True),
            )
        self_messages.extend(matcher.messages)
    assert self_messages[0].startswith("你嗦不到自己的")
    assert self_messages[0].endswith("喵")
    assert self_messages[1] == "你舔不到自己的小学喵"

    matcher = FinishingMatcherStub()
    with pytest.raises(FinishedException):
        await game.grow_target(
            cast(Matcher, matcher),
            make_ref_context(scene_id="12345"),
            TARGET_GROW_COMMAND.parse("舔"),
            Match((At("user", "67890"), At("user", "12345")), True),
        )
    assert calls[-1] == (
        make_scene_ref("12345"),
        make_user_ref(),
        make_user_ref("67890"),
        GrowthMode.DEPTH,
    )
    assert matcher.messages == ["TA的小学很满意喵, 舔深了1.5cm喵, 目前深度为3.5cm喵"]


async def test_target_growth_handler_uses_mode_specific_failure_copy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_alconna import At, Match
    from nonebot_plugin_uniref import SceneRef, UserRef

    from nonebot_plugin_impart_plus.bot.handlers import game
    from nonebot_plugin_impart_plus.bot.matchers import TARGET_GROW_COMMAND
    from nonebot_plugin_impart_plus.impart.app import GrowthOutcome, GrowthOutcomeType
    from nonebot_plugin_impart_plus.impart.core import GrowthMode

    outcome = GrowthOutcome(GrowthOutcomeType.WRONG_STATE)

    async def grow_target(
        _: SceneRef,
        __: UserRef,
        ___: UserRef | None,
        ____: GrowthMode,
    ) -> GrowthOutcome:
        return outcome

    monkeypatch.setattr(game.game_app, "grow_target", grow_target)
    monkeypatch.setattr(game, "choice", lambda _: "牛牛")
    cases = [
        ("嗦", GrowthOutcome(GrowthOutcomeType.WRONG_STATE)),
        ("舔", GrowthOutcome(GrowthOutcomeType.WRONG_STATE)),
        ("舔", GrowthOutcome(GrowthOutcomeType.COOLING_DOWN, remaining=12.5)),
        ("嗦", GrowthOutcome(GrowthOutcomeType.ACTOR_CHALLENGING)),
        ("舔", GrowthOutcome(GrowthOutcomeType.ACTOR_CHALLENGING)),
        ("嗦", GrowthOutcome(GrowthOutcomeType.TARGET_CHALLENGING)),
        ("舔", GrowthOutcome(GrowthOutcomeType.TARGET_CHALLENGING)),
    ]
    messages: list[str] = []
    for command, current_outcome in cases:
        outcome = current_outcome
        matcher = FinishingMatcherStub()
        with pytest.raises(FinishedException):
            await game.grow_target(
                cast(Matcher, matcher),
                make_ref_context(scene_id="12345"),
                TARGET_GROW_COMMAND.parse(command),
                Match((At("user", "67890"),), True),
            )
        messages.extend(matcher.messages)

    assert messages[0].startswith("TA没有")
    assert messages[0].endswith("喵，嗦不了喵")
    assert messages[1:] == [
        "TA没有小学喵，舔不了喵",
        "你已经舔不动了喵, 请等待12.5秒后再舔喵",
        "你的牛牛长度在任务范围内，不允许嗦，请专心与群友pk！",
        "你的小学深度在任务范围内，不允许舔，请专心与群友pk！",
        "TA的牛牛长度在任务范围内，不准嗦！请专心与群友pk！",
        "TA的小学深度在任务范围内，不准舔！请专心与群友pk！",
    ]
