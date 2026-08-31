# PLAN-0001：迁移 Alconna 跨平台接入层

| 状态 | 优先级 | 最后更新 | 基准 |
|---|---|---|---|
| 进行中 | 阻塞 | 2026-08-31 | `feature@6d02776` |

## 背景

当前插件已经把 NoneBot 接入、应用编排、核心规则和基础设施分开，Alconna 迁移可以主要限制在 `src/nonebot_plugin_impart_plus/bot/`。用户明确要求先完成迁移、再为迁移后的行为补测试，并利用 Alconna 根命令、子命令、alias、typed Args 和 compact 语法重新整理命令；不保留旧松散 grammar 的兼容层。

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
| `nonebot-plugin-uniref` | `0.2.0` | 在扩大 Adapter 声明前用于持久化身份；实施见 PLAN-0002 |

Alconna 0.62.1 的 `on_alconna` 已确认包含 `skip_for_unmatch`、`auto_send_output`、`aliases`、`use_cmd_start`、`use_cmd_sep`、`permission`、`handlers`、`priority` 和 `block`。隔离解析验证还确认：

- `use_cmd_start=True` 会把 NoneBot `COMMAND_START` 同时应用到主命令和 `aliases`。
- 官方 `re:...` 命令头可以表达旧正则的大小写不敏感匹配；`CommandMeta(compact=True)` 可以把紧随命令头的内容继续交给参数解析。
- `Args["target", At]` 可以在 parser 层保证 PK 目标必填；可选目标使用 `Args["target?", At]`，不再扫描未声明的尾随消息。

迁移时必须显式设置会影响旧行为的参数，不依赖全局默认值。

NoneBot 2.5.0 的 `inherit_supported_adapters(*names)` 会展开 `~` 缩写并返回已加载依赖插件支持集合的交集；依赖未先 `require()` 时会抛出 `RuntimeError`。对上述锁定版本实测三插件交集为 OneBot V11、Telegram 和 Discord，但实现不硬编码该结果。

### 跨平台能力边界

Uninfo 0.11.1 能为 OneBot V11 和 Discord 枚举成员；Telegram fetcher 没有 `query_members`，因此当前“随机群友”无法在 Telegram 保持原行为。Discord 可以枚举成员，但“群主/管理”与 OneBot 的 owner/admin 角色并非同一模型，需要单独验证角色映射。

这意味着“命令能够被多个 Adapter 解析”不等于“全部玩法已经跨平台”。最终 `supported_adapters` 直接继承 Alconna、Uninfo、UniRef 三个插件的动态交集；本插件仍需为该交集中的 Adapter 验证自身命令、身份和能力降级，依赖升级后也必须重新运行支持矩阵测试。

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
- Alconna matcher 切片本身不改变 SQLite 主键类型；完成这些切片后按 PLAN-0002 使用 UniRef 重构 v1 身份 schema，完成身份隔离后才把 metadata 改为三插件支持交集。
- PLAN-0002 将消费 UniRef 上游提供的事件依赖注入契约：无法形成已验证 Ref 的事件静默跳过，不回复、不写库；对 `block=True` matcher 必须在运行 handler 前完成身份能力判断，避免跳过 handler 后仍阻止低优先级 matcher。
- 插件发布到 NoneBot 插件市场前，数据库始终按全新 v1 处理，不编写迁移兼容代码。
- 第一轮不修改玩法、提示语、随机调用次序、冷却时机和数据提交边界。

### 迁移与测试顺序

遵循“先迁移、后测试”，但每个切片迁移后立即补对应测试，不等全部命令完成后才验证。

1. `feat: 引入跨平台接入依赖`
   - 将 NoneBot 下限提升到 `2.5.0`。
   - 添加 Alconna `0.62.1` 与 Uninfo `0.11.1` 兼容范围。
   - 在入口 `require()` 两个插件；matcher 迁移期间暂不扩大 `supported_adapters`。
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
   - PK 使用必填 `At`；嗦、查询和注入查询使用可选 `At`，不接收未声明的尾随消息。
   - 注入查询把“历史/全部”建模为正式 Alconna Option。
   - 明确无 `At`、`AtAll`、自己、目标不存在和参数解析失败的处理。
7. `test: 验证目标参数命令`
   - 覆盖默认本人、显式目标、`@全体`、PK 必须有目标、历史选项、别名与参数失败输出。
8. `refactor: 迁移排行榜与群友互动命令`
   - 排行榜昵称查询和群成员选择通过狭窄 MemberDirectory helper。
   - OneBot 行为先保持；缺少成员枚举的平台有显式 At 时直接使用该目标，不因“群友/群主/管理”标签禁用命令；无显式 At 时返回能力不足提示。
9. `test: 验证排行榜与群友互动命令`
   - 覆盖成员列表、owner/admin 选择、找不到目标、反透、图片输出和 Adapter 降级。
10. `refactor: 使用UniMessage统一回复`
    - 将文本、at sender 与 PNG bytes 转换为 UniMessage/uniseg segment。
    - 所有发送使用 `fallback="auto"`；移除 OneBot `MessageSegment` 后再进入身份与 metadata gate。
11. `test: 验证跨平台消息渲染`
    - 测试 UniMessage segment 结构；保留 OneBot 行为测试，并为当前三插件交集中的 Adapter 增加最小渲染测试。
12. `refactor: 优化银趴与互动命令结构`
    - `银趴` 作为根命令，开启、禁止、帮助作为子命令；使用 dispatch 保持开关权限与帮助公开访问相互独立。
    - `透` 作为互动根命令、`日` 作为 alias，群友、管理、群主使用类型化 Literal 参数。
    - 根命令使用 compact，同时接受有空格和无空格形式；不注册旧版动作前置 shortcut。
13. `test: 验证分组命令语法`
    - 覆盖根命令 alias、子命令 alias、dispatch path、权限边界、有/无空格，并验证旧格式不再匹配。
14. `feat: 声明三插件适配器交集`
    - PLAN-0002 完成后，在插件入口依次 `require("nonebot_plugin_alconna")`、`require("nonebot_plugin_uninfo")`、`require("nonebot_plugin_uniref")`。
    - 把 `PluginMetadata.supported_adapters` 设置为 `inherit_supported_adapters("nonebot_plugin_alconna", "nonebot_plugin_uninfo", "nonebot_plugin_uniref")`。
    - 不手写 Adapter 集合。
15. `test: 验证适配器支持交集`
    - 在测试依赖组加入当前交集对应的 OneBot V11、Telegram、Discord Adapter；交集随依赖升级变化时，同步测试依赖和 fixture。
    - 验证依赖加载顺序、动态交集、锁定版本的支持矩阵，以及交集内各 Adapter 的最小命令与消息行为。
16. `docs: 更新命令与适配器边界`
    - 同步 README、architecture 和平台支持矩阵。

### 命令迁移映射

| 当前入口 | Alconna 目标 | 必须保留或确认的语义 |
|---|---|---|
| `pk/对决` | `use_cmd_start=True`；必填 `At` | parser 保证目标必填；不能自己；保留 `block=False` |
| `打胶/开导` | 无前缀命令加 alias | `use_cmd_start=False`，保持完整消息匹配 |
| `嗦牛子/嗦/suo` | `use_cmd_start=True`；可选 `At` | 无目标默认本人，`AtAll` 与额外参数不匹配 |
| `查询` | `use_cmd_start=True`；可选 `At` | 无目标默认本人，不接收额外参数 |
| 排行榜别名 | `re:(?i:...)` 精确命令头 | 无前缀、大小写不敏感，不接收尾随内容 |
| 日/透系列 | `透` 根命令 + `日` alias + `Literal["群友", "管理", "群主"]` | compact 支持 `透群友`/`透 群友`；显式 At 优先；不再接受任意黏连尾巴 |
| 银趴开关与帮助 | `银趴` 根命令 + 开启/禁止/帮助子命令 | compact 支持有/无空格，dispatch 分离管理员权限，不兼容动作前置旧格式 |
| 注入查询系列 | `use_cmd_start=True`；可选 `At` + 历史 Option | “历史/全部”是正式选项，不再按任意文本子串判断 |

## 已确认事项

- 2026-08-30：迁移实现先于对应测试，但每个命令切片迁移后立即补测试。
- 2026-08-30：Alconna 迁移不得顺带修改游戏规则、数据库提交顺序、冷却时机或文案。
- 2026-08-30：UniRef 持久化身份不与 matcher 迁移强行绑定，在接入切片后作为独立计划实施。
- 2026-08-31 · D-002：缺少成员枚举时不显式禁用互动命令；存在显式 At 就忽略“群友/群主/管理”的自动选择含义并直接使用该目标，无 At 时才返回平台能力不足提示。
- 2026-08-31 · D-003：命令使用原生 command start、无前缀设置、alias、子命令、Option 与 typed Args 明确定义 grammar；不提供旧格式 shortcut、任意尾随文本或消息内 At 扫描兼容。
- 2026-08-31 · D-001：不把支持范围限制为 OneBot V11；完成 UniRef v1 身份重构后，使用 NoneBot `inherit_supported_adapters()` 直接继承 Alconna、Uninfo、UniRef 三插件支持集合的交集，不手写 Adapter 名单。
- 2026-08-31 · D-004：UniMessage 发送统一采用 `fallback="auto"`，尽量导出为当前 Adapter 可发送的表现。
- 2026-08-31：同平台多 Bot 共享同一用户和场景游戏状态；身份来源不受支持时静默跳过事件处理，不向用户发送拒绝文案。
- 2026-08-31：`银趴` 使用子命令，是因为开关与帮助有独立权限/处理路径；`透/日` 的群友、管理、群主使用 Literal 参数，因为它们共享同一互动用例与参数结构。

## 实施进度

| 状态 | 当前工作项 | 结果或下一步 |
|---|---|---|
| 进行中 | 优化银趴与互动命令结构 | 根命令、子命令、alias 与 compact 已实现，旧格式兼容层已删除，下一步补 dispatch 和严格语法测试 |

## 完成标准与验证

| 覆盖条件或输入 | 预期结果 | 验证方式 |
|---|---|---|
| 插件加载 | Alconna、Uninfo 和所有 matcher 正常注册，无重复命令 | 插件加载测试、matcher 数量与命令解析自检 |
| 使用 command start 的命令及别名 | 读取 `COMMAND_START`；主命令和 alias 的无前缀、`/` 前缀行为符合声明 | Alconna parser test + NoneBug 行为测试 |
| 无前缀命令 | 仅匹配结构化 grammar，`/` 前缀和未声明尾随内容不触发 | Alconna parser 参数化测试 |
| `At`、无目标、`AtAll`、自己 | PK 必填 At；可选 At 命令按声明默认本人；未声明消息段解析失败 | 参数化 parser 与行为测试 |
| 群未开启、冷却、用户创建、挑战状态 | application 的调用与回复未改变 | NoneBug + fake DataManager/Cooldown |
| 管理权限 | OneBot 现有 owner/admin/superuser 行为保持；新平台按 D-001 与已确认的显式 At 降级策略 | 各 Adapter 权限 fixture 或明确的未覆盖说明 |
| 无成员枚举平台的互动命令 | 显式 At 可用且覆盖群友/群主/管理自动选择；无 At 返回能力不足提示 | MemberDirectory capability fake + 行为测试 |
| 文本、at sender、PNG | UniMessage 可导出并发送；无法原样导出时使用 `auto` fallback | segment 单测与各支持 Adapter 行为测试 |
| 依赖加载顺序 | Alconna、Uninfo、UniRef 均在继承支持集合前完成 `require()` | 插件加载测试 |
| 适配器声明 | metadata 等于 `inherit_supported_adapters()` 对三插件计算出的交集，不存在手写名单 | metadata 测试与平台支持矩阵审查 |
| 无法形成已验证 Ref 的事件 | matcher 不回复、不写数据库，也不因 `block=True` 阻止低优先级 matcher | 身份能力 rule/after-rule 测试 + 低优先级 sentinel matcher |
| 质量门 | Ruff、BasedPyright、pytest、sdist/wheel 构建全部通过 | `just lint`、`just check`、`just test`、`uv build` |

## 相关文档

- [当前项目架构](../../architecture/overview.md)
- [NoneBot Alconna 插件文档](https://nonebot.dev/docs/2.4.4/best-practice/alconna/)
- [NoneBot `inherit_supported_adapters`](https://nonebot.dev/docs/2.4.3/api/plugin/load)
- [nonebot-plugin-alconna v0.62.1](https://github.com/nonebot/plugin-alconna/releases/tag/v0.62.1)
- [PLAN-0002：采用 UniRef 持久化身份](PLAN-0002-uniref-persistent-identity.md)
