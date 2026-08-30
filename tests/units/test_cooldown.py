"""CooldownManager 单元测试。

覆盖：
- 各 CD 类型的 check / record / clear
- SUPERUSER 全局 bypass
- CD 过期、未过期、刚好临界
- 多用户互不干扰
"""

import time

import pytest

from nonebot_plugin_impart_plus.infra.cooldown import CooldownManager


@pytest.fixture
def cm() -> CooldownManager:
    """普通用户的 CooldownManager。"""
    return CooldownManager(
        dj_cd_time=10,
        pk_cd_time=5,
        suo_cd_time=10,
        fuck_cd_time=20,
    )


@pytest.fixture
def cm_su() -> CooldownManager:
    """带 SUPERUSER 的 CooldownManager。"""
    return CooldownManager(
        dj_cd_time=10,
        pk_cd_time=5,
        suo_cd_time=10,
        fuck_cd_time=20,
        superusers=frozenset({"9999", "8888"}),
    )


# ═══════════════════════════════════════════════════════
#  基础 check / record 流程
# ═══════════════════════════════════════════════════════


class TestBasicFlow:
    """check → record → check 流程。"""

    def test_first_check_allowed(self, cm: CooldownManager):
        ok, _remain = cm.check_dj("100")
        assert ok is True
        assert _remain == 0.0

    def test_in_cooldown(self, cm: CooldownManager):
        cm.record_dj("100")
        ok, remain = cm.check_dj("100")
        assert ok is False
        assert remain > 0.0

    def test_cooldown_expired(self, cm: CooldownManager):
        """CD 已过期后应允许。"""
        fake_past = time.time() - 20  # 远超 10s
        cm._cd_data["100"] = fake_past
        ok, remain = cm.check_dj("100")
        assert ok is True
        assert remain == 0.0

    def test_cooldown_just_expired(self, cm: CooldownManager):
        """恰好到期。"""
        fake_past = time.time() - 10  # 恰好等于 dj_cd_time
        cm._cd_data["100"] = fake_past
        ok, _remain = cm.check_dj("100")
        assert ok is True

    def test_cooldown_almost_expired(self, cm: CooldownManager):
        """差一毫秒还没过期。"""
        fake_past = time.time() - 9.999
        cm._cd_data["100"] = fake_past
        ok, remain = cm.check_dj("100")
        assert ok is False
        assert remain > 0.0


# ═══════════════════════════════════════════════════════
#  所有 CD 类型
# ═══════════════════════════════════════════════════════


class TestAllCdTypes:
    """四种 CD：dj / pk / suo / fuck 各自独立。"""

    def test_dj_cd(self, cm: CooldownManager):
        cm.record_dj("1")
        assert cm.check_dj("1")[0] is False
        assert cm.check_pk("1")[0] is True  # 不影响 pk

    def test_pk_cd(self, cm: CooldownManager):
        cm.record_pk("1")
        assert cm.check_pk("1")[0] is False
        assert cm.check_dj("1")[0] is True

    def test_suo_cd(self, cm: CooldownManager):
        cm.record_suo("1")
        assert cm.check_suo("1")[0] is False
        assert cm.check_fuck("1")[0] is True

    def test_fuck_cd(self, cm: CooldownManager):
        cm.record_fuck("1")
        assert cm.check_fuck("1")[0] is False
        assert cm.check_suo("1")[0] is True


# ═══════════════════════════════════════════════════════
#  clear 方法
# ═══════════════════════════════════════════════════════


class TestClear:
    """clear 清除后恢复可用。"""

    def test_clear_pk(self, cm: CooldownManager):
        cm.record_pk("1")
        assert cm.check_pk("1")[0] is False
        cm.clear_pk("1")
        assert cm.check_pk("1")[0] is True

    def test_clear_suo(self, cm: CooldownManager):
        cm.record_suo("1")
        cm.clear_suo("1")
        assert cm.check_suo("1")[0] is True

    def test_clear_fuck(self, cm: CooldownManager):
        cm.record_fuck("1")
        cm.clear_fuck("1")
        assert cm.check_fuck("1")[0] is True

    def test_clear_nonexistent(self, cm: CooldownManager):
        """清除不存在的记录不会报错。"""
        cm.clear_pk("not_exist")  # 不应抛异常


# ═══════════════════════════════════════════════════════
#  SUPERUSER bypass
# ═══════════════════════════════════════════════════════


class TestSuperuserBypass:
    """SUPERUSER 跳过所有 CD。"""

    def test_su_dj_always_allowed(self, cm_su: CooldownManager):
        cm_su.record_dj("9999")
        ok, _remain = cm_su.check_dj("9999")
        assert ok is True
        assert _remain == 0.0

    def test_su_pk_always_allowed(self, cm_su: CooldownManager):
        cm_su.record_pk("8888")
        ok, _remain = cm_su.check_pk("8888")
        assert ok is True

    def test_su_suo_always_allowed(self, cm_su: CooldownManager):
        cm_su.record_suo("9999")
        assert cm_su.check_suo("9999")[0] is True

    def test_su_fuck_always_allowed(self, cm_su: CooldownManager):
        cm_su.record_fuck("9999")
        assert cm_su.check_fuck("9999")[0] is True

    def test_non_su_still_blocked(self, cm_su: CooldownManager):
        """非 SUPERUSER 仍受 CD 约束。"""
        cm_su.record_dj("1234")
        assert cm_su.check_dj("1234")[0] is False


# ═══════════════════════════════════════════════════════
#  多用户隔离
# ═══════════════════════════════════════════════════════


class TestUserIsolation:
    """不同用户的 CD 互不影响。"""

    def test_different_users(self, cm: CooldownManager):
        cm.record_dj("A")
        assert cm.check_dj("A")[0] is False
        assert cm.check_dj("B")[0] is True  # B 不受影响

    def test_record_does_not_cross_users(self, cm: CooldownManager):
        cm.record_pk("X")
        cm.record_pk("Y")
        cm.clear_pk("X")
        assert cm.check_pk("X")[0] is True
        assert cm.check_pk("Y")[0] is False  # Y 仍在 CD


# ═══════════════════════════════════════════════════════
#  remain 精度
# ═══════════════════════════════════════════════════════


class TestRemainPrecision:
    """剩余时间保留 3 位小数。"""

    def test_remain_is_rounded(self, cm: CooldownManager):
        cm.record_dj("1")
        _, remain = cm.check_dj("1")
        # remain 应该是 round(x, 3) 的结果
        assert remain == round(remain, 3)


# ═══════════════════════════════════════════════════════
#  默认参数
# ═══════════════════════════════════════════════════════


class TestDefaults:
    """默认构造参数与 game-design 一致。"""

    def test_default_cd_times(self):
        cm = CooldownManager()
        assert cm.dj_cd_time == 300
        assert cm.pk_cd_time == 60
        assert cm.suo_cd_time == 300
        assert cm.fuck_cd_time == 3600

    def test_default_no_superusers(self):
        cm = CooldownManager()
        assert cm._superusers == frozenset()
