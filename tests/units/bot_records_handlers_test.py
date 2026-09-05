from typing import cast

import pytest
from nonebot.exception import FinishedException
from nonebot.matcher import Matcher

from .bot_test_utils import (
    FinishingMatcherStub,
    make_ref_context,
    make_scene_ref,
    make_user_ref,
)


@pytest.mark.parametrize(
    ("total", "self_index", "render_fails"),
    [(32, 11, False), (7, 3, False), (32, 11, True)],
)
async def test_rank_uses_uninfo_user_directory(
    monkeypatch: pytest.MonkeyPatch,
    total: int,
    self_index: int,
    render_fails: bool,
):
    from nonebot_plugin_uninfo import Interface, User
    from nonebot_plugin_uniref import SceneRef, UserRef

    from nonebot_plugin_impart_plus.bot.handlers import records
    from nonebot_plugin_impart_plus.impart.app import (
        RankingEntry,
        RankingOutcome,
        RankingOutcomeType,
    )
    from nonebot_plugin_impart_plus.infra.chart_layout import RankEntry, select_indices

    ranking = [
        RankingEntry(make_user_ref(str(user_id)), float(total - user_id - 2))
        for user_id in range(1, total + 1)
    ]
    app_calls: list[tuple[SceneRef, UserRef]] = []
    user_calls: list[str] = []
    chart_data: list[list[RankEntry]] = []

    async def query_ranking(
        scene_ref: SceneRef,
        user_ref: UserRef,
    ) -> RankingOutcome:
        app_calls.append((scene_ref, user_ref))
        return RankingOutcome(
            RankingOutcomeType.COMPLETED,
            ranking=ranking,
            index=self_index,
        )

    class InterfaceStub:
        async def get_user(self, user_id: str) -> User:
            user_calls.append(user_id)
            if user_id == "2":
                raise RuntimeError("用户目录暂不可用")
            return User(
                id=user_id, nick="同名用户", avatar=f"https://example.com/{user_id}.png"
            )

    async def draw_bar(data: list[RankEntry]) -> bytes:
        chart_data.append(data)
        if render_fails:
            raise RuntimeError("渲染失败")
        return b"png"

    monkeypatch.setattr(records.game_app, "query_ranking", query_ranking)
    monkeypatch.setattr(records.chart_renderer, "render_ranking", draw_bar)
    matcher = FinishingMatcherStub()

    with pytest.raises(FinishedException):
        await records.jjrank(
            cast(Matcher, matcher),
            make_ref_context(scene_id="12345"),
            cast(Interface, InterfaceStub()),
        )

    assert app_calls == [(make_scene_ref("12345"), make_user_ref())]
    expected = [index + 1 for index in select_indices(total, self_index)]
    assert user_calls == [str(rank) for rank in expected]
    assert [entry.rank for entry in chart_data[0]] == expected
    assert [entry.rank for entry in chart_data[0] if entry.is_self] == [self_index + 1]
    assert chart_data[0][0].name == "同名用户"
    assert chart_data[0][-1].name == "同名用户"
    assert chart_data[0][1].name == "2"
    assert chart_data[0][1].avatar_url is None
    assert chart_data[0][0].avatar_url == "https://example.com/1.png"
    assert f"你的排名为{self_index + 1}喵" in matcher.messages[0]
    if render_fails:
        assert matcher.messages == [f"你的排名为{self_index + 1}喵\n图表生成失败"]
        return
    from nonebot_plugin_alconna import AUTO, Image, Text, UniMessage

    assert isinstance(matcher.raw_messages[0], UniMessage)
    assert isinstance(matcher.raw_messages[0][0], Image)
    assert isinstance(matcher.raw_messages[0][1], Text)
    assert matcher.options[0]["fallback"] is AUTO
