# PLAN-0002：评估并采用 UniRef 持久化身份

| 状态 | 优先级 | 最后更新 | 依赖 |
|---|---|---|---|
| 讨论中 | 中 | 2026-08-30 | PLAN-0001 的平台范围决定 |

## 背景

当前数据库把 QQ 用户号和群号直接存为整数主键。只要插件仍是 OneBot V11 单平台，这个模型足够；一旦同一数据库承载 Telegram、Discord 或其他平台，裸 ID 会发生跨平台碰撞，群、频道和私聊场景也无法由单个 `groupid` 表达。

[`nonebot-plugin-uniref`](https://github.com/Misty02600/nonebot-plugin-uniref) 提供可比较、可编码、可持久化的 `UserRef(scope, id)` 与 `SceneRef(scope, type, id)`。本计划评估是否将它用于数据库和冷却键；它不是 Alconna matcher 或 Uninfo 运行时会话的替代品。

## UniRef 评估

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

## 当前数据设计与迁移风险

- [`infra/database.py`](../../../src/nonebot_plugin_impart_plus/infra/database.py) 的三张表都以整数 QQ ID 或群号为核心。
- [`impart/app.py`](../../../src/nonebot_plugin_impart_plus/impart/app.py) 和 `DataManager` 方法签名仍使用 `int`/数字字符串。
- SQLite 不能简单把现有整数主键原地升级为复合跨平台语义；只增加 nullable ref 列仍会让旧整数主键阻止不同平台同值 ID 共存。
- 既有 `impart.db` 已被 README 承诺可以沿用，任何身份迁移都必须可备份、可重跑、可验证，不能静默丢失数据。

## 技术路线

本计划不在 PLAN-0001 的 matcher 迁移中顺带修改数据库。只有 D-101 确认采用后进入实施。

推荐采用 v2 表迁移，而不是原表原地改主键：

1. 增加 `userdata_v2`、`groupdata_v2`、`ejaculation_data_v2`，主键或外键使用 `encode_ref()` 结果。
2. 在单个迁移事务内把旧用户 ID 回填为 `UserRef(scope="QQClient", id=str(userid))`，旧群号回填为 `SceneRef(scope="QQClient", type="group", id=str(groupid))`。
3. 校验旧表与 v2 表记录数、关键字段和注入总量一致后切换读取。
4. 首个版本保留 legacy 表作为恢复来源，不立即删除；重复启动时迁移必须幂等。
5. `DataManager` API 接收 `UserRef`/`SceneRef`，在 infra 内编码，不让 wire string 扩散到 core。
6. `GameApplication` 接收 Ref 或更窄的稳定身份对象；core 的纯数值规则不感知身份。
7. 冷却键改为 `encode_ref(user_ref)`；群开关以场景 Ref 为键。
8. 只有需要事件外发送时才调用 `to_target()`，不把 Target 持久化进业务表。

### 预期提交

1. `feat: 引入UniRef持久化身份依赖`
2. `refactor: 扩展DataManager身份参数`
3. `feat: 迁移旧版身份数据表`
4. `test: 验证UniRef数据迁移`
5. `refactor: 使用Ref统一冷却与场景键`
6. `test: 验证跨平台身份隔离`
7. `docs: 记录持久化身份协议`

测试仍遵循用户确认的顺序：先完成对应迁移切片，再立即增加该切片的迁移和行为测试。

## 待确认事项

### D-101 · P0：UniRef 在何时进入当前插件

- **A：不采用。** Alconna 迁移仍保持 OneBot 整数身份。
- **B：Alconna 完成后单独采用。** 先稳定接入层，再执行数据迁移。
- **C：与 Alconna 首轮同时采用。** 同时修改 matcher、身份和 schema，风险最高。
- **建议：B。** UniRef 有明确长期价值，但与 matcher 是独立边界；分开实施更容易定位回归和恢复数据。

### D-102 · P0：既有数据库如何升级

- **A：建立 v2 表、事务回填、校验后切换，并暂时保留 legacy 表。**
- **B：给旧表增加 ref 列，但继续保留整数主键。** 无法真正解决跨平台同值碰撞，只适合作为短暂过渡。
- **C：放弃旧数据并创建新数据库。** 与当前沿用旧数据库承诺冲突。
- **建议：A。** 它是唯一同时满足跨平台唯一性、可验证和可恢复的方向。

### D-103 · P1：是否按 Bot 隔离用户状态

UniRef 的 Ref 默认不含 Bot，同一平台的两个 Bot 会看到相同用户 Ref。

- **A：同平台 Bot 共享状态。** 与当前 QQ 用户按裸账号共享状态的语义一致。
- **B：按 Bot 隔离。** 业务键额外加入 `self_id`，但 Ref 本身保持不变。
- **建议：A。** 保持现有语义；只有明确需要多 Bot 独立游戏世界时再增加 Bot 维度。

### D-104 · P1：遇到 UniRef 未验证来源如何处理

- **A：显式拒绝该命令并提示平台暂未支持。**
- **B：回退到裸 ID。** 会破坏持久化唯一性保证。
- **建议：A。** 持久化身份应失败安全，不生成之后难以迁移的键。

## 完成标准与验证

| 覆盖条件或输入 | 预期结果 | 验证方式 |
|---|---|---|
| 旧 OneBot 数据库 | 所有用户、群开关、注入记录无损进入 v2 表 | 真实结构 fixture、记录数与字段逐项比对 |
| 重复启动迁移 | 不重复、不覆盖新数据、不改变总量 | 幂等迁移测试 |
| 同值用户 ID、不同 scope | 生成不同主键且互不读取 | DataManager 集成测试 |
| 两个 OneBot Bot 观察同一 QQ 用户 | 按 D-103 得到相同或隔离状态 | 身份键参数化测试 |
| 未验证 Adapter/scope | 按 D-104 显式失败，不写入数据库 | 依赖与数据层测试 |
| Telegram topic | 保持 UniRef 明确拒绝，不生成碰撞 SceneRef | 错误路径测试 |
| 冷却和群开关 | 使用 Ref 后不发生跨平台碰撞 | 应用层与冷却测试 |
| 数据恢复 | legacy 表仍可用于核对和人工恢复 | 迁移后 schema 检查与恢复说明 |
| 质量门 | Ruff、BasedPyright、pytest、构建全部通过 | 项目标准命令 |

## 相关文档

- [当前项目架构](../../architecture/overview.md)
- [UniRef 仓库 main@ec2ee8f](https://github.com/Misty02600/nonebot-plugin-uniref/tree/ec2ee8f0b070c20293cd57ac5459a87d43afc50b)
- [UniRef v0.2.0](https://github.com/Misty02600/nonebot-plugin-uniref/releases/tag/v0.2.0)
- [PLAN-0001：迁移 Alconna 跨平台接入层](PLAN-0001-alconna-multiplatform-migration.md)
