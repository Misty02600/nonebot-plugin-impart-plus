# PLAN-0001：迁移 Alconna 跨平台接入层

| 状态 | 完成时间 |
|---|---|
| 已完成 | 2026-09-03 |

## 问题与最终结果

插件原先把 OneBot V11 事件、消息段、群成员 API 和裸 ID 直接混入 Handler。现在 bot 接入层统一使用 Alconna 定义命令 grammar、Uninfo 提供会话与成员资料、UniRef 表达持久化身份，并通过 UniMessage 生成回复；application、core 和 infra 不再依赖 Adapter 事件。

实际实现与回归验收优先保证 OneBot V11。metadata 仍通过 `inherit_supported_adapters()` 动态继承三项接入依赖的交集，但其他 Adapter 只保持理论兼容边界，不维护逐平台事件 fixture，也不作为当前发布门槛。

## 关键改动

| 模块或路径 | 最终改动 |
|---|---|
| `bot/matchers.py` | 集中定义 Alconna grammar、matcher 与必要 dispatch，明确 command start、alias、compact、参数和传播策略 |
| `bot/handlers/` | 按 `game`、`interaction`、`records`、`control` 分组模块级 Handler，通过 Uninfo、UniRef 和 UniMessage 接入 NoneBot |
| `impart/app.py`、`impart/core.py` | 保持游戏用例和纯规则独立，不接收 Event、Session、Alconna 结果或消息对象 |
| `infra/` | 以 Ref 保存数据库与冷却身份，保留 SQLite、成员资料辅助和图片渲染等技术实现 |
| 插件入口与 README | 使用三插件动态 Adapter 交集，记录 OneBot V11 的实际支持基线和其他平台的理论边界 |

## 验证结果

| 成功标准 | 证据或结果 |
|---|---|
| 命令 grammar | 根命令、alias、command start、compact、typed At、Option、严格尾随文本和失败输入均有 parser 测试 |
| matcher 注册 | 10 个 Alconna matcher 正常注册；互动命令使用单一 `kind` 参数和单一 Handler，银趴权限 dispatch 相互独立 |
| Handler 边界 | RefContext、成员目录、权限、At、冷却释放、随机调用顺序和 UniMessage 文本/图片结构均有聚焦测试 |
| 身份与持久化 | UniRef namespace 隔离、排行榜、注入记录、SceneRef 开关和四类冷却测试通过 |
| 项目质量门 | 84 项 pytest、Ruff、BasedPyright、格式检查、sdist/wheel 构建和 `git diff --check` 全部通过 |

## 已知缺口与后续事项

- 按维护者确认，不增加 OneBot V11 事件级集成测试；现有 parser、Handler、身份、数据和插件注册测试作为当前验收边界。
- OneBot V11 以外 Adapter 不提供逐平台测试承诺；已知能力差异只保留为理论参考，不在本插件增加平台专用分支。
- 动态 metadata 交集不等于各平台已经获得相同程度的行为验证。

## 相关文档

- [当前项目架构](../../architecture/overview.md)
- [PLAN-0002：采用 UniRef 持久化身份](PLAN-0002-uniref-persistent-identity.md)
