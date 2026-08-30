# PLAN-0001：迁移 Alconna 跨平台接入层

| 状态 | 优先级 | 最后更新 | 基准 |
|---|---|---|---|
| 讨论中 | 阻塞 | 2026-08-30 | `feature@7139724` |

## 背景

当前插件已经把 NoneBot 接入、应用编排、核心规则和基础设施分开，Alconna 迁移可以主要限制在 `src/nonebot_plugin_impart_plus/bot/`。用户明确要求先完成迁移、再为迁移后的行为补测试，但实施前必须先确认平台范围、命令兼容和平台能力降级，避免在重写 matcher 时临时决定产品语义。

本计划只处理接入层：命令解析使用 Alconna，当前事件身份与场景使用 Uninfo，消息渲染使用 UniMessage。游戏规则、随机算法、冷却顺序、数据库提交方式和现有文案不在本计划中调整。

## 当前设计与风险

### 现有接入

- [`bot/__init__.py`](../../../src/nonebot_plugin_impart_plus/bot/__init__.py) 注册 9 个 matcher，混用 `on_command` 与 `on_regex`。
- [`bot/handlers.py`](../../../src/nonebot_plugin_impart_plus/bot/handlers.py) 直接依赖 OneBot V11 的 `GroupMessageEvent`、`MessageSegment`、群成员列表、群成员资料、sender card 和 QQ 头像地址。
- PK、嗦、查询和注入查询通过扫描 OneBot `at` 消息段得到目标；`@全体` 被视为没有合法目标。
- 群开关权限直接使用 OneBot V11 `GROUP_ADMIN`、`GROUP_OWNER` 与 NoneBot `SUPERUSER`。
- `.env.test` 的 `COMMAND_START` 是 `["", "/"]`。`on_command` 入口遵循 command start，而现有正则入口直接从消息开头匹配；把所有命令统一改成 `use_cmd_start=True` 会改变部分部署中的无前缀行为。
- 现有仓库测试只有插件加载、配置默认值和测试事件构造 3 项，没有 matcher 行为基线。按用户要求，测试在每个命令切片迁移完成后补充。

### 精确依赖基线

已用隔离环境核对以下发布版本：

| 包 | 版本 | 已验证接口或约束 |
|---|---|---|
| `nonebot-plugin-alconna` | `0.62.1` | `on_alconna`、`Alconna`、`Args`、`Match`、`Query`、`UniMessage`、`At`、`Image`；要求 NoneBot ≥2.5.0 |
| `nonebot-plugin-uninfo` | `0.11.1` | `Uninfo`、`Interface`、`get_session`、`get_interface`；要求 NoneBot ≥2.5.0 |
| `nonebot-plugin-uniref` | `0.2.0` | 本计划不强制采用；独立评估见 PLAN-0002 |

Alconna 0.62.1 的 `on_alconna` 已确认包含 `skip_for_unmatch`、`auto_send_output`、`aliases`、`use_cmd_start`、`use_cmd_sep`、`permission`、`handlers`、`priority` 和 `block`。迁移时必须显式设置会影响旧行为的参数，不依赖全局默认值。

### 跨平台能力边界

Uninfo 0.11.1 能为 OneBot V11 和 Discord 枚举成员；Telegram fetcher 没有 `query_members`，因此当前“随机群友”无法在 Telegram 保持原行为。Discord 可以枚举成员，但“群主/管理”与 OneBot 的 owner/admin 角色并非同一模型，需要单独验证角色映射。

这意味着“命令能够被多个 Adapter 解析”不等于“全部玩法已经跨平台”。在能力未验证前，插件元数据不能扩大 `supported_adapters`。

## 技术路线

### 目标边界

```text
Adapter event
  → on_alconna / Match[At]
  → Uninfo Session
  → 普通 actor_id / scene_id / target_id
  → impart.app
  → Outcome
  → UniMessage
```

- `bot` 持有 Alconna、Uninfo、UniMessage 和狭窄的平台降级 helper。
- `impart/app.py`、`impart/core.py` 和 `infra` 不接收 `Event`、`Session`、`UniMessage` 或 Alconna 解析对象。
- 当前事件回复不构造 `Target`；只有未来出现事件外主动发送时才使用。
- 第一轮不改变 SQLite 主键类型；UniRef 及数据迁移由 PLAN-0002 单独决定。
- 第一轮不修改玩法、提示语、随机调用次序、冷却时机和数据提交边界。

### 迁移与测试顺序

遵循“先迁移、后测试”，但每个切片迁移后立即补对应测试，不等全部命令完成后才验证。

1. `feat: 引入跨平台接入依赖`
   - 将 NoneBot 下限提升到 `2.5.0`。
   - 添加 Alconna `0.62.1` 与 Uninfo `0.11.1` 兼容范围。
   - 在入口 `require()` 两个插件；暂不扩大 `supported_adapters`。
   - 建立 `bot` 内的 session、mention、renderer helper，不迁命令。
2. `refactor: 迁移帮助与群开关命令`
   - 迁移固定文本和简单权限命令。
   - 保留现有 command start、priority、block 和权限语义。
3. `test: 验证帮助与群开关命令`
   - 验证无前缀和 `/` 前缀、管理员/群主/超级用户、普通成员拒绝、固定回复。
4. `refactor: 迁移成长与状态查询命令`
   - 迁移打胶、查询；actor/scene 来自 Uninfo。
   - Outcome 仍由现有 application 产生。
5. `test: 验证成长与状态查询命令`
   - 覆盖群未开启、创建用户、冷却、正常成长、挑战阻止和长度状态文案。
6. `refactor: 迁移目标参数命令`
   - 用 `Match[At]` 迁移嗦、PK、注入查询。
   - 明确无 `At`、`AtAll`、自己、目标不存在和额外文本的处理。
7. `test: 验证目标参数命令`
   - 覆盖默认本人、显式目标、`@全体`、PK 必须有目标、别名与参数失败输出。
8. `refactor: 迁移排行榜与群友互动命令`
   - 排行榜昵称查询和群成员选择通过狭窄 MemberDirectory helper。
   - OneBot 行为先保持；其他平台按已确认的能力策略显式支持或拒绝。
9. `test: 验证排行榜与群友互动命令`
   - 覆盖成员列表、owner/admin 选择、找不到目标、反透、图片输出和 Adapter 降级。
10. `refactor: 使用UniMessage统一回复`
    - 将文本、at sender 与 PNG bytes 转换为 UniMessage/uniseg segment。
    - 明确 fallback；移除 OneBot `MessageSegment` 后再评估 metadata。
11. `test: 验证跨平台消息渲染`
    - 测试 UniMessage segment 结构；保留 OneBot 行为测试，并为已声明支持的 Adapter 增加最小渲染测试。
12. `docs: 更新命令与适配器边界`
    - 同步 README、PluginMetadata、architecture 和平台支持矩阵。

### 命令迁移映射

| 当前入口 | Alconna 目标 | 必须保留或确认的语义 |
|---|---|---|
| `pk/对决` | `Alconna("pk", Args["target", At])` + alias | 目标必填、不能自己、`block=False` 是否继续保留 |
| `打胶/开导` | 一个命令加 alias | 原正则要求完整消息，command start 行为待确认 |
| `嗦牛子/嗦/suo` | 可选 `At` | 无目标默认本人、`AtAll` 不作为用户 |
| `查询` | 可选 `At` | 无目标默认本人 |
| 排行榜别名 | 一个命令加 aliases | 原正则接受前缀后额外文本是否属于契约待确认 |
| 日/透系列 | 命令或子命令映射 | 群友、群主、管理的身份分支与成员能力待确认 |
| 开始/开启/关闭/禁止 | 命令或选项映射 | OneBot owner/admin/superuser 权限迁为 Uninfo 权限 |
| 注入查询系列 | 可选 `At` 与历史选项 | “历史/全部”的位置与额外文本兼容待确认 |
| 银趴/impart 帮助 | 一个命令加 aliases | 完整 metadata usage 输出 |

## 待确认事项

### D-001 · P0：首轮声明支持哪些 Adapter

- **A：首轮仅声明 OneBot V11。** 接入代码使用 Alconna、Uninfo 和 UniMessage，但数据库继续使用现有整数身份；完成 PLAN-0002 后再扩大平台声明。
- **B：立即让通用命令支持 OneBot V11、Telegram、Discord。** 在 PLAN-0002 完成前会让不同 scope 的同值整数 ID 发生碰撞，不能安全实施。
- **C：全部玩法同时支持三平台。** 除身份碰撞外，Telegram 还没有成员枚举，必须先重新设计群友互动。
- **建议：A。** 它保持 Alconna 与身份 schema 两个计划可独立实施和回退，同时让 bot 层先形成跨平台边界。

### D-002 · P0：Telegram 的群友互动如何降级

- **A：禁用群友、群主、管理三类互动命令并返回明确提示。**
- **B：群友命令要求显式 `At`，群主/管理命令禁用。**
- **C：本轮不声明 Telegram 支持。**
- **建议：B。** 保留可由 mention 明确表达的玩法，不伪造成员枚举和角色能力。

### D-003 · P1：命令触发语义是严格兼容还是规范化

- **A：严格兼容。** 原 `on_command` 保留 command start；原正则入口保留无前缀触发及现有尾随文本范围。
- **B：统一规范。** 所有用户命令使用 `use_cmd_start=True`，只接受 Alconna grammar 声明的参数。
- **建议：A。** 首轮迁移不应同时收紧用户输入；规范化可以在测试明确现状后单独讨论。

### D-004 · P1：UniMessage 无法导出 segment 时的 fallback

- **A：`auto`，尽量降级为可发送表现。**
- **B：`forbid`，不支持就显式失败。**
- **建议：A。** 当前主要输出是文本、At 和 PNG，通用表示明确；自动降级更接近现有“尽量回复”的行为。

## 已确认事项

- 2026-08-30：迁移实现先于对应测试，但每个命令切片迁移后立即补测试。
- 2026-08-30：Alconna 迁移不得顺带修改游戏规则、数据库提交顺序、冷却时机或文案。
- 2026-08-30：UniRef 持久化身份不与 matcher 迁移强行绑定，作为独立计划评估。

## 完成标准与验证

| 覆盖条件或输入 | 预期结果 | 验证方式 |
|---|---|---|
| 插件加载 | Alconna、Uninfo 和所有 matcher 正常注册，无重复命令 | 插件加载测试、matcher 数量与命令解析自检 |
| 当前全部命令及别名 | 迁移后的命令触发范围符合 D-003 | Alconna matcher parser test + NoneBug 行为测试 |
| `At`、无目标、`AtAll`、自己 | 每个命令维持既定目标语义 | 参数化行为测试 |
| 群未开启、冷却、用户创建、挑战状态 | application 的调用与回复未改变 | NoneBug + fake DataManager/Cooldown |
| 管理权限 | OneBot 现有 owner/admin/superuser 行为保持；新平台按 D-001/D-002 | 各 Adapter 权限 fixture 或明确的未覆盖说明 |
| 文本、at sender、PNG | UniMessage 可导出并发送；fallback 符合 D-004 | segment 单测与 OneBot 行为测试 |
| 适配器声明 | metadata 只包含已经有行为证据的平台 | metadata 测试与平台支持矩阵审查 |
| 质量门 | Ruff、BasedPyright、pytest、sdist/wheel 构建全部通过 | `just lint`、`just check`、`just test`、`uv build` |

## 相关文档

- [当前项目架构](../../architecture/overview.md)
- [NoneBot Alconna 插件文档](https://nonebot.dev/docs/2.4.4/best-practice/alconna/)
- [nonebot-plugin-alconna v0.62.1](https://github.com/nonebot/plugin-alconna/releases/tag/v0.62.1)
- [PLAN-0002：评估并采用 UniRef 持久化身份](PLAN-0002-uniref-persistent-identity.md)
