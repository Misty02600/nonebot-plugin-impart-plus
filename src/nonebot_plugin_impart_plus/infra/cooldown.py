"""进程内命令冷却。"""

import time

from nonebot_plugin_uniref import UserRef


class CooldownManager:
    def __init__(
        self,
        *,
        dj_cd_time: int,
        pk_cd_time: int,
        suo_cd_time: int,
        fuck_cd_time: int,
    ) -> None:
        self.dj_cd_time = dj_cd_time
        self.pk_cd_time = pk_cd_time
        self.suo_cd_time = suo_cd_time
        self.fuck_cd_time = fuck_cd_time
        self.cd_data: dict[UserRef, float] = {}
        self.pk_cd_data: dict[UserRef, float] = {}
        self.suo_cd_data: dict[UserRef, float] = {}
        self.ejaculation_cd: dict[UserRef, float] = {}

    async def cd_check(self, uid: UserRef) -> bool:
        cd = (
            time.time() - self.cd_data[uid]
            if uid in self.cd_data
            else self.dj_cd_time + 1
        )
        return cd > self.dj_cd_time

    async def pkcd_check(self, uid: UserRef) -> bool:
        cd = (
            time.time() - self.pk_cd_data[uid]
            if uid in self.pk_cd_data
            else self.pk_cd_time + 1
        )
        return cd > self.pk_cd_time

    async def suo_cd_check(self, uid: UserRef) -> bool:
        cd = (
            time.time() - self.suo_cd_data[uid]
            if uid in self.suo_cd_data
            else self.suo_cd_time + 1
        )
        return cd > self.suo_cd_time

    async def fuck_cd_check(self, uid: UserRef) -> bool:
        cd = (
            time.time() - self.ejaculation_cd[uid]
            if uid in self.ejaculation_cd
            else self.fuck_cd_time + 1
        )
        return cd > self.fuck_cd_time

    def record_interaction(self, uid: UserRef) -> None:
        self.ejaculation_cd[uid] = time.time()
