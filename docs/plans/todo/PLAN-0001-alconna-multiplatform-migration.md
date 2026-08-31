# PLAN-0001：迁移 Alconna 跨平台接入层

| 状态 | 优先级 | 最后更新 | 基准 |
|---|---|---|---|
| 讨论中 | 阻塞 | 2026-08-31 | `feature@bdd531e` |

## 背景

当前插件已经把 NoneBot 接入、应用编排、核心规则和基础设施分开，Alconna 迁移可以主要限制在 `src/nonebot_plugin_impart_plus/bot/`。用户明确要求先完成迁移、再为迁移后的行为补测试；命令兼容和缺少成员枚举时的显式 At 行为已经确认，实施前仍需确认首轮平台范围和 UniMessage fallback，避免在重写 matcher 时临时决定产品语义。

本计划只处理接入层：命令解析使用 Alconna，当前事件身份与场景使用 Uninfo，消息渲染使用 UniMessage。游戏规则、随机算法、冷却顺序、数据库提交方式和现有文案不在本计划中调整。

## 当前设计与风险

### 现有接入

- [`bot/__init__.py`](../../../src/nonebot_plugin_impart_plus/bot/__init__.py) 注册 9 个 matcher，混用 `on_command` 与 `on_regex`。
- [`bot/handlers.py`](../../../src/nonebot_plugin_impart_plus/bot/handlers.py) 直接依赖 OneBot V11 的 `GroupMessageEvent`、`MessageSegment`、群成员列表、群成员资料、sender card 和 QQ 头像地址。
- PK、嗦、查询和注入查询通过扫描 OneBot `at` 消息段得到目标；`@全体` 被视为没有合法目标。
- 群开关权限直接使用 OneBot V11 `GROUP_ADMIN`、`GROUP_OWNER` 与 NoneBot `SUPERUSER`。
- `.env.test` 的 `COMMAND_START` 是 `["", "/"]`。`on_command` 入口遵循 command start，而现有正则入口直接从消息开头匹配；把所有命令统一改成 `use_cmd_start=True` 会改变部分部署中的无前缀行为。
- `打胶/开导` 与帮助正则要求完整消息；排行榜、互动和群开关正则只约束消息开头，并使用 `re.I`，因此会接受大小写变体和尾随内容。
- `pk/对决` 通过额外 rule 要求消息中存在非 `@全体` 的 At；嗦、查询、注入查询和互动处理器扫描整条消息取得第一个 At。常规 `Args["target?", At]` 只表达“参数可省略”，不表达“At 可位于剩余消息任意位置”。
- 现有仓库测试只有插件加载、配置默认值和测试事件构造 3 项，没有 matcher 行为基线。按用户要求，测试在每个命令切片迁移完成后补充。

### 精确依赖基线

已用隔离环境核对以下发布版本：

| 包 | 版本 | 已验证接口或约束 |
|---|---|---|
| `nonebot-plugin-alconna` | `0.62.1` | `on_alconna`、`Alconna`、`Args`、`Match`、`Query`、`UniMessage`、`At`、`Image`；要求 NoneBot ≥2.5.0 |
| `nonebot-plugin-uninfo` | `0.11.1` | `Uninfo`、`Interface`、`get_session`、`get_interface`；要求 NoneBot ≥2.5.0 |
| `nonebot-plugin-uniref` | `0.2.0` | 本计划不强制采用；独立评估见 PLAN-0002 |

Alconna 0.62.1 的 `on_alconna` 已确认包含 `skip_for_unmatch`、`auto_send_output`、`aliases`、`use_cmd_start`、`use_cmd_sep`、`permission`、`handlers`、`priority` 和 `block`。隔离解析验证还确认：

- `use_cmd_start=True` 会把 NoneBot `COMMAND_START` 同时应用到主命令和 `aliases`。
- 官方 `re:...` 命令头可以表达旧正则的大小写不敏感匹配；`CommandMeta(compact=True)` 可以把紧随命令头的内容继续交给参数解析。
- `Args["target?", At]["tail?", AllParam]` 会优先得到类型化 At，并把其余文本或消息段保存在 `tail: UniMessage`；At 前存在文本时，At 也会保留在 tail 中。

迁移时必须显式设置会影响旧行为的参数，不依赖全局默认值。

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
- 第一轮不改变 SQLite 主键类型；UniRef 及持久化身份重构由 PLAN-0002 单独决定。插件发布到 NoneBot 插件市场前，数据库始终按全新 v1 处理，不编写迁移兼容代码。
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
   - 两者原本都是无前缀正则，使用 `use_cmd_start=False`；保留 priority、block、大小写不敏感和权限语义。
3. `test: 验证帮助与群开关命令`
   - 验证无前缀可用、`/` 前缀不匹配、管理员/群主/超级用户、普通成员拒绝、固定回复和旧尾随范围。
4. `refactor: 迁移成长与状态查询命令`
   - 迁移打胶、查询；actor/scene 来自 Uninfo。
   - 打胶保留无前缀完整匹配；查询遵循原生 command start。
   - Outcome 仍由现有 application 产生。
5. `test: 验证成长与状态查询命令`
   - 覆盖群未开启、创建用户、冷却、正常成长、挑战阻止和长度状态文案。
6. `refactor: 迁移目标参数命令`
   - 用 `Match[At]` 作为嗦、PK、查询和注入查询的主要目标参数；PK 在业务语义上仍要求目标，其余命令保持目标可选。
   - 仅在类型化参数未取得目标时，从 Alconna 已解析出的可选 `tail: UniMessage` 恢复旧版“附加文本中含 At”行为；不重新扫描原始 Adapter 消息。
   - 明确无 `At`、`AtAll`、自己、目标不存在和额外文本的处理。
7. `test: 验证目标参数命令`
   - 覆盖默认本人、显式目标、`@全体`、PK 必须有目标、别名与参数失败输出。
8. `refactor: 迁移排行榜与群友互动命令`
   - 排行榜昵称查询和群成员选择通过狭窄 MemberDirectory helper。
   - OneBot 行为先保持；缺少成员枚举的平台有显式 At 时直接使用该目标，不因“群友/群主/管理”标签禁用命令；无显式 At 时返回能力不足提示。
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
| `pk/对决` | `use_cmd_start=True`；类型化 At + 可选 tail | 目标在业务上必填、不能自己、兼容 At 前后尾随内容、保留 `block=False` |
| `打胶/开导` | 无前缀命令加 alias | `use_cmd_start=False`，保持完整消息匹配 |
| `嗦牛子/嗦/suo` | `use_cmd_start=True`；可选 `At` + 可选 tail | 无目标默认本人、`AtAll` 不作为用户、兼容旧尾随内容 |
| `查询` | `use_cmd_start=True`；可选 `At` + 可选 tail | 无目标默认本人、兼容旧尾随内容 |
| 排行榜别名 | `re:(?i:...)` 命令头 + compact tail | 无前缀、大小写不敏感，继续接受旧正则允许的尾随内容 |
| 日/透系列 | `re:(?i:...)` 命令头 + 可选 `At`/tail | 显式 At 优先；无 At 才按群友、群主、管理自动选择 |
| 开始/开启/关闭/禁止 | `re:(?i:...)` 命令头 + compact tail | 无前缀、大小写不敏感；OneBot owner/admin/superuser 权限迁为跨平台权限 helper |
| 注入查询系列 | `use_cmd_start=True`；可选 `At` + payload | 保留“历史/全部”子串判断和额外文本范围 |
| 银趴/impart 帮助 | `re:(?i:...)` 精确命令头 | 无前缀完整匹配，输出完整 metadata usage |

## 待确认事项

### D-001 · P0：首轮声明支持哪些 Adapter

- **A：首轮仅声明 OneBot V11。** 接入代码使用 Alconna、Uninfo 和 UniMessage，但数据库继续使用现有整数身份；完成 PLAN-0002 后再扩大平台声明。
- **B：立即让通用命令支持 OneBot V11、Telegram、Discord。** 在 PLAN-0002 完成前会让不同 scope 的同值整数 ID 发生碰撞，不能安全实施。
- **C：全部玩法同时支持三平台。** 除身份碰撞外，Telegram 还没有成员枚举，必须先重新设计群友互动。
- **建议：A。** 它保持 Alconna 与身份 schema 两个计划可独立实施和回退，同时让 bot 层先形成跨平台边界。

### D-004 · P1：UniMessage 无法导出 segment 时的 fallback

- **A：`auto`，尽量降级为可发送表现。**
- **B：`forbid`，不支持就显式失败。**
- **建议：A。** 当前主要输出是文本、At 和 PNG，通用表示明确；自动降级更接近现有“尽量回复”的行为。

## 已确认事项

- 2026-08-30：迁移实现先于对应测试，但每个命令切片迁移后立即补测试。
- 2026-08-30：Alconna 迁移不得顺带修改游戏规则、数据库提交顺序、冷却时机或文案。
- 2026-08-30：UniRef 持久化身份不与 matcher 迁移强行绑定，作为独立计划评估。
- 2026-08-31 · D-002：缺少成员枚举时不显式禁用互动命令；存在显式 At 就忽略“群友/群主/管理”的自动选择含义并直接使用该目标，无 At 时才返回平台能力不足提示。
- 2026-08-31 · D-003：严格保留 command start、无前缀正则、大小写不敏感和尾随内容范围；目标优先使用类型化 `At`，仅从 Alconna 的可选 tail 恢复旧 At 位置，不扫描原始 Adapter 消息。

## 完成标准与验证

| 覆盖条件或输入 | 预期结果 | 验证方式 |
|---|---|---|
| 插件加载 | Alconna、Uninfo 和所有 matcher 正常注册，无重复命令 | 插件加载测试、matcher 数量与命令解析自检 |
| 原 `on_command` 命令及别名 | 读取 `COMMAND_START`；主命令和 alias 的无前缀、`/` 前缀行为与当前配置一致 | Alconna parser test + NoneBug 行为测试 |
| 原完整匹配正则 | 仅无前缀完整消息匹配，`/` 前缀和尾随内容不触发 | Alconna parser 参数化测试 |
| 原前缀匹配正则 | 无前缀、大小写不敏感并接受原有尾随范围 | Alconna parser 参数化测试 |
| `At`、At 前后文本、无目标、`AtAll`、自己 | 类型化 At 优先，兼容 tail 内首个用户 At；每个命令维持既定目标语义 | 参数化 parser 与行为测试 |
| 群未开启、冷却、用户创建、挑战状态 | application 的调用与回复未改变 | NoneBug + fake DataManager/Cooldown |
| 管理权限 | OneBot 现有 owner/admin/superuser 行为保持；新平台按 D-001 与已确认的显式 At 降级策略 | 各 Adapter 权限 fixture 或明确的未覆盖说明 |
| 无成员枚举平台的互动命令 | 显式 At 可用且覆盖群友/群主/管理自动选择；无 At 返回能力不足提示 | MemberDirectory capability fake + 行为测试 |
| 文本、at sender、PNG | UniMessage 可导出并发送；fallback 符合 D-004 | segment 单测与 OneBot 行为测试 |
| 适配器声明 | metadata 只包含已经有行为证据的平台 | metadata 测试与平台支持矩阵审查 |
| 质量门 | Ruff、BasedPyright、pytest、sdist/wheel 构建全部通过 | `just lint`、`just check`、`just test`、`uv build` |

## 相关文档

- [当前项目架构](../../architecture/overview.md)
- [NoneBot Alconna 插件文档](https://nonebot.dev/docs/2.4.4/best-practice/alconna/)
- [nonebot-plugin-alconna v0.62.1](https://github.com/nonebot/plugin-alconna/releases/tag/v0.62.1)
- [PLAN-0002：评估并采用 UniRef 持久化身份](PLAN-0002-uniref-persistent-identity.md)
