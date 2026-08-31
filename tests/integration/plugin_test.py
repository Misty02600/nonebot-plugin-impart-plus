from pathlib import Path

from nonebot import get_plugin
from nonebug import App


def test_plugin_metadata(app: App):
    import nonebot_plugin_impart_plus
    from nonebot_plugin_impart_plus import __plugin_meta__
    from nonebot_plugin_impart_plus.bot.handlers import impart, plugin_config
    from nonebot_plugin_impart_plus.config import Config

    assert __plugin_meta__.name == "nonebot_plugin_impart_plus"
    assert __plugin_meta__.description == "NoneBot2 银趴插件 Plus"
    assert "初始战力为50%" in __plugin_meta__.usage
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
    assert impart is not None
    assert get_plugin("nonebot_plugin_alconna") is not None
    assert get_plugin("nonebot_plugin_uninfo") is not None


def test_alconna_matcher_registration(app: App):
    from nonebot import get_plugin
    from nonebot_plugin_alconna import AlconnaMatcher

    plugin = get_plugin("nonebot_plugin_impart_plus")

    assert plugin is not None
    assert len(plugin.matcher) == 11
    assert all(issubclass(matcher, AlconnaMatcher) for matcher in plugin.matcher)

    dispatch_matchers = {
        matcher.basepath: matcher
        for matcher in plugin.matcher
        if matcher.basepath in {"enable", "disable", "help"}
    }
    assert set(dispatch_matchers) == {"enable", "disable", "help"}
    assert dispatch_matchers["enable"].priority == 10
    assert dispatch_matchers["disable"].priority == 10
    assert dispatch_matchers["help"].priority == 20
    assert len(dispatch_matchers["enable"].permission.checkers) == 2
    assert len(dispatch_matchers["disable"].permission.checkers) == 2
    assert len(dispatch_matchers["help"].permission.checkers) == 0
    assert all(matcher.block for matcher in dispatch_matchers.values())

    parent = next(matcher for matcher in plugin.matcher if matcher.priority == 1)
    assert parent.block is False
    assert len(parent.handlers) == 3
