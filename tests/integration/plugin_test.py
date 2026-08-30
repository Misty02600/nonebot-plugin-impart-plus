from pathlib import Path

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
