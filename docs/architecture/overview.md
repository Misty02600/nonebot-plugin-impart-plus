# 项目架构

## 先建立一个印象

`nonebot_plugin_impart_plus` 是面向 NoneBot2 与 OneBot V11 群聊的互动游戏插件。群管理员先启用插件，群成员再通过命令创建和改变个人数值、进行同阵营 PK、记录互动数据并查询排行榜或历史图表。

插件把群开关、用户游戏状态和注入记录持久化到本地 SQLite；冷却时间只保存在进程内存中。当前公开边界是 NoneBot 命令和 `PluginConfig` 配置，不提供独立的 Python 业务 API 稳定性承诺。

## 核心能力与公开入口

| 核心能力或公开入口 | 对外含义与适用场景 | 关键状态或副作用 | 主要实现位置 |
|---|---|---|---|
| 群开关与帮助 | 管理员启用或停用群内玩法，成员查询命令说明 | 持久化群级 `allow` 状态 | [`control.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/control.py)、[`help.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/help.py) |
| 正值与负值成长 | `打胶/开导`、`开扣/挖矿`、`嗦/舔` 改变本人或目标数值 | 修改用户长度并评估挑战状态；不同命令共享对应冷却 | [`dajiao.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/dajiao.py)、[`kaikou.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/kaikou.py)、[`suo.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/suo.py)、[`tian.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/tian.py) |
| 同阵营 PK | `pk/对决` 通用于两个世界，`击剑` 和 `磨豆腐/磨` 分别限定正值和负值世界 | 同一事务更新双方长度、胜率与挑战状态 | [`pk.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/pk.py) |
| 群友互动 | `日/透` 供正值玩家使用，`榨` 供负值玩家使用；目标可以是群友、群主或管理 | 记录注入量，部分正值分支可能触发 xnn 雌堕 | [`yinpa.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/yinpa.py) |
| 查询与图表 | 查询个人状态、排行榜和注入历史 | 读取持久化数据；排行榜和历史通过 HTML/Jinja2 渲染图片 | [`query.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/query.py)、[`rank.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/rank.py)、[`injection.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/injection.py) |
| `PluginConfig` | 从 NoneBot 配置读取帮助文案、冷却、PK 系数、别名和不活跃惩罚开关 | 进程启动时建立服务实例，运行中不热重载 | [`config.py`](../../src/nonebot_plugin_impart_plus/config.py)、[`dependencies.py`](../../src/nonebot_plugin_impart_plus/bot/dependencies.py) |

世界、挑战和 PK 的稳定状态语义见[核心游戏状态流](flows/gameplay.md)。

## 逻辑组件与实现映射

| 逻辑组件 | 职责与边界 | 依赖方向或主要协作 | 拥有的数据或状态 | 主要实现位置 |
|---|---|---|---|---|
| NoneBot 集成 | 注册 matcher、解析事件和目标、执行权限与世界 guard、组织回复 | 调用领域规则与基础设施，不直接维护数据库会话 | 单次事件的请求者、目标和 PK 上下文 | [`bot/`](../../src/nonebot_plugin_impart_plus/bot) |
| 领域规则 | 定义世界语义、挑战状态机、随机增量和 PK 计算 | `bot` 与 `infra` 调用；除 ORM 模型外不依赖 NoneBot | 纯计算结果，不持有运行状态 | [`core/world.py`](../../src/nonebot_plugin_impart_plus/core/world.py)、[`core/game.py`](../../src/nonebot_plugin_impart_plus/core/game.py)、[`core/rules.py`](../../src/nonebot_plugin_impart_plus/core/rules.py) |
| 持久化服务 | 初始化 SQLite、封装 CRUD 和事务、兼容旧数据库列 | 使用 SQLAlchemy async 与领域状态评估 | 用户、群开关和注入记录 | [`infra/database.py`](../../src/nonebot_plugin_impart_plus/infra/database.py)、[`infra/data_manager.py`](../../src/nonebot_plugin_impart_plus/infra/data_manager.py)、[`core/models.py`](../../src/nonebot_plugin_impart_plus/core/models.py) |
| 运行时服务 | 维护命令冷却、调度不活跃惩罚、渲染图表 | 由 NoneBot 依赖注入提供给 handler | 进程内冷却字典；临时 HTML 与浏览器页面 | [`infra/cooldown.py`](../../src/nonebot_plugin_impart_plus/infra/cooldown.py)、[`infra/chart_renderer.py`](../../src/nonebot_plugin_impart_plus/infra/chart_renderer.py)、[`scheduled.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/scheduled.py) |

实际依赖方向以 `bot → infra/core`、`infra → core` 为主。`core/models.py` 是领域数据结构与 SQLAlchemy 映射的结合点，因此 `core` 并非完全不依赖基础设施库。

## 数据和状态放在哪里

- `UserData`：用户长度、胜率、挑战标记和上次活动时间。
- `GroupData`：群是否允许使用插件。
- `EjaculationData`：按用户和日期保存的注入量记录。
- SQLite 文件位于 `nonebot-plugin-localstore` 提供的插件数据目录，文件名为 `impart.db`；启动时自动建表并补充旧数据库缺少的状态列。
- 四类冷却分别保存在 `CooldownManager` 的内存字典中，进程重启后清空；SUPERUSER 跳过冷却检查。

## 最重要的约束

- 当前实现直接依赖 OneBot V11 的群事件、权限和消息段，不是跨适配器实现。
- Python 支持范围是 3.11–3.13。
- 所有游戏写路径应避免把长度持久化为精确的 `0`；跨越零点时使用 `-0.01` 表达负值世界。
- PK 只允许同世界玩家参与，关键结算在单个数据库事务中更新双方。
- 图表依赖 `nonebot-plugin-htmlrender` 的浏览器环境；浏览器不可用时排行榜与历史图可能失败，但文本玩法不共享该渲染路径。

## 已知维护风险

- `PluginConfig.usage` 中的 PK 说明仍使用旧版“随机数/2、胜率 ±1%”措辞，与当前归一化胜率和阻尼算法不一致。
- 冷却状态不持久化，重启会重置所有冷却。
- 旧 Memory Bank 中的多阶级、技能、Buff、成就和 Alconna/UniInfo 适配均是未实现构想，不属于当前架构。
