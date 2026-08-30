"""冷却管理器

管理各种操作的冷却时间状态。
"""

import time


class CooldownManager:
    """统一管理所有冷却状态

    Attributes:
        dj_cd_time: 打胶冷却时间(秒)
        pk_cd_time: PK 冷却时间(秒)
        suo_cd_time: 嗦冷却时间(秒)
        fuck_cd_time: 透群友冷却时间(秒)
        superusers: SUPERUSER ID 集合，这些用户跳过所有 CD 检查
    """

    def __init__(
        self,
        dj_cd_time: int = 300,
        pk_cd_time: int = 60,
        suo_cd_time: int = 300,
        fuck_cd_time: int = 3600,
        superusers: frozenset[str] = frozenset(),
    ) -> None:
        self.dj_cd_time = dj_cd_time
        self.pk_cd_time = pk_cd_time
        self.suo_cd_time = suo_cd_time
        self.fuck_cd_time = fuck_cd_time
        self._superusers = superusers

        self._cd_data: dict[str, float] = {}
        self._pk_cd_data: dict[str, float] = {}
        self._suo_cd_data: dict[str, float] = {}
        self._ejaculation_cd: dict[str, float] = {}

    # region 通用方法

    def _check(
        self, uid: str, store: dict[str, float], cd_time: int
    ) -> tuple[bool, float]:
        """通用冷却检查

        SUPERUSER 自动跳过所有 CD。

        Args:
            uid: 用户 ID
            store: 冷却记录字典
            cd_time: 冷却时间(秒)

        Returns:
            tuple[bool, float]: (是否允许, 剩余秒数)
        """
        if uid in self._superusers:
            return True, 0.0
        if uid not in store:
            return True, 0.0
        elapsed = time.time() - store[uid]
        if elapsed >= cd_time:
            return True, 0.0
        return False, round(cd_time - elapsed, 3)

    def _record(self, uid: str, store: dict[str, float]) -> None:
        """记录冷却时间"""
        store[uid] = time.time()

    def _clear(self, uid: str, store: dict[str, float]) -> None:
        """清除冷却记录"""
        store.pop(uid, None)

    # endregion

    # region 打胶 CD

    def check_dj(self, uid: str) -> tuple[bool, float]:
        """打胶冷却检查"""
        return self._check(uid, self._cd_data, self.dj_cd_time)

    def record_dj(self, uid: str) -> None:
        """记录打胶时间"""
        self._record(uid, self._cd_data)

    # endregion

    # region PK CD

    def check_pk(self, uid: str) -> tuple[bool, float]:
        """PK 冷却检查"""
        return self._check(uid, self._pk_cd_data, self.pk_cd_time)

    def record_pk(self, uid: str) -> None:
        """记录 PK 时间"""
        self._record(uid, self._pk_cd_data)

    def clear_pk(self, uid: str) -> None:
        """清除 PK 冷却（用于新用户首次 PK）"""
        self._clear(uid, self._pk_cd_data)

    # endregion

    # region 嗦 CD

    def check_suo(self, uid: str) -> tuple[bool, float]:
        """嗦冷却检查"""
        return self._check(uid, self._suo_cd_data, self.suo_cd_time)

    def record_suo(self, uid: str) -> None:
        """记录嗦时间"""
        self._record(uid, self._suo_cd_data)

    def clear_suo(self, uid: str) -> None:
        """清除嗦冷却"""
        self._clear(uid, self._suo_cd_data)

    # endregion

    # region 透群友 CD

    def check_fuck(self, uid: str) -> tuple[bool, float]:
        """透群友冷却检查"""
        return self._check(uid, self._ejaculation_cd, self.fuck_cd_time)

    def record_fuck(self, uid: str) -> None:
        """记录透群友时间"""
        self._record(uid, self._ejaculation_cd)

    def clear_fuck(self, uid: str) -> None:
        """清除透群友冷却"""
        self._clear(uid, self._ejaculation_cd)

    # endregion
