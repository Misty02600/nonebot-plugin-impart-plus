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
    dict[str, set[tuple[str | None, ...]]],
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


@pytest.fixture
async def possession_harness(game_harness, database_harness):
    from nonebot_plugin_uniref import encode_ref

    from nonebot_plugin_impart_plus.infra.database import UserData

    await game_harness.manager.set_scene_enabled(game_harness.scene, True)
    async with database_harness.session_factory() as session, session.begin():
        session.add_all(
            UserData(
                user_ref=encode_ref(user),
                user_namespace=user.namespace,
                jj_length=length,
                win_probability=probability,
                challenge_tier=1,
            )
            for user, length, probability in (
                (game_harness.user, -70.0, 0.6),
                (game_harness.target, 49.998, 0.4),
            )
        )
    return game_harness


async def test_possession_persists_both_states_and_preserves_other_data(
    possession_harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    from nonebot_plugin_impart_plus.impart import app as app_module
    from nonebot_plugin_impart_plus.impart.core import GrowthMode, PossessionStatus

    h = possession_harness
    for user in (h.user, h.target):
        await h.manager.settle_interaction_volumes({user: (250.0, None)})

    def unexpected_random(*_):
        raise AssertionError("夺舍不应消耗结算随机数")

    monkeypatch.setattr(app_module.random, "random", unexpected_random)
    result = await h.application.execute_possession(h.scene, h.user, h.target)
    assert result.type is PossessionStatus.COMPLETED
    assert result.half == 24.999
    assert result.target_challenge is not None
    assert result.target_challenge.tier == 1
    actor = await h.manager.get_user_query_data(h.user, history=True)
    target = await h.manager.get_user_query_data(h.target, history=True)
    assert actor is not None
    assert target is not None
    assert (actor.length, target.length) == (24.999, 19.999)
    assert actor.challenge_tier == target.challenge_tier == 0
    assert actor.records == target.records == {h.manager.get_today(): 250.0}
    assert await h.manager.get_win_probability(h.user) == 0.6
    assert await h.manager.get_win_probability(h.target) == 0.4
    assert (
        h.cooldown.cd_data
        == h.cooldown.pk_cd_data
        == h.cooldown.suo_cd_data
        == h.cooldown.ejaculation_cd
        == {}
    )

    monkeypatch.setattr(app_module, "get_random_num", lambda: 0.0)
    growth = await h.application.grow_self(h.scene, h.user, GrowthMode.LENGTH)
    assert growth.new_length == 24.999


async def test_possession_guards_and_initialization(game_harness) -> None:
    from nonebot_plugin_impart_plus.impart.core import PossessionStatus

    h = game_harness
    disabled = await h.application.execute_possession(h.scene, h.user, None)
    assert disabled.type is PossessionStatus.DISABLED
    await h.manager.set_scene_enabled(h.scene, True)
    missing = await h.application.execute_possession(h.scene, h.user, None)
    assert missing.type is PossessionStatus.MISSING_TARGET
    assert not await h.manager.has_user(h.user)
    created = await h.application.execute_possession(h.scene, h.user, h.target)
    assert created.type is PossessionStatus.USERS_CREATED
    assert created.created_users == (h.user, h.target)
    locked = await h.application.execute_possession(h.scene, h.user, h.target)
    assert locked.type is PossessionStatus.LOCKED
    assert await h.manager.get_jj_length(h.user) == 10.0
    assert await h.manager.get_jj_length(h.target) == 10.0


async def test_possession_rolls_back_then_releases_application_lock(
    possession_harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    import asyncio

    from sqlalchemy.ext.asyncio import AsyncSession

    from nonebot_plugin_impart_plus.impart.core import PossessionStatus

    h = possession_harness
    original_flush = AsyncSession.flush

    async def fail_after_flush(session, *args, **kwargs):
        await original_flush(session, *args, **kwargs)
        raise RuntimeError("possession flush failed")

    with monkeypatch.context() as patch:
        patch.setattr(AsyncSession, "flush", fail_after_flush)
        with pytest.raises(RuntimeError, match="possession flush failed"):
            await h.application.execute_possession(h.scene, h.user, h.target)
    actor = await h.manager.get_user_query_data(h.user, history=False)
    target = await h.manager.get_user_query_data(h.target, history=False)
    assert actor is not None
    assert target is not None
    assert (actor.length, target.length) == (-70.0, 49.998)
    assert actor.challenge_tier == target.challenge_tier == 1
    retry = await asyncio.wait_for(
        h.application.execute_possession(h.scene, h.user, h.target), timeout=3
    )
    assert retry.type is PossessionStatus.COMPLETED


async def test_possession_serializes_duplicate_calls_and_target_growth(
    possession_harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    import asyncio

    from nonebot_plugin_impart_plus.impart import app as app_module
    from nonebot_plugin_impart_plus.impart.core import GrowthMode, PossessionStatus

    h = possession_harness
    entered = asyncio.Event()
    release = asyncio.Event()
    original_settle = h.manager.settle_possession
    monkeypatch.setattr(app_module, "get_random_num", lambda: 1.0)

    async def delayed_settle(*args):
        entered.set()
        await release.wait()
        return await original_settle(*args)

    monkeypatch.setattr(h.manager, "settle_possession", delayed_settle)
    first = asyncio.create_task(
        h.application.execute_possession(h.scene, h.user, h.target)
    )
    try:
        await asyncio.wait_for(entered.wait(), timeout=3)
        second = asyncio.create_task(
            h.application.execute_possession(h.scene, h.user, h.target)
        )
        growth = asyncio.create_task(
            h.application.grow_target(h.scene, h.target, h.user, GrowthMode.LENGTH)
        )
    finally:
        release.set()
    results = await asyncio.wait_for(asyncio.gather(first, second, growth), timeout=3)
    assert [result.type for result in results[:2]] == [
        PossessionStatus.COMPLETED,
        PossessionStatus.LOCKED,
    ]
    assert await h.manager.get_jj_length(h.target) == 19.999
    assert await h.manager.get_jj_length(h.user) == 25.999


async def test_pk_and_growth_report_only_new_possession_unlocks(
    game_harness, database_harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    from nonebot_plugin_uniref import encode_ref

    from nonebot_plugin_impart_plus.impart import app as app_module
    from nonebot_plugin_impart_plus.impart.core import LengthState
    from nonebot_plugin_impart_plus.infra.database import UserData

    h = game_harness
    await h.manager.set_scene_enabled(h.scene, True)
    async with database_harness.session_factory() as session, session.begin():
        session.add_all(
            UserData(
                user_ref=encode_ref(user),
                user_namespace=user.namespace,
                jj_length=length,
                win_probability=0.4,
                challenge_tier=tier,
            )
            for user, length, tier in ((h.user, -29.8, 0), (h.target, -31.0, 1))
        )
    monkeypatch.setattr(app_module.random, "random", lambda: 0.0)
    monkeypatch.setattr(app_module, "get_random_num", lambda: 1.0)
    pk = await h.application.execute_pk(h.scene, h.user, (h.target,))
    assert pk.unlocked_users == {h.user: 1}
    h.cooldown.pk_cd_data.clear()
    repeated = await h.application.execute_pk(h.scene, h.user, (h.target,))
    assert repeated.unlocked_users == {}
    # 回落到25～30的既有称号也应该由同一查询快照展示。
    await h.manager.set_jj_length(h.user, 3.0)
    query = await h.application.query_user(h.scene, h.user, h.user)
    assert query.state is LengthState.ABYSS_LORD


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
    assert "is_near_zero" not in schema[user_table]
    assert "is_zero_or_neg" not in schema[user_table]
    assert "challenge_tier" in schema[user_table]
    assert "is_challenging" not in schema[user_table]
    assert "challenge_completed" not in schema[user_table]
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


async def test_pk_reports_each_opponents_actual_completed_tier(
    game_harness, database_harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    from nonebot_plugin_uniref import UserRef, encode_ref

    from nonebot_plugin_impart_plus.impart import app as app_module
    from nonebot_plugin_impart_plus.infra.database import UserData

    h = game_harness
    second = UserRef("QQClient", "second-target")
    await h.manager.set_scene_enabled(h.scene, True)
    async with database_harness.session_factory() as session, session.begin():
        session.add_all(
            UserData(
                user_ref=encode_ref(user),
                user_namespace=user.namespace,
                jj_length=length,
                win_probability=probability,
                challenge_tier=tier,
            )
            for user, length, probability, tier in (
                (h.user, -100, 0.5, 1),
                (h.target, -319.8, 0.4, 1),
                (second, -1049.8, 0.35, 2),
            )
        )
    monkeypatch.setattr(app_module.random, "random", lambda: 1.0)
    monkeypatch.setattr(app_module, "get_random_num", lambda: 1.0)
    outcome = await h.application.execute_pk(h.scene, h.user, (h.target, second))
    assert outcome.unlocked_users == {h.target: 2, second: 3}
    assert list(outcome.unlocked_users) == [h.target, second]
    assert [p.challenge.tier for p in outcome.targets if p.challenge] == [2, 3]
    states = await h.manager.get_user_states(h.target, second)
    assert (states[h.target].length, states[second].length) == (-320.8, -1051.3)
    assert states[h.target].win_probability == pytest.approx(0.4875)
    assert states[second].win_probability == pytest.approx(0.34 * 10 / 7)


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
    await manager.settle_interaction_volumes({qq_user: (3.0, None)})
    await manager.settle_interaction_volumes({telegram_user: (4.0, None)})

    assert await manager.get_jj_length(qq_user) == 11.0
    assert await manager.get_jj_length(telegram_user) == 12.0
    qq_query = await manager.get_user_query_data(qq_user, history=False)
    telegram_query = await manager.get_user_query_data(telegram_user, history=False)
    assert qq_query is not None
    assert qq_query.records[manager.get_today()] == 3.0
    assert telegram_query is not None
    assert telegram_query.records[manager.get_today()] == 4.0

    async with database_harness.session_factory() as session:
        users = (await session.execute(select(UserData))).scalars().all()
    projections = {user.user_ref: user.user_namespace for user in users}
    assert projections == {
        encode_ref(qq_user): "QQClient",
        encode_ref(telegram_user): "Telegram",
    }


async def test_application_serializes_concurrent_interaction_updates(
    game_harness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from asyncio import gather

    from nonebot_plugin_impart_plus.impart import app as app_module
    from nonebot_plugin_impart_plus.impart.core import (
        InteractionAction,
        InteractionParticipant,
        resolve_interaction,
    )

    manager = game_harness.manager
    application = game_harness.application
    requester = game_harness.user
    recipient = game_harness.target
    await manager.add_new_user(requester)
    await manager.add_new_user(recipient)
    await manager.set_jj_length(recipient, -6.0)
    await manager.settle_interaction_volumes({recipient: (990.0, None)})
    resolution = resolve_interaction(InteractionAction.INJECT, 10.0, 4.0)
    feminization_calls = 0

    def feminization_roll() -> float:
        nonlocal feminization_calls
        feminization_calls += 1
        return 0.999

    monkeypatch.setattr(app_module.random, "uniform", lambda *_: 20.0)
    monkeypatch.setattr(app_module.random, "randint", lambda *_: 1)
    monkeypatch.setattr(app_module.random, "random", feminization_roll)

    results = await gather(
        application.complete_interaction(requester, recipient, resolution),
        application.complete_interaction(requester, recipient, resolution),
    )

    data = await manager.get_user_query_data(recipient, history=False)
    assert data is not None
    assert data.records[manager.get_today()] == 1030.0
    assert (
        sum(
            result.receipts[InteractionParticipant.TARGET].settlement.feminized
            for result in results
        )
        == 1
    )
    assert feminization_calls == 1
    assert await manager.get_jj_length(recipient) == -1.0


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

    missing_pk = await application.execute_pk(scene, pk_user, ())
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
        await application.execute_pk(scene, pk_user, (pk_target,)),
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
        "expected_action",
        "expected_recipient",
        "expected_fluid",
    ),
    [
        ("INJECT", 10.0, None, "INJECT", "target", "DNA"),
        ("INJECT", -10.0, 10.0, "INJECT", "requester", "DNA"),
        ("SQUEEZE", -10.0, -10.0, "SQUEEZE", "requester", "GIRL_JUICE"),
        ("SQUEEZE", 10.0, -10.0, "SQUEEZE", "target", "DNA"),
    ],
)
async def test_interaction_records_volume_for_actual_recipient(
    game_harness,
    monkeypatch: pytest.MonkeyPatch,
    requested: str,
    requester_length: float,
    target_length: float | None,
    expected_action: str,
    expected_recipient: str,
    expected_fluid: str,
) -> None:
    from nonebot_plugin_impart_plus.impart import app as app_module
    from nonebot_plugin_impart_plus.impart.core import (
        InteractionAction,
        InteractionFluid,
        InteractionParticipant,
        InteractionResolution,
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
    )
    assert isinstance(resolution, InteractionResolution)
    assert await manager.has_user(target)
    assert requester in cooldown.ejaculation_cd

    random_calls: list[str] = []

    def volume(*_: object) -> float:
        random_calls.append("volume")
        return 12.5

    def seconds(*_: object) -> int:
        random_calls.append("seconds")
        return 4

    def unexpected_feminization() -> float:
        random_calls.append("feminization")
        return 0.5

    monkeypatch.setattr(app_module.random, "uniform", volume)
    monkeypatch.setattr(app_module.random, "randint", seconds)
    monkeypatch.setattr(app_module.random, "random", unexpected_feminization)
    result = await application.complete_interaction(requester, target, resolution)

    recipient = requester if expected_recipient == "requester" else target
    other = target if recipient == requester else requester
    assert result.resolution.action is InteractionAction[expected_action]
    assert result.resolution.transfers[0].fluid is InteractionFluid[expected_fluid]
    receipt = result.receipts[InteractionParticipant(expected_recipient)]
    assert receipt.volume == 12.5
    assert result.seconds == 4
    assert receipt.settlement.total == 12.5
    recipient_data = await manager.get_user_query_data(recipient, history=False)
    other_data = await manager.get_user_query_data(other, history=False)
    assert recipient_data is not None
    assert recipient_data.records[manager.get_today()] == 12.5
    assert other_data is not None
    assert other_data.records == {}
    assert random_calls == ["volume", "seconds"]


@pytest.mark.parametrize("squeeze", [False, True])
async def test_xnn_interaction_feminizes_actual_recipient(
    game_harness,
    monkeypatch: pytest.MonkeyPatch,
    squeeze: bool,
) -> None:
    from nonebot_plugin_impart_plus.impart import app as app_module
    from nonebot_plugin_impart_plus.impart.core import (
        InteractionAction,
        InteractionResolution,
    )

    manager = game_harness.manager
    application = game_harness.application
    requester = game_harness.user
    recipient = game_harness.target
    await manager.add_new_user(requester)
    await manager.add_new_user(recipient)
    await manager.set_jj_length(recipient, -6.0)
    await manager.settle_interaction_volumes({recipient: (990.0, None)})
    participants = (recipient, requester) if squeeze else (requester, recipient)
    resolution = await application.begin_interaction(
        *participants,
        InteractionAction.SQUEEZE if squeeze else InteractionAction.INJECT,
    )
    assert isinstance(resolution, InteractionResolution)
    random_calls: list[str] = []

    def volume(*_: object) -> float:
        random_calls.append("volume")
        return 20.0

    def seconds(*_: object) -> int:
        random_calls.append("seconds")
        return 4

    def feminization() -> float:
        random_calls.append("feminization")
        return 0.999

    monkeypatch.setattr(app_module.random, "uniform", volume)
    monkeypatch.setattr(app_module.random, "randint", seconds)
    monkeypatch.setattr(app_module.random, "random", feminization)

    result = await application.complete_interaction(*participants, resolution)

    assert random_calls == ["volume", "seconds", "feminization"]
    settlement = result.receipts[resolution.transfers[0].recipient].settlement
    assert settlement.feminized
    assert not settlement.risk_warning
    assert settlement.total == 1010.0
    assert settlement.length == -1.0
    assert await manager.get_jj_length(recipient) == -1.0


async def test_interaction_settlement_rolls_back_volume_and_length(
    database_harness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_uniref import UserRef
    from sqlalchemy.ext.asyncio import AsyncSession

    from nonebot_plugin_impart_plus.infra.database import EjaculationData, UserData

    manager = database_harness.manager
    recipient = UserRef("QQClient", "rollback-recipient")
    await manager.add_new_user(recipient)
    await manager.set_jj_length(recipient, -6.0)
    other = UserRef("QQClient", "rollback-other")
    await manager.add_new_user(other)
    await manager.set_jj_length(other, -7.0)
    await manager.settle_interaction_volumes({other: (100.0, None)})

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
            await manager.settle_interaction_volumes(
                {recipient: (1000.0, 0.0), other: (1000.0, 0.0)}
            )

    async with database_harness.session_factory() as session:
        users = (await session.execute(select(UserData))).scalars().all()
        records = (await session.execute(select(EjaculationData))).scalars().all()
        assert sorted(user.jj_length for user in users) == [3.0, 4.0]
        assert len(records) == 1
        assert records[0].volume == 100.0


@pytest.mark.parametrize(
    ("initial", "rolls", "final_lengths"),
    [
        ((100.0, 200.0), (0.999, 0.999), (3.0, 4.0)),
        ((990.0, 990.0), (0.999, 0.999), (3.0, 4.0)),
        ((990.0, 990.0), (0.0, 0.999), (-2.0, 4.0)),
        ((990.0, 990.0), (0.0, 0.0), (-2.0, -1.0)),
    ],
)
async def test_cuddle_settles_opposite_outputs_and_independent_events(
    game_harness, monkeypatch: pytest.MonkeyPatch, initial, rolls, final_lengths
) -> None:
    from nonebot_plugin_impart_plus.impart import app as app_module
    from nonebot_plugin_impart_plus.impart.core import (
        InteractionAction,
        InteractionParticipant,
        InteractionResolution,
    )

    h = game_harness
    people = (h.user, h.target)
    for user, length in zip(people, (3.0, 4.0), strict=True):
        await h.manager.add_new_user(user)
        await h.manager.set_jj_length(user, length - 10.0)
    await h.manager.settle_interaction_volumes(
        {user: (total, None) for user, total in zip(people, initial, strict=True)}
    )
    resolution = await h.application.begin_interaction(
        *people, InteractionAction.INJECT
    )
    assert isinstance(resolution, InteractionResolution)
    outputs = iter((7.0, 3.0))
    random_rolls = iter(rolls)
    calls = []

    def volume(low, high):
        calls.append("volume")
        assert (low, high) == (1, 10)
        return next(outputs)

    def seconds(*_):
        calls.append("seconds")
        return 4

    def feminization():
        calls.append("feminization")
        return next(random_rolls)

    today = h.manager.get_today()
    date_calls = 0

    def get_today():
        nonlocal date_calls
        date_calls += 1
        return today

    monkeypatch.setattr(app_module.random, "uniform", volume)
    monkeypatch.setattr(app_module.random, "randint", seconds)
    monkeypatch.setattr(app_module.random, "random", feminization)
    monkeypatch.setattr(h.manager, "get_today", get_today)
    result = await h.application.complete_interaction(*people, resolution)
    assert calls == ["volume", "volume", "seconds", "feminization", "feminization"]
    assert date_calls == 1
    for part, user, amount, previous, length in zip(
        InteractionParticipant, people, (3.0, 7.0), initial, final_lengths, strict=True
    ):
        receipt = result.receipts[part]
        assert receipt.volume == amount
        assert receipt.settlement.total == previous + amount
        assert receipt.settlement.length == length
        assert receipt.settlement.feminized == (length < 0)
        assert receipt.settlement.risk_warning == (previous <= 200 < previous + amount)
        snapshot = await h.manager.get_user_query_data(user, history=True)
        assert snapshot is not None
        assert snapshot.records == {today: previous + amount}
        assert await h.manager.get_jj_length(user) == length


@pytest.mark.parametrize("enter_xnn", [False, True])
async def test_interaction_freezes_action_but_uses_latest_recipient_state(
    game_harness, monkeypatch: pytest.MonkeyPatch, enter_xnn: bool
) -> None:
    from nonebot_plugin_impart_plus.impart import app as app_module
    from nonebot_plugin_impart_plus.impart.core import (
        InteractionAction,
        InteractionFluid,
        InteractionParticipant,
        InteractionResolution,
    )

    h = game_harness
    people = (h.user, h.target)
    starts = (-30.0, -10.0) if enter_xnn else (3.0, 4.0)
    for user, length in zip(people, starts, strict=True):
        await h.manager.add_new_user(user)
        await h.manager.set_jj_length(user, length - 10.0)
    await h.manager.settle_interaction_volumes(dict.fromkeys(people, (990.0, None)))
    resolution = await h.application.begin_interaction(
        *people, InteractionAction.SQUEEZE
    )
    assert isinstance(resolution, InteractionResolution)
    # 等待期间形态改变：成长离开 XNN，或夺舍进入 XNN。
    await h.manager.set_jj_length(h.user, 33.0 if enter_xnn else 2.0)
    rolls = []

    def volume(low, high):
        assert (low, high) == (1, 100 if enter_xnn else 10)
        return high

    def feminization():
        rolls.append("roll")
        return 0.0

    monkeypatch.setattr(app_module.random, "uniform", volume)
    monkeypatch.setattr(app_module.random, "randint", lambda *_: 4)
    monkeypatch.setattr(app_module.random, "random", feminization)
    result = await h.application.complete_interaction(*people, resolution)
    assert len(rolls) == 1
    assert result.resolution is resolution
    self_result = result.receipts[InteractionParticipant.REQUESTER].settlement
    assert self_result.feminized is enter_xnn
    assert self_result.length == (-2.0 if enter_xnn else 5.0)
    if enter_xnn:
        assert resolution.action is InteractionAction.SQUEEZE
        assert resolution.transfers[0].fluid is InteractionFluid.GIRL_JUICE
    else:
        assert resolution.action is InteractionAction.CUDDLE
        assert result.receipts[InteractionParticipant.TARGET].settlement.feminized


async def test_interaction_rechecks_cooldown_after_target_selection(
    game_harness,
) -> None:
    from asyncio import gather

    from nonebot_plugin_uniref import UserRef

    from nonebot_plugin_impart_plus.impart.app import (
        InteractionGuard,
        InteractionGuardType,
    )
    from nonebot_plugin_impart_plus.impart.core import (
        InteractionAction,
        InteractionResolution,
    )

    h = game_harness
    await h.manager.set_scene_enabled(h.scene, True)
    await h.manager.add_new_user(h.user)
    guards = await gather(
        h.application.prepare_interaction(h.scene, h.user),
        h.application.prepare_interaction(h.scene, h.user),
    )
    assert all(guard.type is InteractionGuardType.ALLOWED for guard in guards)
    targets = (h.target, UserRef("QQClient", "other-target"))
    for target in targets:
        h.cooldown.record_interaction(target)
    results = await gather(
        *(
            h.application.begin_interaction(h.user, target, InteractionAction.INJECT)
            for target in targets
        )
    )
    assert sum(isinstance(result, InteractionResolution) for result in results) == 1
    for target, result in zip(targets, results, strict=True):
        if isinstance(result, InteractionGuard):
            assert result.type is InteractionGuardType.COOLING_DOWN
            assert not await h.manager.has_user(target)
        else:
            assert await h.manager.has_user(target)
    h.cooldown.fuck_cd_time = 0
    for target in targets:
        result = await h.application.begin_interaction(
            h.user, target, InteractionAction.INJECT
        )
        assert isinstance(result, InteractionResolution)


async def test_query_snapshot_filters_today_and_orders_history(
    game_harness,
    database_harness,
) -> None:
    from nonebot_plugin_uniref import encode_ref

    from nonebot_plugin_impart_plus.infra.database import EjaculationData

    manager = game_harness.manager
    application = game_harness.application
    scene = game_harness.scene
    user = game_harness.user
    today = manager.get_today()
    await manager.add_new_user(user)
    await manager.set_scene_enabled(scene, True)
    async with database_harness.session_factory() as session, session.begin():
        session.add_all(
            [
                EjaculationData(
                    user_ref=encode_ref(user),
                    date=today,
                    volume=5.5,
                ),
                EjaculationData(
                    user_ref=encode_ref(user),
                    date="2026-08-30",
                    volume=3.0,
                ),
            ]
        )

    daily = await manager.get_user_query_data(user, history=False)
    outcome = await application.query_user(scene, user, user, history=True)

    assert daily is not None
    assert list(daily.records) == [today]
    assert list(outcome.history) == sorted(("2026-08-30", today))
    assert outcome.today_total == 5.5
    assert outcome.history_total == 8.5


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

    mixed_positive = await application.execute_pk(
        scene, positive[0], (negative_win[0],)
    )
    mixed_negative = await application.execute_pk(
        scene, negative_win[0], (positive[0],)
    )

    assert mixed_positive.type is PkOutcomeType.WORLD_MISMATCH
    assert mixed_positive.mode is mode.LENGTH
    assert mixed_negative.type is PkOutcomeType.WORLD_MISMATCH
    assert mixed_negative.mode is mode.DEPTH
    assert win_roll_calls == growth_roll_calls == 0
    assert cooldown.pk_cd_data == {}
    assert await manager.get_jj_length(positive[0]) == 10.0
    assert await manager.get_jj_length(negative_win[0]) == -10.0

    positive_result = await application.execute_pk(scene, positive[0], (positive[1],))
    negative_win_result = await application.execute_pk(
        scene, negative_win[0], (negative_win[1],)
    )
    negative_loss_result = await application.execute_pk(
        scene, negative_loss[0], (negative_loss[1],)
    )

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


async def test_pk_settlement_rolls_back_all_users_after_flush(
    database_harness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_uniref import UserRef, encode_ref
    from sqlalchemy import update
    from sqlalchemy.ext.asyncio import AsyncSession

    from nonebot_plugin_impart_plus.infra.database import UserData

    manager = database_harness.manager
    attacker = UserRef("QQClient", "pk-rollback-attacker")
    defenders = (
        UserRef("QQClient", "pk-rollback-defender-1"),
        UserRef("QQClient", "pk-rollback-defender-2"),
        UserRef("QQClient", "pk-rollback-defender-3"),
        UserRef("QQClient", "pk-rollback-defender-4"),
    )
    for user in (attacker, *defenders):
        await manager.add_new_user(user)
    async with database_harness.session_factory() as session, session.begin():
        await session.execute(
            update(UserData).values(
                jj_length=319.9, challenge_tier=1, win_probability=0.4
            )
        )
        await session.execute(
            update(UserData)
            .where(UserData.user_ref == encode_ref(attacker))
            .values(jj_length=1001, challenge_tier=3, win_probability=0.5)
        )
    before_states = await manager.get_user_states(attacker, *defenders)
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
                defenders,
                win_roll=1.0,
                random_num=1.0,
            )

    assert await manager.get_user_states(attacker, *defenders) == before_states


@pytest.mark.parametrize(
    ("tier", "count", "initial_length", "gain"),
    [(1, 2, 100.0, 1.2), (2, 3, 500.0, 2.7), (3, 4, 1500.0, 4.8)],
)
async def test_ranked_pk_uses_one_roll_and_one_cooldown(
    game_harness,
    database_harness,
    monkeypatch: pytest.MonkeyPatch,
    tier: int,
    count: int,
    initial_length: float,
    gain: float,
) -> None:
    from nonebot_plugin_uniref import UserRef, encode_ref
    from sqlalchemy import update

    from nonebot_plugin_impart_plus.impart import app as app_module
    from nonebot_plugin_impart_plus.impart.app import PkOutcomeType
    from nonebot_plugin_impart_plus.infra.database import UserData

    manager = game_harness.manager
    application = game_harness.application
    scene = game_harness.scene
    attacker = UserRef("QQClient", "pk-dual-attacker")
    defenders = tuple(
        UserRef("QQClient", f"pk-defender-{index}") for index in range(count)
    )
    await manager.set_scene_enabled(scene, True)
    for user in (attacker, *defenders):
        await manager.add_new_user(user)
    await manager.set_jj_length(attacker, initial_length - 10.0)
    async with database_harness.session_factory() as session, session.begin():
        await session.execute(
            update(UserData)
            .where(UserData.user_ref == encode_ref(attacker))
            .values(challenge_tier=tier)
        )

    calls = {"win": 0, "growth": 0}

    def win_roll() -> float:
        calls["win"] += 1
        return 0.0

    def growth_roll() -> float:
        calls["growth"] += 1
        return 0.6

    monkeypatch.setattr(app_module.random, "random", win_roll)
    monkeypatch.setattr(app_module, "get_random_num", growth_roll)

    preparation = await application.prepare_pk(scene, attacker)
    outcome = await application.execute_pk(scene, attacker, defenders)

    assert (preparation.enabled, preparation.max_targets) == (True, count)
    assert outcome.type is PkOutcomeType.COMPLETED
    assert outcome.unlocked_users == {}
    assert outcome.attacker_change == gain
    assert [target.length_change for target in outcome.targets] == [-0.6] * count
    assert calls == {"win": 1, "growth": 1}
    assert set(game_harness.cooldown.pk_cd_data) == {attacker}
    assert await manager.get_jj_length(attacker) == initial_length + gain
    states = await manager.get_user_states(*defenders)
    assert [states[user].length for user in defenders] == [9.4] * count
    assert all(state.challenge_tier == 0 for state in states.values())
    assert await manager.get_win_probability(attacker) == 0.49
    assert [await manager.get_win_probability(user) for user in defenders] == [
        0.51
    ] * count

    mode = game_harness.growth_mode.LENGTH
    gave = await application.grow_target(scene, attacker, defenders[0], mode)
    received = await application.grow_target(scene, defenders[1], attacker, mode)
    own = await application.grow_self(scene, attacker, mode)
    assert gave.amount == 0.6
    assert received.amount == own.amount == round(0.6 * (tier + 1), 3)
    assert calls == {"win": 1, "growth": 4}


@pytest.mark.parametrize(
    ("tier", "length", "lower_length"), [(1, 100, 20), (2, 500, 100), (3, 1500, 500)]
)
async def test_ranked_pk_guards_before_cooldown_and_random(
    game_harness,
    database_harness,
    monkeypatch: pytest.MonkeyPatch,
    tier: int,
    length: float,
    lower_length: float,
) -> None:
    from nonebot_plugin_uniref import UserRef, encode_ref
    from sqlalchemy import update

    from nonebot_plugin_impart_plus.impart import app as app_module
    from nonebot_plugin_impart_plus.impart.app import PkOutcomeType
    from nonebot_plugin_impart_plus.infra.database import UserData

    manager = game_harness.manager
    application = game_harness.application
    scene = game_harness.scene
    attacker = UserRef("QQClient", "pk-guard-attacker")
    negative = UserRef("QQClient", "pk-guard-negative")
    missing = tuple(
        UserRef("QQClient", f"pk-guard-missing-{index}") for index in range(tier)
    )
    targets = (negative, *missing)
    await manager.set_scene_enabled(scene, True)
    for user in (attacker, negative):
        await manager.add_new_user(user)
    await manager.set_jj_length(attacker, length - 10)
    await manager.set_jj_length(negative, -20.0)
    async with database_harness.session_factory() as session, session.begin():
        await session.execute(
            update(UserData)
            .where(UserData.user_ref == encode_ref(attacker))
            .values(challenge_tier=tier)
        )

    def unexpected_random() -> float:
        raise AssertionError("门禁拒绝不应生成PK随机数")

    monkeypatch.setattr(app_module.random, "random", unexpected_random)
    monkeypatch.setattr(app_module, "get_random_num", unexpected_random)

    preparation = await application.prepare_pk(scene, attacker)
    created = await application.execute_pk(scene, attacker, targets)
    mismatch = await application.execute_pk(scene, attacker, targets)
    async with database_harness.session_factory() as session, session.begin():
        await session.execute(
            update(UserData)
            .where(UserData.user_ref == encode_ref(attacker))
            .values(challenge_tier=tier - 1, jj_length=lower_length)
        )
    lost_entitlement = await application.execute_pk(scene, attacker, targets)

    still_legal = await application.execute_pk(scene, attacker, targets[:-1])

    assert preparation.max_targets == tier + 1
    assert created.type is PkOutcomeType.USERS_CREATED
    assert created.created_users == missing
    assert mismatch.type is PkOutcomeType.WORLD_MISMATCH
    assert lost_entitlement.type is PkOutcomeType.MULTI_TARGET_UNAVAILABLE
    assert still_legal.type is PkOutcomeType.WORLD_MISMATCH
    assert game_harness.cooldown.pk_cd_data == {}


async def test_growth_settlement_rolls_back_length_probability_and_tier(
    database_harness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_uniref import UserRef
    from sqlalchemy.ext.asyncio import AsyncSession

    from nonebot_plugin_impart_plus.impart.core import GrowthMode

    manager = database_harness.manager
    user = UserRef("QQClient", "growth-rollback")
    await manager.add_new_user(user)
    await manager.set_jj_length(user, 14.5)
    original_flush = AsyncSession.flush

    async def fail_after_flush(session, *args, **kwargs):
        await original_flush(session, *args, **kwargs)
        raise RuntimeError("growth flush failed")

    with monkeypatch.context() as patch:
        patch.setattr(AsyncSession, "flush", fail_after_flush)
        with pytest.raises(RuntimeError, match="growth flush failed"):
            await manager.settle_growth(user, GrowthMode.LENGTH, random_num=1.0)

    state = (await manager.get_user_states(user))[user]
    assert (state.length, state.win_probability, state.challenge_tier) == (24.5, 0.5, 0)


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
        defender_refs: tuple[UserRef, ...],
    ) -> PkOutcome:
        nonlocal execution_calls
        execution_calls += 1
        if execution_calls == 1:
            first_entered.set()
            await release_first.wait()
        return await original_execute(attacker_ref, defender_refs)

    monkeypatch.setattr(manager, "is_scene_enabled", scene_enabled)
    monkeypatch.setattr(application, "_execute_pk", delayed_execute)
    monkeypatch.setattr(app_module.random, "random", lambda: 0.0)
    monkeypatch.setattr(app_module, "get_random_num", lambda: 1.0)

    first = asyncio.create_task(
        application.execute_pk(scene, first_attacker, (target,))
    )
    await first_entered.wait()
    second = asyncio.create_task(
        application.execute_pk(scene, second_attacker, (target,))
    )
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

    length = await application.grow_self(scene, length_user, mode.LENGTH)
    depth = await application.grow_self(scene, depth_user, mode.DEPTH)
    wrong_state = await application.grow_self(scene, wrong_state_user, mode.DEPTH)

    assert (length.type.value, length.new_length) == ("completed", 11.25)
    assert (depth.type.value, depth.new_length) == ("completed", -1.25)
    assert length.amount == depth.amount == 1.25
    assert wrong_state.type.value == "wrong_state"
    assert await manager.get_jj_length(wrong_state_user) == 10.0
    assert generated == 2
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
    await manager.set_win_probability(positive_challenger, -0.1)
    await manager.set_win_probability(negative_challenger, -0.1)

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

    assert self_outcome.challenge is not None
    assert target_outcome.challenge is not None
    assert self_outcome.new_length == target_outcome.new_length == -25.0
    assert await manager.get_win_probability(self_user) == 0.45
    assert await manager.get_win_probability(target) == 0.45


@pytest.mark.parametrize("ranking", [False, True], ids=["query", "ranking"])
async def test_query_and_interaction_share_user_initialization(
    game_harness, monkeypatch: pytest.MonkeyPatch, ranking: bool
) -> None:
    import asyncio

    from nonebot_plugin_uniref import UserRef

    from nonebot_plugin_impart_plus.impart.app import (
        InteractionGuardType,
        QueryOutcomeType,
        RankingOutcomeType,
    )

    h = game_harness
    await h.manager.set_scene_enabled(h.scene, True)
    if ranking:
        for index in range(5):
            await h.manager.add_new_user(UserRef("QQClient", f"seed-{index}"))

    original_add = h.manager.add_new_user
    insert_started = asyncio.Event()
    calls = []

    async def slow_add(user_ref: UserRef) -> None:
        calls.append(user_ref)
        insert_started.set()
        await asyncio.sleep(0.05)
        await original_add(user_ref)

    monkeypatch.setattr(h.manager, "add_new_user", slow_add)

    async def query_after_insert_started():
        await insert_started.wait()
        if ranking:
            return await h.application.query_ranking(h.scene, h.user)
        return await h.application.query_user(h.scene, h.user, h.user)

    interaction, query = await asyncio.wait_for(
        asyncio.gather(
            h.application.prepare_interaction(h.scene, h.user),
            query_after_insert_started(),
        ),
        timeout=3,
    )

    assert interaction.type is InteractionGuardType.USER_CREATED
    assert query.type is (
        RankingOutcomeType.COMPLETED if ranking else QueryOutcomeType.COMPLETED
    )
    assert calls == [h.user]
    assert await h.manager.get_jj_length(h.user) == 10.0
    assert h.cooldown.ejaculation_cd == {}


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

    newcomer = UserRef("Telegram", "newcomer")
    assert (
        await application.query_ranking(telegram_scene, newcomer)
    ).type is RankingOutcomeType.TOO_FEW
    assert not await manager.has_user(newcomer)
