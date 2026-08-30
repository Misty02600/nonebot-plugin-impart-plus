"""集成测试 conftest —— NoneBug matcher 端到端测试。

每个测试拥有独立的 in-memory SQLite 数据库 + 干净的 CooldownManager，
通过 monkey-patch 依赖注入函数实现隔离。

所有 nonebot_plugin_impart_plus 的导入必须在 fixture 内部延迟进行，
因为 NoneBot 需要在 tests/conftest.py 中先完成初始化。
"""

from __future__ import annotations

import pytest

# ── 常量 ────────────────────────────────────────────

USER_ID = 12345678
TARGET_ID = 11111111
GROUP_ID = 87654321
SUPERUSER_ID = 99999


# ── 通配消息哨兵 ────────────────────────────────────


class _AnyMessage:
    """与任何消息值相等的通配哨兵，用于 should_call_send 跳过消息内容断言。"""

    def __eq__(self, other: object) -> bool:
        return True

    def __ne__(self, other: object) -> bool:
        return False

    def __repr__(self) -> str:
        return "<ANY_MSG>"


ANY_MSG = _AnyMessage()
"""在 should_call_send 中代替具体消息，匹配任意发送内容。"""


# ── fixture：独立数据库 + CooldownManager ───────────


@pytest.fixture
async def fresh_env(monkeypatch):
    """为每个测试创建全新的 in-memory DB + CooldownManager。

    通过 monkeypatch 替换 dependencies 模块中的全局单例函数，
    使 NoneBug matcher 测试在完全隔离的状态下运行。

    Yields:
        (DataManager, CooldownManager) 供测试直接操作数据库状态。
    """
    from sqlalchemy.ext.asyncio import create_async_engine

    from nonebot_plugin_impart_plus.infra.cooldown import CooldownManager
    from nonebot_plugin_impart_plus.infra.data_manager import DataManager
    from nonebot_plugin_impart_plus.infra.database import (
        create_session_factory,
        init_db,
    )

    # 创建内存数据库
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = create_session_factory(engine)
    await init_db(engine)

    dm = DataManager(session_factory)
    cd = CooldownManager(
        dj_cd_time=300,
        pk_cd_time=60,
        suo_cd_time=300,
        fuck_cd_time=3600,
        superusers=frozenset({str(SUPERUSER_ID)}),
    )

    # 替换 DI 返回的单例（Depends 捕获的是函数引用，
    # 函数内部通过 module globals 访问 _data_manager / _cooldown，
    # 所以必须 patch 这两个私有变量而非 get_xxx 函数）
    import nonebot_plugin_impart_plus.bot.dependencies as deps

    monkeypatch.setattr(deps, "_data_manager", dm)
    monkeypatch.setattr(deps, "_cooldown", cd)

    # 预开启群聊
    await dm.set_group_allow(GROUP_ID, allow=True)

    yield dm, cd

    # 清理
    await engine.dispose()
