from pathlib import Path
from typing import cast

from nonebot import get_plugin
from nonebot.plugin import inherit_supported_adapters
from nonebug import App


def test_plugin_metadata(app: App):
    import nonebot_plugin_impart_plus
    from nonebot_plugin_impart_plus import __plugin_meta__
    from nonebot_plugin_impart_plus.bot.dependencies import plugin_config
    from nonebot_plugin_impart_plus.bot.handlers.game import pk
    from nonebot_plugin_impart_plus.config import Config

    assert __plugin_meta__.name == "nonebot-plugin-impart-plus"
    assert __plugin_meta__.description == "NoneBot2 银趴插件 Plus"
    assert "初始胜率为50%" in __plugin_meta__.usage
    assert "[透|日|榨][群友|管理|群主]" in __plugin_meta__.usage
    assert "[开扣|挖矿]" in __plugin_meta__.usage
    assert "可能触发特殊事件" in __plugin_meta__.usage
    assert "[银趴|impart][查询|查询历史|查询全部]" in __plugin_meta__.usage
    assert "[银趴|impart][开启|禁止|帮助]" in __plugin_meta__.usage
    assert __plugin_meta__.type == "application"
    assert nonebot_plugin_impart_plus.__file__ is not None
    expected_package = (
        Path(__file__).parents[2] / "src" / "nonebot_plugin_impart_plus" / "__init__.py"
    )
    assert (
        Path(nonebot_plugin_impart_plus.__file__).resolve()
        == expected_package.resolve()
    )
    assert isinstance(plugin_config, Config)
    assert pk is not None
    assert get_plugin("nonebot_plugin_alconna") is not None
    assert get_plugin("nonebot_plugin_orm") is not None
    assert get_plugin("nonebot_plugin_uninfo") is not None
    assert get_plugin("nonebot_plugin_uniref") is not None
    assert __plugin_meta__.supported_adapters == inherit_supported_adapters(
        "nonebot_plugin_alconna",
        "nonebot_plugin_uninfo",
        "nonebot_plugin_uniref",
    )
    assert __plugin_meta__.supported_adapters == {
        "nonebot.adapters.discord",
        "nonebot.adapters.feishu",
        "nonebot.adapters.milky",
        "nonebot.adapters.onebot.v11",
        "nonebot.adapters.qq",
        "nonebot.adapters.telegram",
    }


def test_alconna_matcher_registration(app: App):
    from nonebot import get_plugin
    from nonebot_plugin_alconna import AlconnaMatcher

    from nonebot_plugin_impart_plus.bot import handlers
    from nonebot_plugin_impart_plus.bot.matchers import (
        impart_matcher,
        interaction_matcher,
        pk_matcher,
        possession_matcher,
        rank_matcher,
        self_growth_matcher,
        target_growth_matcher,
    )

    plugin = get_plugin("nonebot_plugin_impart_plus")

    assert plugin is not None
    assert len(plugin.matcher) == 11
    assert all(issubclass(matcher, AlconnaMatcher) for matcher in plugin.matcher)

    dispatch_matchers: dict[str, type[AlconnaMatcher]] = {}
    for matcher in plugin.matcher:
        basepath = getattr(matcher, "basepath", None)
        if basepath in {"enabled", "query", "history_query", "help"}:
            dispatch_matchers[basepath] = cast(type[AlconnaMatcher], matcher)
    assert set(dispatch_matchers) == {"enabled", "query", "history_query", "help"}
    assert dispatch_matchers["enabled"].priority == 10
    assert dispatch_matchers["query"].priority == 20
    assert dispatch_matchers["history_query"].priority == 20
    assert dispatch_matchers["help"].priority == 20
    assert len(dispatch_matchers["enabled"].permission.checkers) == 2
    assert len(dispatch_matchers["query"].permission.checkers) == 0
    assert len(dispatch_matchers["history_query"].permission.checkers) == 0
    assert len(dispatch_matchers["help"].permission.checkers) == 0
    assert all(matcher.block for matcher in dispatch_matchers.values())

    public_matchers = (
        pk_matcher,
        possession_matcher,
        self_growth_matcher,
        target_growth_matcher,
        rank_matcher,
        interaction_matcher,
        impart_matcher,
    )
    assert all(len(matcher.permission.checkers) == 2 for matcher in public_matchers)

    assert interaction_matcher.priority == 20
    assert interaction_matcher.block is True
    assert len(interaction_matcher.handlers) == 1
    assert impart_matcher.priority == 1
    assert impart_matcher.block is False
    assert len(impart_matcher.handlers) == 4
    assert all(
        len(matcher.handlers) == 1
        for matcher in plugin.matcher
        if matcher is not impart_matcher
    )
    assert not hasattr(handlers, "Impart")
    assert not hasattr(handlers, "impart")
