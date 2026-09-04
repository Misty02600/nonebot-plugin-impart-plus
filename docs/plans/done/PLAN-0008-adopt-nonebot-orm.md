# PLAN-0008：接入 NoneBot ORM

| 状态 | 完成时间 |
|---|---|
| 已完成 | 2026-09-04 |

## 问题与最终结果

插件原先单独维护 LocalStore `impart.db`、SQLAlchemy Engine、DeclarativeBase 和启动 `create_all()`，没有可发布的 schema 版本。现在模型、生产 Session、默认数据库配置和 schema 生命周期由 `nonebot-plugin-orm 0.8.3` 接管，包内 Alembic migration 可以升级、检查和降级数据库；游戏行为保持不变，并补齐了每日互动总量的并发累计保证。

三个模型显式使用默认 bind，以匹配 ORM 0.8.3 生成的 generic migration；可以通过 `SQLALCHEMY_DATABASE_URL` 更换默认数据库，但不承诺 multidb 插件专用 bind。

## 关键改动

| 模块或路径 | 最终改动 |
|---|---|
| `pyproject.toml`、插件入口 | 引入并先加载 `nonebot-plugin-orm[default]`，以 SQLite 作为开箱即用兜底但不锁定后端；保留 LocalStore 直接依赖，供下一阶段按上游插件数据目录定位 `impart.db` |
| `infra/database.py` | 三个模型继承 ORM `Model`、使用插件前缀表名和默认 bind；Ref 与 namespace 建立适用于目标数据库方言的长度边界；每日互动量增加 `(user_ref, date)` 唯一约束 |
| `infra/data_manager.py`、`bot/dependencies.py` | DataManager 保留可测试的 Session factory 边界，生产改用 ORM `get_session()`；持久身份在入库前验证长度，每日总量使用条件更新与插入冲突重试避免并发丢失 |
| `bot/__init__.py` | 删除本插件的启动建表钩子，只保留定时任务 |
| `migrations/f8062f5c90ba_initial_schema.py` | 首个 `nonebot_plugin_impart_plus` migration 创建三张业务表、Ref 投影索引与每日唯一约束，并提供完整 downgrade |
| `.env.test`、测试与 CI | 测试启动使用独立内存数据库和 ORM 自动同步；模型测试继续使用隔离 sessionmaker，并验证表名、默认 bind、索引、唯一约束、目标方言 DDL、长度边界和并发累计；CI 在一个 Python 版本额外执行临时 SQLite migration smoke |
| `docs/architecture/overview.md` | 同步数据库所有权、后端选择、默认连接与 multidb 边界 |

## 验证结果

| 成功标准 | 证据或结果 |
|---|---|
| migration 生命周期 | 临时 SQLite 上 `upgrade → check → downgrade nonebot_plugin_impart_plus@base → upgrade → check` 全部成功；CI 固定执行 `upgrade → check` smoke |
| schema | 创建三张插件前缀表、有限长度 Ref/namespace、namespace/type 索引与 `(user_ref, date)` 唯一约束；SQLite、PostgreSQL、MySQL 模型 DDL 均可编译，降级后本插件表为零 |
| 运行与业务回归 | ORM 依赖加载；DataManager、命令、随机、冷却和游戏状态行为未改，并发累计不会报重复键或丢失数量 |
| 静态与构建质量 | lock、Ruff、格式、BasedPyright、wheel/sdist 构建和 `git diff --check` 全部通过；wheel 包含最终 migration |

## 已知缺口与后续事项

- 上游数据导入已由 [PLAN-0009](PLAN-0009-import-upstream-data.md) 完成。
- PK 等用例仍由多个 DataManager 方法分别提交，尚未建立统一事务边界。
- `nonebot-plugin-orm 0.8.3` 搭配当前 Alembic 1.19.1 时会产生两条配置项弃用警告，但 migration 与测试正常通过。
- 当前只支持 generic 默认 bind，不支持同一 migration 在 default 与 multidb 专用 bind 之间切换。
- `[default]` 会安装 SQLite 驱动；改用其他后端时由 Bot 项目安装对应驱动并配置 URL。SQLite 有实际 migration 与持久化测试，PostgreSQL 和 MySQL 当前只做 DDL 编译验证。

## 相关文档

- [当前项目架构](../../architecture/overview.md)
- [UniRef 持久身份](PLAN-0002-uniref-persistent-identity.md)
