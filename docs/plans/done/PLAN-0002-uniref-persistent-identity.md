# PLAN-0002：采用 UniRef 持久化身份

| 状态 | 完成时间 |
|---|---|
| 已完成 | 2026-09-02 |

## 问题与最终结果

插件原先把用户和场景 ID 作为裸整数或数字字符串传入 application、冷却和 SQLite，无法隔离不同平台的同值 ID。现在 bot 接入层通过 UniRef 0.4 的单一 `RefContext` 取得 `UserRef` 和 `SceneRef`，application、DataManager 与冷却不再接受裸身份。

数据库已直接重建为全新 v1 Ref schema，没有旧 ID、旧表、迁移、回填、双写或 fallback。排行榜按 `UserRef.namespace` 分榜，同一 namespace 内仍跨场景排序。

## 关键改动

| 模块或路径 | 最终改动 |
|---|---|
| `pyproject.toml`、插件入口 | 引入 UniRef 0.4，按顺序加载 Alconna、Uninfo、UniRef，并通过 `inherit_supported_adapters()` 声明实时交集 |
| `bot/matchers.py` | 集中定义命令 grammar、matcher 和 dispatch，直接复用 Uninfo `GROUP | GUILD` 作为公开场景 Rule checker，不增加自定义场景函数或 Ref 预检层 |
| `bot/handlers/` | 统一注入 `RefContext`，在副作用前从 `user_ref`/`scene_ref` 属性取得当前身份；Alconna At 和成员目标使用 `build_user_ref()`，非用户 At 不进入业务处理，原始平台 ID 只保留给 Uninfo 查询和展示 |
| `impart/app.py` | 所有用户和场景参数改为 UserRef/SceneRef；排行榜返回类型化 `RankingEntry` |
| `infra/cooldown.py` | 四类进程内冷却直接使用可哈希 UserRef 作为键；所有用户遵守相同冷却，不提供超级用户豁免 |
| `infra/database.py` | 创建 `user_data`、`scene_data`、`ejaculation_data`，保存完整编码 Ref 和 namespace/type 查询投影；删除全部旧 schema 兼容代码 |
| `infra/data_manager.py` | 独占 Ref codec，验证投影一致性，并通过 `user_namespace` 索引查询排行榜 |

## 验证结果

| 成功标准 | 证据或结果 |
|---|---|
| 同值跨 namespace 用户隔离 | DataManager 状态、注入记录和四类冷却参数化测试通过 |
| SceneRef 开关隔离 | namespace 与 SceneKind 组合测试通过 |
| namespace 排行榜 | 各 namespace 独立人数阈值、排序和本人排名测试通过 |
| Handler 身份注入 | RefContext 无法建立时直接控制业务 Handler 是否执行；属性与目标 Ref 在 Handler 开头构造，不额外改变 matcher 的 `block` 传播语义 |
| 互动冷却规则 | 活跃冷却中的普通用户和超级用户使用相同判断，不存在配置型豁免 |
| 动态 Adapter 交集 | 当前锁定依赖下验证为 OneBot V11、Milky、Telegram、Discord、QQ、Feishu，实现未硬编码集合 |
| 无兼容层 | 源码定向搜索确认不存在旧 ID 字段、旧 DataManager API、ALTER/PRAGMA、legacy 或联合类型入口 |
| 项目质量门 | pytest、Ruff、BasedPyright、格式检查、sdist/wheel 构建和 `git diff --check` 全部通过 |

## 已知缺口与后续事项

- 现有开发环境的旧 `impart.db` 不受支持，运行当前代码前需要由维护者删除；代码不会自动迁移或删除。
- UniRef 0.4 的 QQAPI 群成员和频道用户 Ref 使用复合完整 ID；排行榜资料查询不解析该私有格式，当前可能退回 Ref ID 展示，等待上游公开的 Ref 资料查询入口。
- OneBot V11 以外 Adapter 只保持理论兼容边界，不维护真实事件、权限、成员目录或消息导出矩阵。

## 相关文档

- [当前项目架构](../../architecture/overview.md)
- [PLAN-0001：迁移 Alconna 跨平台接入层](PLAN-0001-alconna-multiplatform-migration.md)
- [UniRef v0.4.0](https://github.com/Misty02600/nonebot-plugin-uniref/tree/v0.4.0)
