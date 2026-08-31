from typing import cast

import pytest
from nonebot.exception import FinishedException
from nonebot.matcher import Matcher

from .bot_test_utils import FinishingMatcherStub, MatcherStub, make_session


async def test_interaction_with_mention_skips_member_enumeration(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_alconna import At, Match
    from nonebot_plugin_uninfo import Interface, Member, User

    from nonebot_plugin_impart_plus.bot.handlers import interaction
    from nonebot_plugin_impart_plus.impart.app import (
        InteractionGuard,
        InteractionGuardType,
        InteractionResult,
    )

    app_calls: list[tuple[int, int]] = []
    complete_calls: list[tuple[int, int, float]] = []

    async def prepare_interaction(scene_id: int, user_id: int) -> InteractionGuard:
        app_calls.append((scene_id, user_id))
        return InteractionGuard(InteractionGuardType.ALLOWED)

    async def complete_interaction(
        user_id: int,
        target_id: int,
        random_value: float,
    ) -> InteractionResult:
        complete_calls.append((user_id, target_id, random_value))
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
        "群主",
        Match(At("user", "67890"), True),
    )

    assert app_calls == [(12345, 10001)]
    assert complete_calls == [(10001, 67890, 0.75)]
    assert len(matcher.messages) == 1
    assert "目标(67890)" in matcher.messages[0]
    from nonebot_plugin_alconna import AUTO, Image, Text, UniMessage

    assert isinstance(matcher.raw_messages[0], UniMessage)
    assert isinstance(matcher.raw_messages[0][0], Text)
    assert isinstance(matcher.raw_messages[0][1], Image)
    assert matcher.options[0]["fallback"] is AUTO


async def test_interaction_without_member_capability_requests_mention(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_alconna import At, Match
    from nonebot_plugin_uninfo import Interface, Member

    from nonebot_plugin_impart_plus.bot.handlers import interaction
    from nonebot_plugin_impart_plus.impart.app import (
        InteractionGuard,
        InteractionGuardType,
    )

    released: list[int] = []

    async def prepare_interaction(_: int, __: int) -> InteractionGuard:
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
            "群友",
            Match(At("user", "unused"), False),
        )

    assert released == [10001]
    assert matcher.messages == ["当前平台无法获取群成员列表，请明确@目标"]


async def test_interaction_selects_uninfo_owner_and_admin_roles(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_uninfo import Member, Role, User

    from nonebot_plugin_impart_plus.bot.handlers import interaction

    async def get_length(_: int) -> float:
        return 10.0

    monkeypatch.setattr(interaction.game_app, "get_length", get_length)
    members = [
        Member(User(id="10001"), roles=[Role("MEMBER", 1)]),
        Member(User(id="20002"), roles=[Role("OWNER", 100)]),
        Member(User(id="30003"), roles=[Role("ADMINISTRATOR", 10)]),
    ]

    owner_matcher = MatcherStub()
    owner = await interaction.yinpa_identity_handle(
        "群主",
        members,
        "发起者",
        cast(Matcher, owner_matcher),
        10001,
        0.75,
    )
    admin_matcher = MatcherStub()
    admin = await interaction.yinpa_identity_handle(
        "管理",
        members,
        "发起者",
        cast(Matcher, admin_matcher),
        10001,
        0.75,
    )

    assert owner == "20002"
    assert admin == "30003"
    assert owner_matcher.messages == ["现在咱将把群主\n送给发起者色色！"]
    assert admin_matcher.messages == ["现在咱将随机抽取一位幸运管理\n送给发起者色色！"]
