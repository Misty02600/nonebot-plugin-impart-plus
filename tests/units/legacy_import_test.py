import sqlite3
from contextlib import closing
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def _create_current_legacy_database(path: Path) -> None:
    path.parent.mkdir(parents=True)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.executescript(
            """
            CREATE TABLE userdata (
                userid INTEGER PRIMARY KEY,
                jj_length FLOAT NOT NULL,
                last_masturbation_time INTEGER NOT NULL,
                win_probability FLOAT,
                is_challenging BOOLEAN,
                challenge_completed BOOLEAN,
                is_near_zero BOOLEAN,
                is_zero_or_neg BOOLEAN
            );
            CREATE TABLE groupdata (
                groupid INTEGER PRIMARY KEY,
                allow BOOLEAN NOT NULL
            );
            CREATE TABLE ejaculation_data (
                id INTEGER PRIMARY KEY,
                userid INTEGER NOT NULL,
                date VARCHAR(20) NOT NULL,
                volume FLOAT NOT NULL
            );
            """
        )
        connection.executemany(
            "INSERT INTO userdata VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                (10001, 26.5, 1234, 0.4, 1, 0, 0, 0),
                (10002, -8.25, 5678, 0.6, 0, 1, 1, 1),
            ),
        )
        connection.executemany(
            "INSERT INTO groupdata VALUES (?, ?)",
            ((20001, 1), (20002, 0)),
        )
        connection.executemany(
            "INSERT INTO ejaculation_data VALUES (?, ?, ?, ?)",
            (
                (1, 10001, "2026-09-03", 1.111),
                (2, 10001, "2026-09-03", 2.222),
                (3, 10002, "2026-09-04", 4.5),
            ),
        )


def _create_early_legacy_database(path: Path) -> None:
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.executescript(
            """
            CREATE TABLE userdata (
                userid INTEGER PRIMARY KEY,
                jj_length FLOAT NOT NULL
            );
            CREATE TABLE groupdata (
                groupid INTEGER PRIMARY KEY,
                allow BOOLEAN NOT NULL
            );
            CREATE TABLE ejaculation_data (
                id INTEGER PRIMARY KEY,
                userid INTEGER NOT NULL,
                date VARCHAR(20) NOT NULL,
                volume FLOAT NOT NULL
            );
            INSERT INTO userdata VALUES (30001, 11.5);
            """
        )


async def _create_target_database(
    path: Path,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    from nonebot_plugin_orm import Model

    from nonebot_plugin_impart_plus.infra.database import (
        EjaculationData,
        SceneData,
        UserData,
    )

    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")

    def create_tables(connection) -> None:
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
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def test_imports_complete_legacy_snapshot_once(tmp_path: Path) -> None:
    from nonebot_plugin_uniref import SceneKind, SceneRef, UserRef, encode_ref

    from nonebot_plugin_impart_plus.infra.database import (
        EjaculationData,
        SceneData,
        UserData,
    )
    from nonebot_plugin_impart_plus.infra.legacy_import import import_legacy_data

    source = tmp_path / "legacy" / "impart.db"
    engine, sessions = await _create_target_database(tmp_path / "target.db")
    try:
        assert await import_legacy_data(sessions, source) is False
        _create_current_legacy_database(source)
        original_source = source.read_bytes()

        assert await import_legacy_data(sessions, source) is True
        assert source.read_bytes() == original_source
        assert await import_legacy_data(sessions, source) is False

        async with sessions() as session:
            users = (await session.execute(select(UserData))).scalars().all()
            scenes = (await session.execute(select(SceneData))).scalars().all()
            injections = (
                (
                    await session.execute(
                        select(EjaculationData).order_by(
                            EjaculationData.user_ref,
                            EjaculationData.date,
                        )
                    )
                )
                .scalars()
                .all()
            )

        assert {
            user.user_ref: (
                user.user_namespace,
                user.jj_length,
                user.win_probability,
                user.is_challenging,
                user.challenge_completed,
                user.is_near_zero,
                user.is_zero_or_neg,
            )
            for user in users
        } == {
            encode_ref(UserRef("QQClient", "10001")): (
                "QQClient",
                26.5,
                0.4,
                True,
                False,
                False,
                False,
            ),
            encode_ref(UserRef("QQClient", "10002")): (
                "QQClient",
                -8.25,
                0.6,
                False,
                True,
                True,
                True,
            ),
        }
        assert {
            scene.scene_ref: (scene.scene_namespace, scene.scene_type, scene.allow)
            for scene in scenes
        } == {
            encode_ref(SceneRef("QQClient", SceneKind.GROUP, "20001")): (
                "QQClient",
                "group",
                True,
            ),
            encode_ref(SceneRef("QQClient", SceneKind.GROUP, "20002")): (
                "QQClient",
                "group",
                False,
            ),
        }
        assert [(row.user_ref, row.date, row.volume) for row in injections] == [
            (encode_ref(UserRef("QQClient", "10001")), "2026-09-03", 3.333),
            (encode_ref(UserRef("QQClient", "10002")), "2026-09-04", 4.5),
        ]
    finally:
        await engine.dispose()


async def test_defaults_old_columns_and_skips_non_empty_target(
    tmp_path: Path,
) -> None:
    from nonebot_plugin_uniref import UserRef, encode_ref

    from nonebot_plugin_impart_plus.infra.database import UserData
    from nonebot_plugin_impart_plus.infra.legacy_import import import_legacy_data

    source = tmp_path / "early.db"
    _create_early_legacy_database(source)

    imported_engine, imported_sessions = await _create_target_database(
        tmp_path / "imported.db"
    )
    occupied_engine, occupied_sessions = await _create_target_database(
        tmp_path / "occupied.db"
    )
    try:
        assert await import_legacy_data(imported_sessions, source) is True
        async with imported_sessions() as session:
            imported = await session.get(
                UserData,
                encode_ref(UserRef("QQClient", "30001")),
            )
        assert imported is not None
        assert imported.win_probability == 0.5
        assert imported.is_challenging is False
        assert imported.challenge_completed is False
        assert imported.is_near_zero is False
        assert imported.is_zero_or_neg is False

        async with occupied_sessions() as session:
            session.add(
                UserData(
                    user_ref=encode_ref(UserRef("QQClient", "existing")),
                    user_namespace="QQClient",
                    jj_length=10.0,
                    win_probability=0.5,
                )
            )
            await session.commit()

        with closing(sqlite3.connect(source)) as connection, connection:
            connection.execute('DROP TABLE "groupdata"')

        assert await import_legacy_data(occupied_sessions, source) is False

        async with occupied_sessions() as session:
            users = (await session.execute(select(UserData))).scalars().all()
        assert [user.user_ref for user in users] == [
            encode_ref(UserRef("QQClient", "existing"))
        ]
    finally:
        await imported_engine.dispose()
        await occupied_engine.dispose()
