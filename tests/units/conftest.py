"""单元测试 conftest —— 纯核心逻辑测试专用。

在 collection 阶段前通过 pytest_configure 初始化 NoneBot 并加载插件，
使 `nonebot_plugin_impart_plus.__init__` 中的 NoneBot 依赖链不会失败。

与 tests/conftest.py (nonebug 集成测试) 共存：
  - 单独运行: `pytest tests/units/` → 这里完成 init + load
  - 全量运行: `pytest` → 这里先 init + load，集成 conftest 跳过重复加载
"""

import nonebot


def pytest_configure(config):  # pyright: ignore[reportUnusedParameter]
    """在收集测试之前初始化 NoneBot 并加载插件。"""
    try:
        nonebot.get_driver()
    except ValueError:
        nonebot.init()

    # 如果插件尚未加载，加载它
    if not nonebot.get_plugin("nonebot_plugin_impart_plus"):
        nonebot.load_from_toml("pyproject.toml")
