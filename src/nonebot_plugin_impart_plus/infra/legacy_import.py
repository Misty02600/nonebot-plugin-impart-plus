"""从上游插件的 SQLite 数据库执行一次性只读导入。"""

import asyncio
import sqlite3
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nonebot import get_plugin_config
from nonebot_plugin_localstore import get_data_dir
from nonebot_plugin_localstore.config import Config as LocalStoreConfig
from nonebot_plugin_uniref import SceneKind, SceneRef, UserRef, encode_ref
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import EjaculationData, SceneData, UserData

LEGACY_SOURCE = "nonebot_plugin_impart"
_LEGACY_DATABASE_NAME = "impart.db"
_QQ_NAMESPACE = "QQClient"


@dataclass(frozen=True, slots=True)
class _LegacySnapshot:
    users: tuple[dict[str, Any], ...]
    scenes: tuple[dict[str, Any], ...]
    injections: tuple[dict[str, Any], ...]


def legacy_database_path() -> Path:
    """返回上游插件按当前 LocalStore 配置得到的标准数据库路径。"""
    config = get_plugin_config(LocalStoreConfig)
    if configured := config.localstore_plugin_data_dir.get(LEGACY_SOURCE):
        return configured / _LEGACY_DATABASE_NAME
    return get_data_dir(None) / LEGACY_SOURCE / _LEGACY_DATABASE_NAME


def _table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {
        str(row["name"]) for row in connection.execute(f'PRAGMA table_info("{table}")')
    }


def _require_columns(
    connection: sqlite3.Connection,
    table: str,
    required: set[str],
) -> set[str]:
    columns = _table_columns(connection, table)
    missing = required - columns
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"legacy table {table!r} is missing columns: {missing_text}")
    return columns


def _optional_value(
    row: sqlite3.Row,
    columns: set[str],
    name: str,
    default: Any,
) -> Any:
    value = row[name] if name in columns else None
    return default if value is None else value


def _read_legacy_database(path: Path) -> _LegacySnapshot:
    """以只读方式加载并验证完整旧库快照。

    扩展状态列在上游历史版本中逐步加入；缺失时使用该版本原本的默认值。注入表没有唯一约束，
    因此在内存中按用户和日期合并后再交给目标事务。
    """
    uri = f"{path.resolve().as_uri()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        connection.execute("BEGIN")

        user_columns = _require_columns(
            connection,
            "userdata",
            {"userid", "jj_length", "last_masturbation_time"},
        )
        _require_columns(connection, "groupdata", {"groupid", "allow"})
        _require_columns(
            connection,
            "ejaculation_data",
            {"id", "userid", "date", "volume"},
        )

        optional_user_columns = (
            "win_probability",
            "is_challenging",
            "challenge_completed",
            "is_near_zero",
            "is_zero_or_neg",
        )
        selected_user_columns = (
            "userid",
            "jj_length",
            "last_masturbation_time",
            *(name for name in optional_user_columns if name in user_columns),
        )
        user_rows = connection.execute(
            f'SELECT {", ".join(selected_user_columns)} FROM "userdata" '
            'ORDER BY "userid"'
        ).fetchall()
        users = tuple(
            {
                "user_ref": encode_ref(UserRef(_QQ_NAMESPACE, str(row["userid"]))),
                "user_namespace": _QQ_NAMESPACE,
                "jj_length": float(row["jj_length"]),
                "last_masturbation_time": int(row["last_masturbation_time"]),
                "win_probability": float(
                    _optional_value(
                        row,
                        user_columns,
                        "win_probability",
                        0.5,
                    )
                ),
                "is_challenging": bool(
                    _optional_value(row, user_columns, "is_challenging", False)
                ),
                "challenge_completed": bool(
                    _optional_value(row, user_columns, "challenge_completed", False)
                ),
                "is_near_zero": bool(
                    _optional_value(row, user_columns, "is_near_zero", False)
                ),
                "is_zero_or_neg": bool(
                    _optional_value(row, user_columns, "is_zero_or_neg", False)
                ),
            }
            for row in user_rows
        )

        scenes = tuple(
            {
                "scene_ref": encode_ref(
                    SceneRef(
                        _QQ_NAMESPACE,
                        SceneKind.GROUP,
                        str(row["groupid"]),
                    )
                ),
                "scene_namespace": _QQ_NAMESPACE,
                "scene_type": SceneKind.GROUP.value,
                "allow": bool(row["allow"]),
            }
            for row in connection.execute(
                'SELECT "groupid", "allow" FROM "groupdata" ORDER BY "groupid"'
            )
        )

        injection_totals: dict[tuple[int, str], float] = {}
        for row in connection.execute(
            'SELECT "userid", "date", "volume" FROM "ejaculation_data" ORDER BY "id"'
        ):
            date = str(row["date"])
            if len(date) > 20:
                raise ValueError("legacy injection date exceeds 20 characters")
            key = (int(row["userid"]), date)
            injection_totals[key] = round(
                injection_totals.get(key, 0.0) + float(row["volume"]),
                3,
            )
        injections = tuple(
            {
                "user_ref": encode_ref(UserRef(_QQ_NAMESPACE, str(user_id))),
                "date": date,
                "volume": volume,
            }
            for (user_id, date), volume in sorted(injection_totals.items())
        )

    return _LegacySnapshot(users=users, scenes=scenes, injections=injections)


async def _target_has_data(session: AsyncSession) -> bool:
    for column in (UserData.user_ref, SceneData.scene_ref, EjaculationData.id):
        if (
            await session.execute(select(column).limit(1))
        ).scalar_one_or_none() is not None:
            return True
    return False


async def import_legacy_data(
    session_factory: Callable[[], AsyncSession],
    source_path: Path | None = None,
) -> bool:
    """在空目标库中一次性导入上游插件数据。

    Args:
        session_factory: 创建目标 ORM 会话的可调用对象。
        source_path: 仅供内部调用和测试覆盖的源文件；省略时使用 LocalStore 标准路径。

    Returns:
        本次成功执行导入时为 ``True``；源文件不存在、没有数据或目标已有数据时为 ``False``。

    Raises:
        RuntimeError: 源路径存在但不是文件。
        ValueError: 旧库缺少必要表或字段，或包含无法写入的新 schema 数据。
    """
    path = source_path if source_path is not None else legacy_database_path()
    if not path.exists():
        return False
    if not path.is_file():
        raise RuntimeError(f"legacy database path is not a file: {path}")

    async with session_factory() as session:
        if await _target_has_data(session):
            return False
        snapshot = await asyncio.to_thread(_read_legacy_database, path)
        if not (snapshot.users or snapshot.scenes or snapshot.injections):
            return False

        if snapshot.users:
            await session.execute(insert(UserData), snapshot.users)
        if snapshot.scenes:
            await session.execute(insert(SceneData), snapshot.scenes)
        if snapshot.injections:
            await session.execute(insert(EjaculationData), snapshot.injections)
        await session.commit()
    return True
