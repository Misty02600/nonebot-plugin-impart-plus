from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def _read_schema(
    connection: Connection,
) -> tuple[
    dict[str, set[str]],
    dict[str, set[tuple[str, ...]]],
    dict[str, set[tuple[str, ...]]],
]:
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
    unique_constraints = {
        table: {
            tuple(constraint["column_names"])
            for constraint in inspector.get_unique_constraints(table)
            if constraint["column_names"]
        }
        for table in inspector.get_table_names()
    }
    return tables, indexes, unique_constraints


@pytest.fixture
async def database_harness(tmp_path: Path):
    from nonebot_plugin_orm import Model

    from nonebot_plugin_impart_plus.infra.data_manager import DataManager
    from nonebot_plugin_impart_plus.infra.database import (
        EjaculationData,
        SceneData,
        UserData,
    )

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'identity.db'}")

    def create_tables(connection: Connection) -> None:
        Model.metadata.create_all(
            connection,
            tables=[
                UserData.__table__,
                SceneData.__table__,
                EjaculationData.__table__,
            ],
        )

    async with engine.begin() as connection:
        await connection.run_sync(create_tables)
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
        application=GameApplication(database_harness.manager, cooldown),
        cooldown=cooldown,
        scene=SceneRef("QQClient", SceneKind.GROUP, "100"),
        user=UserRef("QQClient", "1"),
        target=UserRef("QQClient", "2"),
        growth_mode=GrowthMode,
    )


async def test_ref_schema_contains_no_legacy_identity(database_harness) -> None:
    from sqlalchemy.dialects import mysql, postgresql, sqlite
    from sqlalchemy.schema import CreateIndex, CreateTable

    from nonebot_plugin_impart_plus.infra.database import (
        EjaculationData,
        SceneData,
        UserData,
    )

    async with database_harness.engine.begin() as connection:
        schema, indexes, unique_constraints = await connection.run_sync(_read_schema)

    user_table = UserData.__table__.name
    scene_table = SceneData.__table__.name
    ejaculation_table = EjaculationData.__table__.name
    assert {
        table.info["bind_key"]
        for table in (
            UserData.__table__,
            SceneData.__table__,
            EjaculationData.__table__,
        )
    } == {""}
    assert set(schema) == {user_table, scene_table, ejaculation_table}
    assert {"user_ref", "user_namespace"} <= schema[user_table]
    assert "userid" not in schema[user_table]
    assert "last_masturbation_time" not in schema[user_table]
    assert {"scene_ref", "scene_namespace", "scene_type"} <= schema[scene_table]
    assert "groupid" not in schema[scene_table]
    assert "user_ref" in schema[ejaculation_table]
    assert "userid" not in schema[ejaculation_table]
    assert ("user_namespace",) in indexes[user_table]
    assert ("scene_namespace",) in indexes[scene_table]
    assert ("scene_type",) in indexes[scene_table]
    assert ("user_ref", "date") in unique_constraints[ejaculation_table]

    for dialect in (sqlite.dialect(), postgresql.dialect(), mysql.dialect()):
        for table in (
            UserData.__table__,
            SceneData.__table__,
            EjaculationData.__table__,
        ):
            str(CreateTable(table).compile(dialect=dialect))
            for index in table.indexes:
                str(CreateIndex(index).compile(dialect=dialect))


async def test_persistence_rejects_refs_outside_schema_limits(
    database_harness,
) -> None:
    from nonebot_plugin_uniref import UserRef, encode_ref

    from nonebot_plugin_impart_plus.infra.database import (
        PERSISTED_NAMESPACE_MAX_LENGTH,
        PERSISTED_REF_MAX_LENGTH,
    )

    manager = database_harness.manager
    namespace = "n" * PERSISTED_NAMESPACE_MAX_LENGTH
    await manager.get_ranking(namespace)

    with pytest.raises(ValueError, match="namespace exceeds"):
        await manager.get_ranking(f"{namespace}n")

    prefix_length = len(encode_ref(UserRef("n", "x"))) - 1
    largest_ref = UserRef("n", "x" * (PERSISTED_REF_MAX_LENGTH - prefix_length))
    assert len(encode_ref(largest_ref)) == PERSISTED_REF_MAX_LENGTH
    assert not await manager.has_user(largest_ref)

    with pytest.raises(ValueError, match="encoded Ref exceeds"):
        await manager.has_user(UserRef("n", f"{largest_ref.id}x"))


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


async def test_concurrent_ejaculation_updates_preserve_total(
    database_harness,
) -> None:
    from asyncio import gather

    from nonebot_plugin_uniref import UserRef

    manager = database_harness.manager
    recipient = UserRef("QQClient", "concurrent-recipient")

    await gather(*(manager.insert_ejaculation(recipient, 1.0) for _ in range(8)))
    assert await manager.get_today_ejaculation_data(recipient) == 8.0

    await gather(*(manager.insert_ejaculation(recipient, 0.125) for _ in range(8)))
    assert await manager.get_today_ejaculation_data(recipient) == 9.0


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


async def test_gameplay_commands_initialize_missing_users_without_action(
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
    interaction_user = UserRef("QQClient", "42")
    await manager.add_new_user(suo_user)
    await manager.set_jj_length(suo_user, 2.0)
    await manager.add_new_user(query_target)
    await manager.set_jj_length(query_target, 3.0)

    def unexpected_random() -> float:
        raise AssertionError("首次初始化不应消费随机数")

    monkeypatch.setattr(app_module, "get_random_num", unexpected_random)
    monkeypatch.setattr(app_module.random, "random", unexpected_random)

    missing_pk = await application.execute_pk(scene, pk_user, None)
    assert missing_pk.type.value == "missing_target"
    assert not await manager.has_user(pk_user)

    outcomes = [
        await application.grow_self(scene, grow_user, growth_mode.DEPTH),
        await application.grow_target(
            scene,
            suo_user,
            suo_target,
            growth_mode.LENGTH,
        ),
        await application.query_user(scene, query_user, query_target),
        await application.execute_pk(scene, pk_user, pk_target),
        await application.prepare_interaction(scene, interaction_user),
    ]

    expected_users = [
        (grow_user,),
        (suo_target,),
        (query_user,),
        (pk_user, pk_target),
        (interaction_user,),
    ]

    assert [outcome.type.value for outcome in outcomes] == [
        "user_created",
        "user_created",
        "user_created",
        "users_created",
        "user_created",
    ]
    assert [outcome.created_users for outcome in outcomes] == expected_users
    assert cooldown.cd_data == {}
    assert cooldown.suo_cd_data == {}
    assert cooldown.pk_cd_data == {}
    assert cooldown.ejaculation_cd == {}
    for created_user in (user for users in expected_users for user in users):
        assert await manager.has_user(created_user)
        assert await manager.get_jj_length(created_user) == 10.0
        assert await manager.get_win_probability(created_user) == 0.5
    assert await manager.get_jj_length(suo_user) == 12.0
    assert await manager.get_jj_length(query_target) == 13.0


@pytest.mark.parametrize(
    (
        "requested",
        "requester_length",
        "target_length",
        "roll",
        "expected_action",
        "expected_recipient",
        "expected_fluid",
    ),
    [
        ("INJECT", 10.0, None, 0.75, "INJECT", "target", "DNA"),
        ("INJECT", -10.0, 10.0, 0.75, "INJECT", "requester", "DNA"),
        ("SQUEEZE", -10.0, -10.0, None, "SQUEEZE", "requester", "GIRL_JUICE"),
        ("SQUEEZE", 10.0, -10.0, None, "SQUEEZE", "target", "DNA"),
    ],
)
async def test_interaction_records_volume_for_actual_recipient(
    game_harness,
    monkeypatch: pytest.MonkeyPatch,
    requested: str,
    requester_length: float,
    target_length: float | None,
    roll: float | None,
    expected_action: str,
    expected_recipient: str,
    expected_fluid: str,
) -> None:
    from nonebot_plugin_impart_plus.impart import app as app_module
    from nonebot_plugin_impart_plus.impart.core import (
        InteractionAction,
        InteractionFluid,
    )

    manager = game_harness.manager
    application = game_harness.application
    cooldown = game_harness.cooldown
    requester = game_harness.user
    target = game_harness.target
    await manager.add_new_user(requester)
    await manager.set_jj_length(requester, requester_length - 10.0)
    if target_length is not None:
        await manager.add_new_user(target)
        await manager.set_jj_length(target, target_length - 10.0)

    resolution = await application.begin_interaction(
        requester,
        target,
        InteractionAction[requested],
        roll,
    )
    assert await manager.has_user(target)
    assert requester in cooldown.ejaculation_cd

    random_calls: list[str] = []

    def volume(*_: object) -> float:
        random_calls.append("volume")
        return 12.5

    def seconds(*_: object) -> int:
        random_calls.append("seconds")
        return 4

    monkeypatch.setattr(app_module.random, "uniform", volume)
    monkeypatch.setattr(app_module.random, "randint", seconds)
    result = await application.complete_interaction(requester, target, resolution)

    recipient = requester if expected_recipient == "requester" else target
    other = target if recipient == requester else requester
    assert result.resolution.action is InteractionAction[expected_action]
    assert result.resolution.fluid is InteractionFluid[expected_fluid]
    assert result.ejaculation == 12.5
    assert result.seconds == 4
    assert result.today_total == 12.5
    assert await manager.get_today_ejaculation_data(recipient) == 12.5
    assert await manager.get_today_ejaculation_data(other) == 0.0
    assert random_calls == ["volume", "seconds"]


async def test_pk_rejects_mixed_world_and_reverses_negative_deltas(
    game_harness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_uniref import UserRef

    from nonebot_plugin_impart_plus.impart import app as app_module
    from nonebot_plugin_impart_plus.impart.app import PkOutcomeType

    manager = game_harness.manager
    application = game_harness.application
    cooldown = game_harness.cooldown
    scene = game_harness.scene
    mode = game_harness.growth_mode
    positive = (UserRef("QQClient", "50"), UserRef("QQClient", "51"))
    negative_win = (UserRef("QQClient", "52"), UserRef("QQClient", "53"))
    negative_loss = (UserRef("QQClient", "54"), UserRef("QQClient", "55"))
    await manager.set_scene_enabled(scene, True)
    for user in (*positive, *negative_win, *negative_loss):
        await manager.add_new_user(user)
    for user in (*negative_win, *negative_loss):
        await manager.set_jj_length(user, -20.0)

    win_rolls = iter((0.0, 0.0, 1.0))
    win_roll_calls = 0

    def fixed_win_roll() -> float:
        nonlocal win_roll_calls
        win_roll_calls += 1
        return next(win_rolls)

    growth_roll_calls = 0

    def fixed_growth_roll() -> float:
        nonlocal growth_roll_calls
        growth_roll_calls += 1
        return 1.25

    monkeypatch.setattr(app_module.random, "random", fixed_win_roll)
    monkeypatch.setattr(app_module, "get_random_num", fixed_growth_roll)

    mixed_positive = await application.execute_pk(scene, positive[0], negative_win[0])
    mixed_negative = await application.execute_pk(scene, negative_win[0], positive[0])

    assert mixed_positive.type is PkOutcomeType.WORLD_MISMATCH
    assert mixed_positive.mode is mode.LENGTH
    assert mixed_negative.type is PkOutcomeType.WORLD_MISMATCH
    assert mixed_negative.mode is mode.DEPTH
    assert win_roll_calls == growth_roll_calls == 0
    assert cooldown.pk_cd_data == {}
    assert await manager.get_jj_length(positive[0]) == 10.0
    assert await manager.get_jj_length(negative_win[0]) == -10.0

    positive_result = await application.execute_pk(scene, *positive)
    negative_win_result = await application.execute_pk(scene, *negative_win)
    negative_loss_result = await application.execute_pk(scene, *negative_loss)

    assert positive_result.mode is mode.LENGTH
    assert negative_win_result.mode is mode.DEPTH
    assert negative_loss_result.mode is mode.DEPTH
    assert await manager.get_jj_length(positive[0]) == 10.625
    assert await manager.get_jj_length(positive[1]) == 8.75
    assert await manager.get_jj_length(negative_win[0]) == -10.625
    assert await manager.get_jj_length(negative_win[1]) == -8.75
    assert await manager.get_jj_length(negative_loss[0]) == -8.75
    assert await manager.get_jj_length(negative_loss[1]) == -10.625
    assert await manager.get_win_probability(negative_loss[0]) == 0.51
    assert await manager.get_win_probability(negative_loss[1]) == 0.49
    assert win_roll_calls == growth_roll_calls == 3


async def test_pk_settlement_rolls_back_both_users_after_flush(
    database_harness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_uniref import UserRef
    from sqlalchemy.ext.asyncio import AsyncSession

    manager = database_harness.manager
    attacker = UserRef("QQClient", "pk-rollback-attacker")
    defender = UserRef("QQClient", "pk-rollback-defender")
    await manager.add_new_user(attacker)
    await manager.add_new_user(defender)
    original_flush = AsyncSession.flush

    async def fail_after_flush(
        session: AsyncSession,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        await original_flush(session, *args, **kwargs)
        raise RuntimeError("injected flush failure")

    with monkeypatch.context() as patch:
        patch.setattr(AsyncSession, "flush", fail_after_flush)
        with pytest.raises(RuntimeError, match="injected flush failure"):
            await manager.settle_pk(
                attacker,
                defender,
                win_roll=0.0,
                random_num=1.0,
            )

    assert await manager.get_jj_length(attacker) == 10.0
    assert await manager.get_jj_length(defender) == 10.0
    assert await manager.get_win_probability(attacker) == 0.5
    assert await manager.get_win_probability(defender) == 0.5


async def test_application_serializes_pk_with_a_shared_target(
    game_harness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import asyncio

    from nonebot_plugin_uniref import SceneRef, UserRef

    from nonebot_plugin_impart_plus.impart import app as app_module
    from nonebot_plugin_impart_plus.impart.app import PkOutcome, PkOutcomeType

    manager = game_harness.manager
    application = game_harness.application
    scene = game_harness.scene
    first_attacker = UserRef("QQClient", "pk-concurrent-first")
    second_attacker = UserRef("QQClient", "pk-concurrent-second")
    target = UserRef("QQClient", "pk-concurrent-target")
    await manager.set_scene_enabled(scene, True)
    for user in (first_attacker, second_attacker, target):
        await manager.add_new_user(user)

    original_execute = application._execute_pk
    first_entered = asyncio.Event()
    release_first = asyncio.Event()
    execution_calls = 0

    async def scene_enabled(_: SceneRef) -> bool:
        return True

    async def delayed_execute(
        attacker_ref: UserRef,
        defender_ref: UserRef,
    ) -> PkOutcome:
        nonlocal execution_calls
        execution_calls += 1
        if execution_calls == 1:
            first_entered.set()
            await release_first.wait()
        return await original_execute(attacker_ref, defender_ref)

    monkeypatch.setattr(manager, "is_scene_enabled", scene_enabled)
    monkeypatch.setattr(application, "_execute_pk", delayed_execute)
    monkeypatch.setattr(app_module.random, "random", lambda: 0.0)
    monkeypatch.setattr(app_module, "get_random_num", lambda: 1.0)

    first = asyncio.create_task(application.execute_pk(scene, first_attacker, target))
    await first_entered.wait()
    second = asyncio.create_task(application.execute_pk(scene, second_attacker, target))
    await asyncio.sleep(0)
    calls_while_first_held_lock = execution_calls
    release_first.set()
    outcomes = await asyncio.gather(first, second)

    assert calls_while_first_held_lock == 1
    assert [outcome.type for outcome in outcomes] == [
        PkOutcomeType.COMPLETED,
        PkOutcomeType.COMPLETED,
    ]
    assert await manager.get_jj_length(target) == 8.0
    assert await manager.get_win_probability(target) == 0.52


async def test_self_growth_applies_signed_direction_and_checks_both_challenges(
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
    assert calls == 2
    assert set(game_harness.cooldown.cd_data) == {length_user, depth_user}


async def test_target_growth_enforces_boundaries_and_signed_direction(
    game_harness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_uniref import UserRef

    from nonebot_plugin_impart_plus.impart import app as app_module
    from nonebot_plugin_impart_plus.impart.app import GrowthOutcomeType

    manager = game_harness.manager
    application = game_harness.application
    cooldown = game_harness.cooldown
    scene = game_harness.scene
    mode = game_harness.growth_mode
    user = UserRef("QQClient", "60")
    other_user = UserRef("QQClient", "61")
    length_target = UserRef("QQClient", "62")
    depth_target = UserRef("QQClient", "63")
    disabled = await application.grow_target(scene, user, None, mode.LENGTH)
    await manager.set_scene_enabled(scene, True)

    missing = await application.grow_target(scene, user, None, mode.LENGTH)
    self_target = await application.grow_target(scene, user, user, mode.LENGTH)

    assert disabled.type is GrowthOutcomeType.DISABLED
    assert missing.type is GrowthOutcomeType.MISSING_TARGET
    assert self_target.type is GrowthOutcomeType.SELF_TARGET
    assert not await manager.has_user(user)
    assert cooldown.suo_cd_data == {}

    for current_user in (user, other_user, length_target, depth_target):
        await manager.add_new_user(current_user)
    await manager.set_jj_length(depth_target, -12.0)

    generated = 0

    def fixed_random() -> float:
        nonlocal generated
        generated += 1
        return 1.25

    monkeypatch.setattr(app_module, "get_random_num", fixed_random)
    original_update = manager.update_challenge_status
    challenge_calls = 0

    async def track_challenge(user_ref) -> str:
        nonlocal challenge_calls
        challenge_calls += 1
        return await original_update(user_ref)

    monkeypatch.setattr(manager, "update_challenge_status", track_challenge)

    wrong_length = await application.grow_target(
        scene,
        user,
        depth_target,
        mode.LENGTH,
    )
    wrong_depth = await application.grow_target(
        scene,
        user,
        length_target,
        mode.DEPTH,
    )

    assert wrong_length.type is GrowthOutcomeType.WRONG_STATE
    assert wrong_depth.type is GrowthOutcomeType.WRONG_STATE
    assert generated == 0
    assert challenge_calls == 0
    assert cooldown.suo_cd_data == {}

    depth = await application.grow_target(
        scene,
        user,
        depth_target,
        mode.DEPTH,
    )
    shared_cooldown = await application.grow_target(
        scene,
        user,
        length_target,
        mode.LENGTH,
    )
    length = await application.grow_target(
        scene,
        other_user,
        length_target,
        mode.LENGTH,
    )

    assert (depth.type, depth.new_length) == (GrowthOutcomeType.COMPLETED, -3.25)
    assert shared_cooldown.type is GrowthOutcomeType.COOLING_DOWN
    assert (length.type, length.new_length) == (
        GrowthOutcomeType.COMPLETED,
        11.25,
    )
    assert generated == 2
    assert challenge_calls == 3
    assert set(cooldown.suo_cd_data) == {user, other_user}


async def test_growth_challenge_guards_precede_cooldown_and_random(
    game_harness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_uniref import UserRef

    from nonebot_plugin_impart_plus.impart import app as app_module
    from nonebot_plugin_impart_plus.impart.app import GrowthOutcomeType

    manager = game_harness.manager
    application = game_harness.application
    cooldown = game_harness.cooldown
    scene = game_harness.scene
    mode = game_harness.growth_mode
    positive_challenger = UserRef("QQClient", "70")
    negative_challenger = UserRef("QQClient", "71")
    positive_normal = UserRef("QQClient", "72")
    negative_normal = UserRef("QQClient", "73")
    await manager.set_scene_enabled(scene, True)
    for user in (
        positive_challenger,
        negative_challenger,
        positive_normal,
        negative_normal,
    ):
        await manager.add_new_user(user)
    await manager.set_jj_length(positive_challenger, 15.0)
    await manager.set_jj_length(negative_challenger, -35.0)
    await manager.set_jj_length(negative_normal, -20.0)
    assert (
        await manager.update_challenge_status(positive_challenger)
        == "challenge_started_low_win"
    )
    assert (
        await manager.update_challenge_status(negative_challenger)
        == "challenge_started_low_win"
    )

    generated = 0

    def track_random() -> float:
        nonlocal generated
        generated += 1
        return 1.25

    monkeypatch.setattr(app_module, "get_random_num", track_random)

    outcomes = [
        await application.grow_self(scene, positive_challenger, mode.LENGTH),
        await application.grow_self(scene, negative_challenger, mode.DEPTH),
        await application.grow_target(
            scene,
            positive_challenger,
            positive_normal,
            mode.LENGTH,
        ),
        await application.grow_target(
            scene,
            negative_challenger,
            negative_normal,
            mode.DEPTH,
        ),
        await application.grow_target(
            scene,
            positive_normal,
            positive_challenger,
            mode.LENGTH,
        ),
        await application.grow_target(
            scene,
            negative_normal,
            negative_challenger,
            mode.DEPTH,
        ),
    ]

    assert [outcome.type for outcome in outcomes] == [
        GrowthOutcomeType.ACTOR_CHALLENGING,
        GrowthOutcomeType.ACTOR_CHALLENGING,
        GrowthOutcomeType.ACTOR_CHALLENGING,
        GrowthOutcomeType.ACTOR_CHALLENGING,
        GrowthOutcomeType.TARGET_CHALLENGING,
        GrowthOutcomeType.TARGET_CHALLENGING,
    ]
    assert generated == 0
    assert cooldown.cd_data == {}
    assert cooldown.suo_cd_data == {}
    assert await manager.get_jj_length(positive_challenger) == 25.0
    assert await manager.get_jj_length(negative_challenger) == -25.0
    assert await manager.get_jj_length(positive_normal) == 10.0
    assert await manager.get_jj_length(negative_normal) == -10.0


async def test_negative_growth_can_start_challenge(
    game_harness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_uniref import UserRef

    from nonebot_plugin_impart_plus.impart import app as app_module

    manager = game_harness.manager
    application = game_harness.application
    scene = game_harness.scene
    mode = game_harness.growth_mode
    self_user = UserRef("QQClient", "80")
    actor = UserRef("QQClient", "81")
    target = UserRef("QQClient", "82")
    await manager.set_scene_enabled(scene, True)
    for user in (self_user, actor, target):
        await manager.add_new_user(user)
    await manager.set_jj_length(self_user, -34.0)
    await manager.set_jj_length(target, -34.0)
    monkeypatch.setattr(app_module, "get_random_num", lambda: 1.0)

    self_outcome = await application.grow_self(scene, self_user, mode.DEPTH)
    target_outcome = await application.grow_target(scene, actor, target, mode.DEPTH)

    assert self_outcome.challenge_started
    assert target_outcome.challenge_started
    assert self_outcome.new_length == target_outcome.new_length == -25.0
    assert await manager.get_win_probability(self_user) == 0.4
    assert await manager.get_win_probability(target) == 0.4


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
    application = GameApplication(manager, cooldown)
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
