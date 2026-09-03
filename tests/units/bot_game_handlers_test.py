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
    assert "长了1.25cm" in matcher.messages[0]
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
        "开扣结束喵, 你的小学很满意喵, 深了1.25cm喵, 目前深度为3.25cm喵"
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

    async def query_user(
        _: SceneRef,
        __: UserRef,
        ___: UserRef,
    ) -> QueryOutcome:
        return QueryOutcome(
            QueryOutcomeType.COMPLETED,
            length=-2.5,
            state=LengthState.GIRL,
        )

    monkeypatch.setattr(game.game_app, "query_user", query_user)
    matcher = MatcherStub()

    await game.queryjj(
        cast(Matcher, matcher),
        make_ref_context(scene_id="12345"),
        Match(At("user", "67890"), True),
    )

    assert matcher.messages == ["TA已经是女孩子啦！\nTA的小学目前深度为2.5cm喵"]


async def test_pk_handler_requires_and_uses_mention(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_alconna import At
    from nonebot_plugin_uniref import SceneRef, UserRef

    from nonebot_plugin_impart_plus.bot.handlers import game
    from nonebot_plugin_impart_plus.impart.app import PkOutcome, PkOutcomeType

    calls: list[tuple[SceneRef, UserRef, UserRef]] = []

    async def execute_pk(
        scene_ref: SceneRef,
        attacker_ref: UserRef,
        defender_ref: UserRef,
    ) -> PkOutcome:
        calls.append((scene_ref, attacker_ref, defender_ref))
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
            At("user", "67890"),
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


async def test_suo_handler_defaults_to_self(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_alconna import At, Match
    from nonebot_plugin_uniref import SceneRef, UserRef

    from nonebot_plugin_impart_plus.bot.handlers import game
    from nonebot_plugin_impart_plus.impart.app import GrowthOutcome, GrowthOutcomeType

    calls: list[tuple[SceneRef, UserRef, UserRef]] = []

    async def grow_target(
        scene_ref: SceneRef,
        user_ref: UserRef,
        target_ref: UserRef,
    ) -> GrowthOutcome:
        calls.append((scene_ref, user_ref, target_ref))
        return GrowthOutcome(
            GrowthOutcomeType.COMPLETED,
            random_num=1.5,
            new_length=11.5,
        )

    monkeypatch.setattr(game.game_app, "grow_target", grow_target)
    matcher = FinishingMatcherStub()

    with pytest.raises(FinishedException):
        await game.suo(
            cast(Matcher, matcher),
            make_ref_context(scene_id="12345"),
            Match(At("user", "unused"), False),
        )

    assert calls == [(make_scene_ref("12345"), make_user_ref(), make_user_ref())]
    assert "你的" in matcher.messages[0]
