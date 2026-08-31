# 项目架构

## 先建立一个印象

`nonebot_plugin_impart_plus` 是面向 NoneBot2 与 OneBot V11 群聊的互动游戏插件。管理员先为群聊开启功能，群成员再通过命令创建和改变长度、进行 PK、与群友互动，以及查询排行榜和注入记录。

当前 `feature` 使用粗粒度传统分层：bot 接收入站事件并生成回复，`impart/app.py` 编排完整游戏用例，`impart/core.py` 保存框架无关的纯规则，infra 封装数据库、冷却和图表等具体技术。这里记录当前代码事实，不把 `main` 分支的新增玩法视为既定目标。

## 核心能力与公开入口

插件当前对外承诺的是 NoneBot 命令和配置项，不提供独立的 Python 业务 API 稳定性承诺。首次发布到 NoneBot 插件市场前，SQLite schema 始终视为开发中的 v1，现有开发数据库不属于兼容承诺。

| 核心能力或公开入口 | 对外含义 | 关键状态或副作用 | 主要实现位置 |
|---|---|---|---|
| 群开关与帮助 | 管理员、群主或超级用户开启和关闭群内玩法；成员查看命令说明 | 持久化群级 `allow` 状态；完整帮助文本由插件元数据 `PluginMetadata.usage` 提供 | [`__init__.py`](../../src/nonebot_plugin_impart_plus/__init__.py)、[`bot/__init__.py`](../../src/nonebot_plugin_impart_plus/bot/__init__.py)、[`bot/handlers.py`](../../src/nonebot_plugin_impart_plus/bot/handlers.py) |
| 长度成长与查询 | `打胶/开导` 增加本人长度，`嗦牛子/嗦/suo` 增加本人或被 `@` 用户长度，`查询` 显示长度状态 | 应用层处理冷却、创建用户、状态读取和保存，bot 只生成原有回复 | [`impart/app.py`](../../src/nonebot_plugin_impart_plus/impart/app.py)、[`bot/handlers.py`](../../src/nonebot_plugin_impart_plus/bot/handlers.py) |
| PK 与登神挑战 | `pk/对决` 需要 `@` 对手；按发起者战力判定胜负，并调整双方长度和内部胜率值 | 保持原有多次独立数据库提交；纯胜负与增量计算位于 core | [`impart/app.py`](../../src/nonebot_plugin_impart_plus/impart/app.py)、[`impart/core.py`](../../src/nonebot_plugin_impart_plus/impart/core.py) |
| 群友互动 | `日/透群友`、`日/透群主`、`日/透管理` 选择目标并记录注入量 | bot 读取群成员角色，应用层处理冷却、活动记录、反透判定和注入写入 | [`bot/handlers.py`](../../src/nonebot_plugin_impart_plus/bot/handlers.py)、[`impart/app.py`](../../src/nonebot_plugin_impart_plus/impart/app.py) |
| 排行榜与注入查询 | 显示长度前五、后五和本人排名；查询当天或历史注入量 | 应用层返回普通数据，bot 调用 Pillow renderer 生成 PNG | [`impart/app.py`](../../src/nonebot_plugin_impart_plus/impart/app.py)、[`infra/chart_renderer.py`](../../src/nonebot_plugin_impart_plus/infra/chart_renderer.py) |
| `Config` | 配置四类冷却时长、不活跃惩罚和长度别名 | 只描述插件启动配置；帮助文案属于插件元数据，机器人昵称读取 NoneBot 全局配置，可变冷却状态属于 infra | [`config.py`](../../src/nonebot_plugin_impart_plus/config.py)、[`bot/dependencies.py`](../../src/nonebot_plugin_impart_plus/bot/dependencies.py)、[`infra/cooldown.py`](../../src/nonebot_plugin_impart_plus/infra/cooldown.py) |

## 逻辑组件与实现映射

| 逻辑组件 | 当前职责 | 主要协作与边界 | 拥有的数据或状态 | 主要实现位置 |
|---|---|---|---|---|
| 插件入口与 bot 接入 | 声明元数据、注册 matcher 和定时任务、解析 OneBot 事件、选择群成员、组合并发送文案 | 通过组装模块取得 `GameApplication`；不直接调用数据库和冷却 | 单次事件上下文；模块级机器人昵称 | [`__init__.py`](../../src/nonebot_plugin_impart_plus/__init__.py)、[`bot/`](../../src/nonebot_plugin_impart_plus/bot) |
| 应用用例 | 按原有顺序执行群开关、冷却、随机、数据读取、core 计算和持久化，返回语义化 outcome | 当前直接依赖具体 infra，实现单入口传统分层，没有 ports | 无独立持久状态；持有 `CooldownManager` | [`impart/app.py`](../../src/nonebot_plugin_impart_plus/impart/app.py) |
| 核心规则 | 分类长度状态，计算挑战、xnn、非正长度状态转换，以及 PK 结果和反透条件 | 只依赖标准库；不导入 NoneBot、SQLAlchemy 或 Pillow | 不持有运行状态 | [`impart/core.py`](../../src/nonebot_plugin_impart_plus/impart/core.py) |
| 数据库与数据访问 | 定义 ORM、初始化和兼容旧字段，执行 CRUD，并把 ORM 用户状态映射给 core 后写回转换结果 | `database.py` 拥有 engine/session factory，composition root 创建单个 `DataManager`；每个方法保持独立提交 | 用户、群开关和注入记录 | [`infra/database.py`](../../src/nonebot_plugin_impart_plus/infra/database.py)、[`infra/data_manager.py`](../../src/nonebot_plugin_impart_plus/infra/data_manager.py) |
| 运行时与媒体基础设施 | 保存四类冷却时间戳；使用 Pillow 和内置字体绘制图片 | 由 `bot/dependencies.py` 组装并提供给应用或 bot | 进程内冷却字典；renderer 实例的调色板和字体路径 | [`infra/cooldown.py`](../../src/nonebot_plugin_impart_plus/infra/cooldown.py)、[`infra/chart_renderer.py`](../../src/nonebot_plugin_impart_plus/infra/chart_renderer.py) |

主要代码依赖方向是 `bot → impart.app → impart.core/infra`，同时 bot 为呈现排行榜和历史记录而直接调用 `infra.chart_renderer`。`bot/dependencies.py` 是 composition root，可以同时引用配置、应用和具体基础设施。

## 运行时数据流

1. `bot` 从 OneBot 事件提取群号、用户号、`@` 目标和群成员资料。
2. `GameApplication` 按原实现顺序检查群开关和冷却，通过注入的 `DataManager` 读取状态。
3. 需要纯计算时，application 将普通数值传给 `impart/core.py`，取得状态分类、PK 增量或反透结果。
4. application 调用 `DataManager` 方法保存变化，并返回不包含 NoneBot 对象的 outcome。
5. bot 根据 outcome 选择原有文案；需要图片时再调用 `ChartRenderer`，最后通过 matcher 发送。

## 数据和状态放在哪里

- `UserData` 保存 `userid`、长度 `jj_length`、最后活动时间、内部胜率 `win_probability`，以及挑战、xnn 临界区和非正长度标记。
- `GroupData` 保存群聊是否允许使用插件。
- `EjaculationData` 按用户和日期保存注入量；同一天的记录累加到同一数值。
- SQLite 文件位于 `nonebot-plugin-localstore` 提供的插件数据目录，文件名为 `impart.db`。启动时建表，并为旧 `userdata` 表补充缺失字段。
- 打胶、PK、嗦和群友互动冷却保存在 `CooldownManager` 的四个字典中，进程重启后清空；只有群友互动冷却明确允许超级用户绕过。
- 每日零点任务调用 application 的不活跃惩罚用例；开启惩罚时，各主要命令也按原行为在处理前执行同一检查。

## 当前稳定状态语义

- 新用户初始长度为 `10.0`，内部胜率为 `0.5`。
- `25 <= length < 30` 会进入登神挑战并把内部胜率乘以 `0.8`；挑战期间禁止打胶和嗦。
- 挑战中跌到 `length < 25` 会退出挑战、恢复内部胜率系数并额外减少 5；达到 `length >= 30` 会完成挑战。
- `0 < length <= 5` 被标记为 xnn 临界区，`length <= 0` 显示为女孩子状态；当前没有与负长度对应的独立成长、PK 或群友互动命令体系。
- PK 只使用发起者自身的内部胜率判定胜负；胜者内部胜率减 `0.01`，败者增加 `0.01`。双方长度和胜率继续通过多次独立数据库提交更新。
- xnn 发起群友互动时有 50% 概率被反透，非正长度发起者必定成为被注入方；注入记录本身不会改变长度。

## 当前质量边界与维护风险

- 现有仓库测试只验证插件可加载、配置默认值和测试事件构造；本轮另做了不入库的确定性 application/core 自检，但尚未形成长期回归测试。
- `bot/handlers.py` 仍集中全部 matcher 文案和群成员选择逻辑，后续只有在实际维护收益明确时再按能力拆分。
- PK 和挑战结算继续由多个 `DataManager` 方法分别提交；中途异常可能留下双方状态只更新一部分的结果。
- `get_jj_length()` 和 `get_win_probability()` 使用真假值回退默认值，持久化的精确 `0` 与“没有查询结果”不能被区分。
- 用户文案已使用“战力”，内部字段和计算仍沿用 `win_probability`；后续设计需要明确战力是展示名称还是新的数值语义。
- 当前数据库仍有兼容旧表的启动逻辑，但插件尚未发布，这段逻辑不构成兼容承诺。首次进入 NoneBot 插件市场前，模型或状态 schema 可以直接修改并重建开发数据库，不新增迁移、回填、v2 表或 legacy 兼容；发布后再建立正式的数据迁移策略。
