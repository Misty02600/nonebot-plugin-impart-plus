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
            random_num=1.25,
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
            random_num=1.25,
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
        "开扣结束喵, 你的小学很满意喵, 扣深了1.25cm喵, 目前深度为3.25cm喵"
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


async def test_query_handler_prefers_typed_mention(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_alconna import At, Match
    from nonebot_plugin_uniref import SceneRef, UserRef

    from nonebot_plugin_impart_plus.bot.handlers import game
    from nonebot_plugin_impart_plus.impart.app import QueryOutcome, QueryOutcomeType
    from nonebot_plugin_impart_plus.impart.core import LengthState

    calls: list[tuple[SceneRef, UserRef, UserRef]] = []

    async def query_user(
        scene_ref: SceneRef,
        requester_ref: UserRef,
        target_ref: UserRef,
    ) -> QueryOutcome:
        calls.append((scene_ref, requester_ref, target_ref))
        return QueryOutcome(
            QueryOutcomeType.COMPLETED,
            length=12.5,
            state=LengthState.NORMAL,
        )

    monkeypatch.setattr(game.game_app, "query_user", query_user)
    matcher = MatcherStub()

    await game.queryjj(
        cast(Matcher, matcher),
        make_ref_context(scene_id="12345"),
        Match(At("user", "67890"), True),
    )

    assert calls == [(make_scene_ref("12345"), make_user_ref(), make_user_ref("67890"))]
    assert len(matcher.messages) == 1
    assert "TA的" in matcher.messages[0]
    assert "12.5cm" in matcher.messages[0]


async def test_query_handler_uses_absolute_depth_for_negative_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_alconna import At, Match
    from nonebot_plugin_uniref import SceneRef, UserRef

    from nonebot_plugin_impart_plus.bot.handlers import game
    from nonebot_plugin_impart_plus.impart.app import QueryOutcome, QueryOutcomeType
    from nonebot_plugin_impart_plus.impart.core import LengthState

    outcomes = iter(
        (
            QueryOutcome(
                QueryOutcomeType.COMPLETED,
                length=-2.5,
                state=LengthState.GIRL,
            ),
            QueryOutcome(
                QueryOutcomeType.COMPLETED,
                length=-30.0,
                state=LengthState.ABYSS_LORD,
            ),
        )
    )

    async def query_user(
        _: SceneRef,
        __: UserRef,
        ___: UserRef,
    ) -> QueryOutcome:
        return next(outcomes)

    monkeypatch.setattr(game.game_app, "query_user", query_user)
    messages: list[str] = []
    for _ in range(2):
        matcher = MatcherStub()
        await game.queryjj(
            cast(Matcher, matcher),
            make_ref_context(scene_id="12345"),
            Match(At("user", "67890"), True),
        )
        messages.extend(matcher.messages)

    assert messages == [
        "TA已经是女孩子啦！\nTA的小学目前深度为2.5cm喵",
        "🕳️深淵の主🕳️\nTA的小学目前深度为30.0cm喵",
    ]


async def test_pk_handler_requires_and_uses_mention(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_alconna import At, Match
    from nonebot_plugin_uniref import SceneRef, UserRef

    from nonebot_plugin_impart_plus.bot.handlers import game
    from nonebot_plugin_impart_plus.impart.app import PkOutcome, PkOutcomeType

    calls: list[tuple[SceneRef, UserRef, UserRef | None]] = []

    async def execute_pk(
        scene_ref: SceneRef,
        attacker_ref: UserRef,
        defender_ref: UserRef | None,
    ) -> PkOutcome:
        calls.append((scene_ref, attacker_ref, defender_ref))
        if defender_ref is None:
            return PkOutcome(PkOutcomeType.MISSING_TARGET)
        return PkOutcome(
            PkOutcomeType.USERS_CREATED,
            created_users=(attacker_ref, defender_ref),
        )

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
            make_user_ref("67890"),
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
    assert calls[-1] == (make_scene_ref("12345"), make_user_ref(), None)
    assert missing_matcher.messages == ["请at你要pk的目标"]


async def test_pk_handler_renders_world_specific_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_alconna import At, Match
    from nonebot_plugin_uniref import SceneRef, UserRef

    from nonebot_plugin_impart_plus.bot.handlers import game
    from nonebot_plugin_impart_plus.impart.app import PkOutcome, PkOutcomeType
    from nonebot_plugin_impart_plus.impart.core import GrowthMode, PkResolution

    current_mode = GrowthMode.LENGTH

    async def execute_pk(
        _: SceneRef,
        __: UserRef,
        ___: UserRef | None,
    ) -> PkOutcome:
        return PkOutcome(PkOutcomeType.WORLD_MISMATCH, mode=current_mode)

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
            resolution=PkResolution(True, 0.75, 1.5),
            attacker_probability=0.49,
        ),
        PkOutcome(
            PkOutcomeType.COMPLETED,
            mode=GrowthMode.DEPTH,
            resolution=PkResolution(True, 0.75, 1.5),
            attacker_status="challenge_started_low_win",
            defender_status="challenge_failed_high_win",
            attacker_probability=0.49,
        ),
        PkOutcome(
            PkOutcomeType.COMPLETED,
            mode=GrowthMode.DEPTH,
            resolution=PkResolution(False, 0.75, 1.5),
            attacker_status="challenge_completed_reduce",
            defender_status="challenge_success_high_win",
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
    assert "TA的小学深度变浅了5cm喵" in result_messages[1]
    assert result_messages[1].endswith("你的胜率现在为49%喵")
    assert result_messages[2].startswith(
        "对决失败喵, 在对面小学的深暗压迫下你的小学变浅了1.5cm喵, 对面加深了0.75cm喵"
    )
    assert "你被深渊拒绝了" in result_messages[2]
    assert "帮助TA完成深渊挑战" in result_messages[2]
    assert "授予TA🎊“深淵の主”🎊称号" in result_messages[2]
    assert result_messages[2].endswith("你的胜率现在为51%喵")


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
            random_num=1.5,
            new_length=-3.5,
        )

    monkeypatch.setattr(game.game_app, "grow_target", grow_target)

    missing_matcher = FinishingMatcherStub()
    with pytest.raises(FinishedException):
        await game.grow_target(
            cast(Matcher, missing_matcher),
            make_ref_context(scene_id="12345"),
            TARGET_GROW_COMMAND.parse("嗦"),
            Match((At("user", "unused"),), False),
        )
    assert missing_matcher.messages == ["请at你要嗦/舔的目标"]

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
