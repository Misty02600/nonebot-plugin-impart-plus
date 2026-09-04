# PLAN-0009：导入上游插件数据

| 状态 | 完成时间 |
|---|---|
| 已完成 | 2026-09-04 |

## 问题与最终结果

`nonebot_plugin_impart` 把 OneBot V11 游戏状态保存在 LocalStore 的 `impart.db`，而当前插件使用 NoneBot ORM 与 UniRef schema。插件现在会在 ORM schema 就绪后自动检查旧库：源文件不存在、源库没有记录或三个目标业务表任一非空时安静跳过；只有目标全空且源库有数据时，才以一个目标事务复制用户、群开关和注入历史。旧 SQLite 文件始终只读且不会被移动、改名或删除。

## 关键改动

| 模块或路径 | 最终改动 |
|---|---|
| `infra/legacy_import.py` | 按当前 LocalStore 根目录及旧插件目录映射定位 `nonebot_plugin_impart/impart.db`，在一个目标 Session 中检查三张业务表；目标全空时以单个只读 SQLite 事务加载一致快照。用户和群 ID 编码到 `QQClient` UserRef/Group SceneRef，旧版本缺失的状态列使用上游默认值，重复日期注入记录汇总到一行 |
| `bot/__init__.py` | 在 ORM 之后、APScheduler 之前运行导入器，避免导入失败后留下已启动的调度器；只有实际导入时记录一条日志 |
| `tests/units/legacy_import_test.py` | 用两项聚焦测试覆盖无源跳过、完整快照、源文件不变、重复启动、旧字段默认值和非空目标跳过 |
| `docs/architecture/overview.md` | 同步启动顺序、数据所有权、失败边界和支持范围 |

## 验证结果

| 成功标准 | 证据或结果 |
|---|---|
| 数据保真 | 当前上游 schema 的用户长度、活动时间、胜率、状态、群开关全部保留；同用户同日期的 `1.111 + 2.222` 汇总为 `3.333` |
| 安全与幂等 | 旧文件导入前后字节一致；成功导入后业务表非空，后续启动直接跳过；预先存在目标数据时同样不合并或覆盖 |
| 一致快照 | WAL 源库在读取用户表后并发提交新群数据，当前只读事务继续看到启动读取时的群表状态 |
| 旧版本字段 | 缺少胜率和挑战、临界状态列时分别使用 `0.5` 与 `False` |
| 启动集成 | 真实 NoneBot startup 验证 ORM 先建表，随后从标准 LocalStore 路径导入 `user:QQClient:42`；源库无效导致失败时 APScheduler 尚未启动 |
| ORM 生命周期 | 最终三表 schema 在临时 SQLite 上通过 `upgrade → check → downgrade → upgrade → check` |
| 全量质量 | 131 项 pytest、Ruff、格式、BasedPyright、lock、build 与 `git diff --check` 全部通过；wheel 包含导入器和 migration |

## 已知缺口与后续事项

- 只识别当前 LocalStore 配置下的标准旧插件路径，不提供单独导入命令、显式文件路径、合并、覆盖或反向同步。
- 源数据只按原插件实际支持的 OneBot V11 整数 QQ/群 ID 映射到 `QQClient`；不猜测其他平台身份。
- 多个 Bot 在同一 NoneBot 进程中共享一次启动导入；不承诺多个 NoneBot 进程同时对同一目标库执行首次导入。
- 插件尚未发布到市场，本次继续直接调整 v1 初始 migration；已经运行过旧开发 revision 的本地数据库不提供兼容升级。
- 当前 Alembic 1.19.1 仍会输出两条由 NoneBot ORM 配置触发的弃用警告，不影响导入或 migration。

## 相关文档

- [当前项目架构](../../architecture/overview.md)
- [PLAN-0008：接入 NoneBot ORM](PLAN-0008-adopt-nonebot-orm.md)
