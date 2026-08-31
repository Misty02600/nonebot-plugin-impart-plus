# PLAN-0002：采用 UniRef 持久化身份

| 状态 | 优先级 | 最后更新 | 依赖 |
|---|---|---|---|
| 讨论中 | 中 | 2026-08-31 | PLAN-0001 完成 Alconna 接入切片后、扩大 Adapter 声明前 |

## 背景

当前数据库把 QQ 用户号和群号直接存为整数主键。只要插件仍是 OneBot V11 单平台，这个模型足够；一旦同一数据库承载 Telegram、Discord 或其他平台，裸 ID 会发生跨平台碰撞，群、频道和私聊场景也无法由单个 `groupid` 表达。

[`nonebot-plugin-uniref`](https://github.com/Misty02600/nonebot-plugin-uniref) 提供可比较、可编码、可持久化的 `UserRef(scope, id)` 与 `SceneRef(scope, type, id)`。本计划将它用于数据库和冷却键；它不是 Alconna matcher 或 Uninfo 运行时会话的替代品。

项目已经确认不把首轮支持范围限制为 OneBot V11，最终 Adapter 声明取 Alconna、Uninfo、UniRef 三插件支持集合的交集。因此 UniRef 不再只是候选评估：它必须在 PLAN-0001 扩大 `PluginMetadata.supported_adapters` 前完成，用来消除跨 scope 的持久化 ID 碰撞。

## UniRef 价值与边界

### 已核对版本与质量

- PyPI 最新版：`nonebot-plugin-uniref 0.2.0`。
- 最新活跃分支：唯一的 `main`，审查基准 `ec2ee8f0b070c20293cd57ac5459a87d43afc50b`；它比 `v0.2.0` tag 多一个可选依赖类型检查 CI 修正。
- 依赖：Uninfo ≥0.11.1、NoneBot ≥2.5.0；`[alconna]` extra 使用 Alconna ≥0.62.1。
- 最新 CI 在 Python 3.11–3.14、Ruff 和 BasedPyright 上全部成功。
- 公开面小且有 ADR：Ref 不绑定 Bot，不拥有业务数据库；只从已验证来源生成持久化身份；Target 转换是可选集成。

### 对本插件的直接价值

| 当前数据或能力 | UniRef 可提供的价值 |
|---|---|
| `UserData.userid: int` | 用规范编码的 `UserRef` 区分不同 scope 下的同值用户 ID |
| `EjaculationData.userid: int` | 注入记录与用户状态使用同一稳定实体引用 |
| `GroupData.groupid: int` | 用 `SceneRef` 表示群、私聊或频道场景，不把所有场景压成 group ID |
| 冷却字典的裸用户 ID | 用编码 Ref 避免跨平台用户碰撞 |
| 事件外主动发送 | `to_target(ref, bot=?)` 可以恢复 Alconna Target，但当前插件没有主动发送需求，短期价值低 |

### 不解决的问题

- 不提供成员列表、昵称资料、owner/admin 角色或权限；这些仍由 Uninfo `Session`/`Interface` 提供。
- 不提供 `MemberRef`、公共 Registry、ORM 模型或数据库迁移。
- 不保证 Bot 在线、目标可达或当前仍有权限。
- 自动提取只验证 OneBot V11 × QQClient、原生 Telegram 和原生 Discord；相同 scope 的其他 Adapter 默认拒绝。
- Telegram topic 当前因 ID 仅在父 chat 内唯一而显式拒绝。

因此，UniRef 对“跨平台持久化身份”价值高，对“只把 matcher 换成 Alconna”价值低。

## 当前数据设计与重构边界

- [`infra/database.py`](../../../src/nonebot_plugin_impart_plus/infra/database.py) 的三张表都以整数 QQ ID 或群号为核心。
- [`impart/app.py`](../../../src/nonebot_plugin_impart_plus/impart/app.py) 和 `DataManager` 方法签名仍使用 `int`/数字字符串。
- 插件尚未发布到 NoneBot 插件市场，当前数据库契约始终视为全新 v1：可以直接重建表和字段，不保留开发期数据库兼容。
- [`infra/database.py`](../../../src/nonebot_plugin_impart_plus/infra/database.py) 现有旧列兼容逻辑也属于发布前遗留；最终身份 schema 落地时一并删除，不扩展为 migration framework。

## 技术路线

本计划不在 PLAN-0001 的 matcher 迁移中顺带修改数据库。先完成 Alconna 接入切片，再单独实施本计划并直接修改 v1 schema：

1. 直接调整 `userdata`、`groupdata`、`ejaculation_data` 的用户和场景键，使用 `encode_ref()` 结果；不创建 v2 或 legacy 表。
2. 删除旧列探测、回填和兼容分支；开发环境中的旧 `impart.db` 由维护者删除后按新 schema 重建。
3. `DataManager` API 接收 `UserRef`/`SceneRef`，在 infra 内编码，不让 wire string 扩散到 core。
4. `GameApplication` 接收 Ref 或更窄的稳定身份对象；core 的纯数值规则不感知身份。
5. 冷却键改为 `encode_ref(user_ref)`；群开关以场景 Ref 为键。
6. 只有需要事件外发送时才调用 `to_target()`，不把 Target 持久化进业务表。

该规则持续到插件首次发布到 NoneBot 插件市场；发布后若再修改持久化 schema，届时重新建立迁移与兼容策略，不能把本阶段的“直接重建”惯例延伸到已发布版本。

### 预期提交

1. `feat: 引入UniRef持久化身份依赖`
2. `refactor: 扩展DataManager身份参数`
3. `refactor: 使用Ref重建身份数据表`
4. `refactor: 使用Ref统一冷却与场景键`
5. `test: 验证跨平台身份隔离`
6. `docs: 记录持久化身份协议`

测试仍遵循用户确认的顺序：先完成对应 schema 或身份切片，再立即增加该切片的行为测试；不增加旧数据库升级、回填或幂等迁移测试。

## 待确认事项

### D-103 · P1：是否按 Bot 隔离用户状态

UniRef 的 Ref 默认不含 Bot，同一平台的两个 Bot 会看到相同用户 Ref。

- **A：同平台 Bot 共享状态。** 与当前 QQ 用户按裸账号共享状态的语义一致。
- **B：按 Bot 隔离。** 业务键额外加入 `self_id`，但 Ref 本身保持不变。
- **建议：A。** 保持现有语义；只有明确需要多 Bot 独立游戏世界时再增加 Bot 维度。

### D-104 · P1：遇到 UniRef 未验证来源如何处理

- **A：显式拒绝该命令并提示平台暂未支持。**
- **B：回退到裸 ID。** 会破坏持久化唯一性保证。
- **建议：A。** 持久化身份应失败安全，不写入来源不明确、无法稳定复现的键。

## 完成标准与验证

| 覆盖条件或输入 | 预期结果 | 验证方式 |
|---|---|---|
| 空数据库首次启动 | 直接创建采用 Ref 键的 v1 表，不出现 v2 或 legacy 表 | schema 集成测试 |
| 旧开发数据库 | 不执行探测、回填或兼容；删除后可按当前 v1 schema 重建 | 源码审查与干净数据库启动测试 |
| 同值用户 ID、不同 scope | 生成不同主键且互不读取 | DataManager 集成测试 |
| 两个 OneBot Bot 观察同一 QQ 用户 | 按 D-103 得到相同或隔离状态 | 身份键参数化测试 |
| 未验证 Adapter/scope | 按 D-104 显式失败，不写入数据库 | 依赖与数据层测试 |
| Telegram topic | 保持 UniRef 明确拒绝，不生成碰撞 SceneRef | 错误路径测试 |
| 冷却和群开关 | 使用 Ref 后不发生跨平台碰撞 | 应用层与冷却测试 |
| 发布前 schema 代码 | 不包含 migration runner、旧列兼容或 legacy 表分支 | 静态审查与定向测试 |
| 质量门 | Ruff、BasedPyright、pytest、构建全部通过 | 项目标准命令 |

## 已确认事项

- 2026-08-31 · D-101：先迁移 Alconna 接入，再单独采用 UniRef 重构持久化身份；PLAN-0001 只有在本计划完成后才扩大 Adapter 声明。
- 2026-08-31 · D-102：插件首次进入 NoneBot 插件市场前始终按全新 v1 开发；schema 直接修改，旧开发数据库直接重建，不编写迁移、回填、v2 表或 legacy 兼容逻辑。

## 相关文档

- [当前项目架构](../../architecture/overview.md)
- [UniRef 仓库 main@ec2ee8f](https://github.com/Misty02600/nonebot-plugin-uniref/tree/ec2ee8f0b070c20293cd57ac5459a87d43afc50b)
- [UniRef v0.2.0](https://github.com/Misty02600/nonebot-plugin-uniref/releases/tag/v0.2.0)
- [PLAN-0001：迁移 Alconna 跨平台接入层](PLAN-0001-alconna-multiplatform-migration.md)
