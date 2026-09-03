from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def _read_schema(
    connection: Connection,
) -> tuple[dict[str, set[str]], dict[str, set[tuple[str, ...]]]]:
    inspector = inspect(connection)
    tables = {
        table: {column["name"] for column in inspector.get_columns(table)}
        for table in inspector.get_table_names()
    }
    indexes = {
        table: {
            tuple(index["column_names"])
            for index in inspector.get_indexes(table)
            if index["column_names"]
        }
        for table in inspector.get_table_names()
    }
    return tables, indexes


@pytest.fixture
async def database_harness(tmp_path: Path):
    from nonebot_plugin_impart_plus.infra.data_manager import DataManager
    from nonebot_plugin_impart_plus.infra.database import Base

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'identity.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield SimpleNamespace(
            manager=DataManager(session_factory),
            engine=engine,
            session_factory=session_factory,
        )
    finally:
        await engine.dispose()


@pytest.fixture
def game_harness(database_harness):
    from nonebot_plugin_uniref import SceneKind, SceneRef, UserRef

    from nonebot_plugin_impart_plus.impart.app import GameApplication
    from nonebot_plugin_impart_plus.impart.core import GrowthMode
    from nonebot_plugin_impart_plus.infra.cooldown import CooldownManager

    cooldown = CooldownManager(
        dj_cd_time=60,
        pk_cd_time=60,
        suo_cd_time=60,
        fuck_cd_time=60,
    )
    return SimpleNamespace(
        manager=database_harness.manager,
        application=GameApplication(
            database_harness.manager,
            cooldown,
            penalties_enabled=True,
        ),
        cooldown=cooldown,
        scene=SceneRef("QQClient", SceneKind.GROUP, "100"),
        user=UserRef("QQClient", "1"),
        target=UserRef("QQClient", "2"),
        growth_mode=GrowthMode,
    )


async def test_ref_schema_contains_no_legacy_identity(database_harness) -> None:
    async with database_harness.engine.begin() as connection:
        schema, indexes = await connection.run_sync(_read_schema)

    assert set(schema) == {"user_data", "scene_data", "ejaculation_data"}
    assert {"user_ref", "user_namespace"} <= schema["user_data"]
    assert "userid" not in schema["user_data"]
    assert {"scene_ref", "scene_namespace", "scene_type"} <= schema["scene_data"]
    assert "groupid" not in schema["scene_data"]
    assert "user_ref" in schema["ejaculation_data"]
    assert "userid" not in schema["ejaculation_data"]
    assert ("user_namespace",) in indexes["user_data"]
    assert ("scene_namespace",) in indexes["scene_data"]
    assert ("scene_type",) in indexes["scene_data"]


async def test_data_manager_isolates_same_id_by_namespace(database_harness) -> None:
    from nonebot_plugin_uniref import UserRef, encode_ref

    from nonebot_plugin_impart_plus.infra.database import UserData

    manager = database_harness.manager
    qq_user = UserRef(namespace="QQClient", id="123")
    telegram_user = UserRef(namespace="Telegram", id="123")

    await manager.add_new_user(qq_user)
    await manager.add_new_user(telegram_user)
    await manager.set_jj_length(qq_user, 1.0)
    await manager.set_jj_length(telegram_user, 2.0)
    await manager.insert_ejaculation(qq_user, 3.0)
    await manager.insert_ejaculation(telegram_user, 4.0)

    assert await manager.get_jj_length(qq_user) == 11.0
    assert await manager.get_jj_length(telegram_user) == 12.0
    assert await manager.get_today_ejaculation_data(qq_user) == 3.0
    assert await manager.get_today_ejaculation_data(telegram_user) == 4.0

    async with database_harness.session_factory() as session:
        users = (await session.execute(select(UserData))).scalars().all()
    projections = {user.user_ref: user.user_namespace for user in users}
    assert projections == {
        encode_ref(qq_user): "QQClient",
        encode_ref(telegram_user): "Telegram",
    }


async def test_scene_switch_uses_full_scene_ref(database_harness) -> None:
    from nonebot_plugin_uniref import SceneKind, SceneRef, encode_ref

    from nonebot_plugin_impart_plus.infra.database import SceneData

    manager = database_harness.manager
    qq_group = SceneRef("QQClient", SceneKind.GROUP, "456")
    telegram_group = SceneRef("Telegram", SceneKind.GROUP, "456")
    qq_private = SceneRef("QQClient", SceneKind.PRIVATE, "456")

    await manager.set_scene_enabled(qq_group, True)
    await manager.set_scene_enabled(telegram_group, False)
    await manager.set_scene_enabled(qq_private, False)

    assert await manager.is_scene_enabled(qq_group) is True
    assert await manager.is_scene_enabled(telegram_group) is False
    assert await manager.is_scene_enabled(qq_private) is False

    async with database_harness.session_factory() as session:
        scenes = (await session.execute(select(SceneData))).scalars().all()
    projections = {
        scene.scene_ref: (scene.scene_namespace, scene.scene_type) for scene in scenes
    }
    assert projections == {
        encode_ref(qq_group): ("QQClient", "group"),
        encode_ref(telegram_group): ("Telegram", "group"),
        encode_ref(qq_private): ("QQClient", "private"),
    }


async def test_length_commands_initialize_missing_users_without_action(
    game_harness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_uniref import UserRef

    from nonebot_plugin_impart_plus.impart import app as app_module

    manager = game_harness.manager
    application = game_harness.application
    cooldown = game_harness.cooldown
    scene = game_harness.scene
    growth_mode = game_harness.growth_mode
    await manager.set_scene_enabled(scene, True)

    grow_user = UserRef("QQClient", "10")
    suo_user = UserRef("QQClient", "20")
    suo_target = UserRef("QQClient", "21")
    query_user = UserRef("QQClient", "30")
    query_target = UserRef("QQClient", "31")
    pk_user = UserRef("QQClient", "40")
    pk_target = UserRef("QQClient", "41")
    await manager.add_new_user(suo_user)
    await manager.set_jj_length(suo_user, 2.0)
    await manager.add_new_user(query_target)
    await manager.set_jj_length(query_target, 3.0)

    async def unexpected_penalty() -> None:
        raise AssertionError("首次初始化不应执行全局惩罚")

    def unexpected_random() -> float:
        raise AssertionError("首次初始化不应消费随机数")

    monkeypatch.setattr(manager, "punish_all_inactive_users", unexpected_penalty)
    monkeypatch.setattr(app_module, "get_random_num", unexpected_random)
    monkeypatch.setattr(app_module.random, "random", unexpected_random)

    outcomes = [
        await application.grow_self(scene, grow_user, growth_mode.DEPTH),
        await application.grow_target(scene, suo_user, suo_target),
        await application.query_user(scene, query_user, query_target),
        await application.execute_pk(scene, pk_user, pk_target),
    ]
    expected_users = [
        (grow_user,),
        (suo_target,),
        (query_user,),
        (pk_user, pk_target),
    ]

    assert [outcome.type.value for outcome in outcomes] == [
        "user_created",
        "user_created",
        "user_created",
        "users_created",
    ]
    assert [outcome.created_users for outcome in outcomes] == expected_users
    assert cooldown.cd_data == {}
    assert cooldown.suo_cd_data == {}
    assert cooldown.pk_cd_data == {}
    for created_user in (user for users in expected_users for user in users):
        assert await manager.has_user(created_user)
        assert await manager.get_jj_length(created_user) == 10.0
        assert await manager.get_win_probability(created_user) == 0.5
    assert await manager.get_jj_length(suo_user) == 12.0
    assert await manager.get_jj_length(query_target) == 13.0


async def test_self_growth_applies_signed_direction_and_skips_depth_challenge(
    game_harness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_uniref import UserRef

    from nonebot_plugin_impart_plus.impart import app as app_module

    manager = game_harness.manager
    application = game_harness.application
    scene = game_harness.scene
    mode = game_harness.growth_mode
    length_user = UserRef("QQClient", "50")
    depth_user = UserRef("QQClient", "51")
    wrong_state_user = UserRef("QQClient", "52")
    await manager.set_scene_enabled(scene, True)
    for user in (length_user, depth_user, wrong_state_user):
        await manager.add_new_user(user)
    await manager.set_jj_length(depth_user, -10.0)

    generated = 0

    def fixed_random() -> float:
        nonlocal generated
        generated += 1
        return 1.25

    monkeypatch.setattr(app_module, "get_random_num", fixed_random)

    original_update = manager.update_challenge_status
    calls = 0

    async def track_challenge(user_ref) -> str:
        nonlocal calls
        calls += 1
        return await original_update(user_ref)

    monkeypatch.setattr(manager, "update_challenge_status", track_challenge)

    length = await application.grow_self(scene, length_user, mode.LENGTH)
    depth = await application.grow_self(scene, depth_user, mode.DEPTH)
    wrong_state = await application.grow_self(scene, wrong_state_user, mode.DEPTH)

    assert (length.type.value, length.new_length) == ("completed", 11.25)
    assert (depth.type.value, depth.new_length) == ("completed", -1.25)
    assert wrong_state.type.value == "wrong_state"
    assert await manager.get_jj_length(wrong_state_user) == 10.0
    assert generated == 2
    assert calls == 1
    assert set(game_harness.cooldown.cd_data) == {length_user, depth_user}


async def test_application_ranking_is_partitioned_by_namespace(
    database_harness,
) -> None:
    from nonebot_plugin_uniref import SceneKind, SceneRef, UserRef

    from nonebot_plugin_impart_plus.impart.app import (
        GameApplication,
        RankingOutcomeType,
    )
    from nonebot_plugin_impart_plus.infra.cooldown import CooldownManager

    manager = database_harness.manager
    cooldown = CooldownManager(
        dj_cd_time=60,
        pk_cd_time=60,
        suo_cd_time=60,
        fuck_cd_time=60,
    )
    application = GameApplication(manager, cooldown, penalties_enabled=False)
    qq_scene = SceneRef("QQClient", SceneKind.GROUP, "100")
    telegram_scene = SceneRef("Telegram", SceneKind.GROUP, "100")
    qq_users = [UserRef("QQClient", str(index)) for index in range(6)]
    telegram_users = [UserRef("Telegram", str(index)) for index in range(4)]

    await manager.set_scene_enabled(qq_scene, True)
    await manager.set_scene_enabled(telegram_scene, True)
    for index, user in enumerate(qq_users):
        await manager.add_new_user(user)
        await manager.set_jj_length(user, float(index))
    for user in telegram_users:
        await manager.add_new_user(user)

    qq_outcome = await application.query_ranking(qq_scene, qq_users[3])
    telegram_outcome = await application.query_ranking(
        telegram_scene,
        telegram_users[0],
    )

    assert qq_outcome.type is RankingOutcomeType.COMPLETED
    assert qq_outcome.index == 2
    assert [entry.user.namespace for entry in qq_outcome.ranking] == ["QQClient"] * 6
    assert telegram_outcome.type is RankingOutcomeType.TOO_FEW
