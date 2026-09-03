from pathlib import Path

from nonebot import get_plugin
from nonebug import App


def test_plugin_metadata(app: App):
    import nonebot_plugin_impart_plus
    from nonebot_plugin_impart_plus import __plugin_meta__
    from nonebot_plugin_impart_plus.bot.dependencies import plugin_config
    from nonebot_plugin_impart_plus.bot.handlers.game import pk
    from nonebot_plugin_impart_plus.config import Config

    assert __plugin_meta__.name == "nonebot_plugin_impart_plus"
    assert __plugin_meta__.description == "NoneBot2 银趴插件 Plus"
    assert "初始战力为50%" in __plugin_meta__.usage
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
    assert get_plugin("nonebot_plugin_uninfo") is not None


def test_alconna_matcher_registration(app: App):
    from nonebot import get_plugin
    from nonebot_plugin_alconna import AlconnaMatcher

    from nonebot_plugin_impart_plus.bot import handlers

    plugin = get_plugin("nonebot_plugin_impart_plus")

    assert plugin is not None
    assert len(plugin.matcher) == 13
    assert all(issubclass(matcher, AlconnaMatcher) for matcher in plugin.matcher)

    dispatch_matchers = {
        matcher.basepath: matcher
        for matcher in plugin.matcher
        if matcher.basepath in {"member", "admin", "owner", "enabled", "query", "help"}
    }
    assert set(dispatch_matchers) == {
        "member",
        "admin",
        "owner",
        "enabled",
        "query",
        "help",
    }
    assert dispatch_matchers["member"].priority == 20
    assert dispatch_matchers["admin"].priority == 20
    assert dispatch_matchers["owner"].priority == 20
    assert dispatch_matchers["enabled"].priority == 10
    assert dispatch_matchers["query"].priority == 20
    assert dispatch_matchers["help"].priority == 20
    assert len(dispatch_matchers["enabled"].permission.checkers) == 2
    assert len(dispatch_matchers["query"].permission.checkers) == 0
    assert len(dispatch_matchers["help"].permission.checkers) == 0
    assert all(matcher.block for matcher in dispatch_matchers.values())

    parents = [matcher for matcher in plugin.matcher if matcher.priority == 1]
    assert len(parents) == 2
    assert all(parent.block is False for parent in parents)
    assert all(len(parent.handlers) == 3 for parent in parents)
    assert all(
        len(matcher.handlers) == 1
        for matcher in plugin.matcher
        if matcher not in parents
    )
    assert not hasattr(handlers, "Impart")
    assert not hasattr(handlers, "impart")
