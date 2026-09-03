from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest
from nonebot.exception import FinishedException
from nonebot.matcher import Matcher

from .bot_test_utils import (
    FinishingMatcherStub,
    MatcherStub,
    make_ref_context,
    make_scene_ref,
    make_session,
    make_user_ref,
)


async def test_interaction_with_mention_skips_member_enumeration(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_alconna import At, Match
    from nonebot_plugin_uninfo import Interface, Member, User
    from nonebot_plugin_uniref import SceneRef, UserRef

    from nonebot_plugin_impart_plus.bot.handlers import interaction
    from nonebot_plugin_impart_plus.impart.app import (
        InteractionGuard,
        InteractionGuardType,
        InteractionResult,
    )

    app_calls: list[tuple[SceneRef, UserRef]] = []
    complete_calls: list[tuple[UserRef, UserRef, float]] = []

    async def prepare_interaction(
        scene_ref: SceneRef,
        user_ref: UserRef,
    ) -> InteractionGuard:
        app_calls.append((scene_ref, user_ref))
        return InteractionGuard(InteractionGuardType.ALLOWED)

    async def complete_interaction(
        user_ref: UserRef,
        target_ref: UserRef,
        random_value: float,
    ) -> InteractionResult:
        complete_calls.append((user_ref, target_ref, random_value))
        return InteractionResult(
            reversed=False,
            ejaculation=2.5,
            today_total=8.0,
            seconds=3,
        )

    async def no_sleep(_: float) -> None:
        return None

    class InterfaceStub:
        async def get_members(self, *_: object) -> list[Member]:
            raise AssertionError("显式 At 不应枚举成员")

        async def get_member(self, *_: object) -> Member:
            return Member(
                User(
                    id="67890",
                    nick="目标",
                    avatar="https://example.com/avatar.png",
                )
            )

        async def get_user(self, user_id: str) -> User:
            return User(id=user_id, nick="目标")

    monkeypatch.setattr(
        interaction.game_app,
        "prepare_interaction",
        prepare_interaction,
    )
    monkeypatch.setattr(interaction.game_app, "roll_interaction", lambda: 0.75)
    monkeypatch.setattr(
        interaction.game_app,
        "complete_interaction",
        complete_interaction,
    )
    monkeypatch.setattr(interaction.asyncio, "sleep", no_sleep)
    matcher = MatcherStub()

    await interaction.yinpa(
        cast(Matcher, matcher),
        make_session(1, "12345"),
        cast(Interface, InterfaceStub()),
        make_ref_context(scene_id="12345"),
        "群友",
        Match(At("user", "67890"), True),
    )

    assert app_calls == [(make_scene_ref("12345"), make_user_ref())]
    assert complete_calls == [(make_user_ref(), make_user_ref("67890"), 0.75)]
    assert len(matcher.messages) == 1
    assert "目标(67890)" in matcher.messages[0]
    from nonebot_plugin_alconna import AUTO, Image, Text, UniMessage

    assert isinstance(matcher.raw_messages[0], UniMessage)
    assert isinstance(matcher.raw_messages[0][0], Text)
    assert isinstance(matcher.raw_messages[0][1], Image)
    assert matcher.options[0]["fallback"] is AUTO


async def test_non_user_mention_skips_before_interaction_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot.exception import SkippedException
    from nonebot_plugin_alconna import At, Match
    from nonebot_plugin_uninfo import Interface

    from nonebot_plugin_impart_plus.bot.handlers import interaction

    prepare_interaction = AsyncMock()
    monkeypatch.setattr(
        interaction.game_app,
        "prepare_interaction",
        prepare_interaction,
    )
    target = At("role", "67890")

    with pytest.raises(SkippedException):
        await interaction.yinpa(
            cast(Matcher, MatcherStub()),
            make_session(1, "12345"),
            cast(Interface, object()),
            make_ref_context(scene_id="12345"),
            "群友",
            Match(target, True),
        )

    prepare_interaction.assert_not_awaited()


async def test_interaction_without_member_capability_requests_mention(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_alconna import At, Match
    from nonebot_plugin_uninfo import Interface, Member
    from nonebot_plugin_uniref import SceneRef, UserRef

    from nonebot_plugin_impart_plus.bot.handlers import interaction
    from nonebot_plugin_impart_plus.impart.app import (
        InteractionGuard,
        InteractionGuardType,
    )

    released: list[UserRef] = []

    async def prepare_interaction(_: SceneRef, __: UserRef) -> InteractionGuard:
        return InteractionGuard(InteractionGuardType.ALLOWED)

    class InterfaceStub:
        async def get_members(self, *_: object) -> list[Member]:
            return []

    monkeypatch.setattr(
        interaction.game_app,
        "prepare_interaction",
        prepare_interaction,
    )
    monkeypatch.setattr(
        interaction.game_app,
        "release_interaction_cooldown",
        released.append,
    )
    matcher = FinishingMatcherStub()

    with pytest.raises(FinishedException):
        await interaction.yinpa(
            cast(Matcher, matcher),
            make_session(1, "12345"),
            cast(Interface, InterfaceStub()),
            make_ref_context(scene_id="12345"),
            "群友",
            Match(At("user", "unused"), False),
        )

    assert released == [make_user_ref()]
    assert matcher.messages == ["请@指定目标"]


async def test_interaction_selects_uninfo_owner_and_admin_roles(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_uninfo import Member, Role, User
    from nonebot_plugin_uniref import UserRef

    from nonebot_plugin_impart_plus.bot.handlers import interaction

    async def get_length(_: UserRef) -> float:
        return 10.0

    monkeypatch.setattr(interaction.game_app, "get_length", get_length)
    members = [
        Member(User(id="10001"), roles=[Role("MEMBER", 1)]),
        Member(User(id="20002"), roles=[Role("OWNER", 100)]),
        Member(User(id="30003"), roles=[Role("ADMINISTRATOR", 10)]),
    ]

    owner = interaction.select_interaction_target(
        "群主",
        members,
        "10001",
    )
    admin = interaction.select_interaction_target(
        "管理",
        members,
        "10001",
    )

    assert owner == "20002"
    assert admin == "30003"

    owner_matcher = MatcherStub()
    await interaction.send_interaction_prompt(
        "群主",
        "发起者",
        cast(Matcher, owner_matcher),
        make_user_ref(),
        0.75,
    )
    admin_matcher = MatcherStub()
    await interaction.send_interaction_prompt(
        "管理",
        "发起者",
        cast(Matcher, admin_matcher),
        make_user_ref(),
        0.75,
    )

    assert owner_matcher.messages == ["现在咱将把群主\n送给发起者色色！"]
    assert admin_matcher.messages == ["现在咱将随机抽取一位幸运管理\n送给发起者色色！"]


async def test_automatic_target_rolls_before_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_alconna import At, Match
    from nonebot_plugin_uninfo import Interface, Member, User

    from nonebot_plugin_impart_plus.bot.handlers import interaction
    from nonebot_plugin_impart_plus.impart.app import (
        InteractionGuard,
        InteractionGuardType,
    )

    class SelectionReached(Exception):
        pass

    calls: list[str] = []
    prepare_interaction = AsyncMock(
        return_value=InteractionGuard(InteractionGuardType.ALLOWED)
    )

    def roll_interaction() -> float:
        calls.append("roll")
        return 0.75

    def select_interaction_target(
        kind: str,
        available_members: list[Member],
        uid: str,
    ) -> None:
        calls.append("select")
        assert kind == "群友"
        assert available_members
        assert uid == "10001"
        raise SelectionReached

    class InterfaceStub:
        async def get_members(self, *_: object) -> list[Member]:
            return [Member(User(id="20002"))]

    monkeypatch.setattr(
        interaction.game_app,
        "prepare_interaction",
        prepare_interaction,
    )
    monkeypatch.setattr(interaction.game_app, "roll_interaction", roll_interaction)
    monkeypatch.setattr(
        interaction,
        "select_interaction_target",
        select_interaction_target,
    )

    with pytest.raises(SelectionReached):
        await interaction.yinpa(
            cast(Matcher, MatcherStub()),
            make_session(1, "12345"),
            cast(Interface, InterfaceStub()),
            make_ref_context(scene_id="12345"),
            "群友",
            Match(At("user", "unused"), False),
        )

    assert calls == ["roll", "select"]


async def test_member_query_exception_is_logged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_uninfo import Interface, Member

    from nonebot_plugin_impart_plus.bot.handlers import shared

    failure = RuntimeError("member query failed")

    class InterfaceStub:
        async def get_members(self, *_: object) -> list[Member]:
            raise failure

    session = make_session(1, "12345")
    logger = Mock()
    monkeypatch.setattr(shared, "logger", logger)

    members = await shared.get_members_or_empty(
        cast(Interface, InterfaceStub()),
        session,
    )

    assert members == []
    logger.opt.assert_called_once_with(exception=failure)
    logger.opt.return_value.warning.assert_called_once_with(
        "获取成员列表失败: adapter={}, scene_type={}",
        session.adapter,
        session.scene.type.name,
    )


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("群主", "没找到群主"),
        ("管理", "没找到管理"),
    ],
)
async def test_role_target_ignores_mention_and_uses_role_message(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    expected: str,
) -> None:
    from nonebot_plugin_alconna import At, Match
    from nonebot_plugin_uninfo import Interface, Member, Role, User
    from nonebot_plugin_uniref import SceneRef, UserRef

    from nonebot_plugin_impart_plus.bot.handlers import interaction
    from nonebot_plugin_impart_plus.impart.app import (
        InteractionGuard,
        InteractionGuardType,
    )

    released: list[UserRef] = []

    async def prepare_interaction(_: SceneRef, __: UserRef) -> InteractionGuard:
        return InteractionGuard(InteractionGuardType.ALLOWED)

    class InterfaceStub:
        async def get_members(self, *_: object) -> list[Member]:
            return [Member(User(id="20002"), roles=[Role("MEMBER", 1)])]

    monkeypatch.setattr(
        interaction.game_app,
        "prepare_interaction",
        prepare_interaction,
    )
    monkeypatch.setattr(
        interaction.game_app,
        "release_interaction_cooldown",
        released.append,
    )
    matcher = FinishingMatcherStub()

    with pytest.raises(FinishedException):
        await interaction.yinpa(
            cast(Matcher, matcher),
            make_session(1, "12345"),
            cast(Interface, InterfaceStub()),
            make_ref_context(scene_id="12345"),
            kind,
            Match(At("user", "67890"), True),
        )

    assert released == [make_user_ref()]
    assert matcher.messages == [expected]


@pytest.mark.parametrize(
    ("kind", "role"),
    [
        ("群主", "OWNER"),
        ("管理", "ADMINISTRATOR"),
    ],
)
async def test_role_target_self_uses_global_self_message(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    role: str,
) -> None:
    from nonebot_plugin_alconna import At, Match
    from nonebot_plugin_uninfo import Interface, Member, Role, User
    from nonebot_plugin_uniref import SceneRef, UserRef

    from nonebot_plugin_impart_plus.bot.handlers import interaction
    from nonebot_plugin_impart_plus.impart.app import (
        InteractionGuard,
        InteractionGuardType,
    )

    released: list[UserRef] = []

    async def prepare_interaction(_: SceneRef, __: UserRef) -> InteractionGuard:
        return InteractionGuard(InteractionGuardType.ALLOWED)

    class InterfaceStub:
        async def get_members(self, *_: object) -> list[Member]:
            return [Member(User(id="10001"), roles=[Role(role, 100)])]

    monkeypatch.setattr(
        interaction.game_app,
        "prepare_interaction",
        prepare_interaction,
    )
    monkeypatch.setattr(
        interaction.game_app,
        "release_interaction_cooldown",
        released.append,
    )
    matcher = FinishingMatcherStub()

    with pytest.raises(FinishedException):
        await interaction.yinpa(
            cast(Matcher, matcher),
            make_session(1, "12345"),
            cast(Interface, InterfaceStub()),
            make_ref_context(scene_id="12345"),
            kind,
            Match(At("user", "unused"), False),
        )

    assert released == [make_user_ref()]
    assert matcher.messages == ["你透你自己?"]


async def test_explicit_self_target_uses_global_self_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_alconna import At, Match
    from nonebot_plugin_uninfo import Interface, Member
    from nonebot_plugin_uniref import SceneRef, UserRef

    from nonebot_plugin_impart_plus.bot.handlers import interaction
    from nonebot_plugin_impart_plus.impart.app import (
        InteractionGuard,
        InteractionGuardType,
    )

    released: list[UserRef] = []

    async def prepare_interaction(_: SceneRef, __: UserRef) -> InteractionGuard:
        return InteractionGuard(InteractionGuardType.ALLOWED)

    class InterfaceStub:
        async def get_members(self, *_: object) -> list[Member]:
            raise AssertionError("显式 At 不应枚举成员")

    monkeypatch.setattr(
        interaction.game_app,
        "prepare_interaction",
        prepare_interaction,
    )
    monkeypatch.setattr(
        interaction.game_app,
        "release_interaction_cooldown",
        released.append,
    )
    matcher = FinishingMatcherStub()
    target = At("user", "10001")

    with pytest.raises(FinishedException):
        await interaction.yinpa(
            cast(Matcher, matcher),
            make_session(1, "12345"),
            cast(Interface, InterfaceStub()),
            make_ref_context(scene_id="12345"),
            "群友",
            Match(target, True),
        )

    assert released == [make_user_ref()]
    assert matcher.messages == ["你透你自己?"]
