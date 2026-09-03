import time

import pytest


@pytest.mark.parametrize(
    ("method_name", "data_name"),
    [
        ("cd_check", "cd_data"),
        ("pkcd_check", "pk_cd_data"),
        ("suo_cd_check", "suo_cd_data"),
        ("fuck_cd_check", "ejaculation_cd"),
    ],
)
async def test_cooldowns_are_isolated_by_user_ref(
    method_name: str,
    data_name: str,
) -> None:
    from nonebot_plugin_uniref import UserRef

    from nonebot_plugin_impart_plus.infra.cooldown import CooldownManager

    cooldown = CooldownManager(
        dj_cd_time=60,
        pk_cd_time=60,
        suo_cd_time=60,
        fuck_cd_time=60,
    )
    qq_user = UserRef("QQClient", "123")
    telegram_user = UserRef("Telegram", "123")
    getattr(cooldown, data_name)[qq_user] = time.time()

    assert await getattr(cooldown, method_name)(qq_user) is False
    assert await getattr(cooldown, method_name)(telegram_user) is True


async def test_interaction_cooldown_has_no_superuser_bypass() -> None:
    from nonebot_plugin_uniref import UserRef

    from nonebot_plugin_impart_plus.infra.cooldown import CooldownManager

    cooldown = CooldownManager(
        dj_cd_time=60,
        pk_cd_time=60,
        suo_cd_time=60,
        fuck_cd_time=60,
    )
    user = UserRef("Telegram", "admin")
    cooldown.ejaculation_cd[user] = time.time()

    assert await cooldown.fuck_cd_check(user) is False
