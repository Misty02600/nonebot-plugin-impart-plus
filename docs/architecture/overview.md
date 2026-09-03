# 项目架构

## 先建立一个印象

`nonebot_plugin_impart_plus` 是面向 NoneBot2 群聊与频道场景的互动游戏插件。管理员先为场景开启功能，成员再通过命令创建和改变长度、进行 PK、与群友互动，以及查询排行榜和注入记录。bot 接入使用 Alconna、Uninfo、UniRef 和 UniMessage，metadata 通过 `inherit_supported_adapters()` 动态继承三项接入依赖的 Adapter 交集。

当前 `feature` 使用粗粒度传统分层：bot 接收入站事件并生成回复，`impart/app.py` 编排完整游戏用例，`impart/core.py` 保存框架无关的纯规则，infra 封装数据库、冷却和图表等具体技术。这里记录当前代码事实，不把 `main` 分支的新增玩法视为既定目标。

## 核心能力与公开入口

插件当前对外承诺的是 NoneBot 命令和配置项，不提供独立的 Python 业务 API 稳定性承诺。首次发布到 NoneBot 插件市场前，SQLite schema 始终视为开发中的 v1，现有开发数据库不属于兼容承诺。

| 核心能力或公开入口 | 对外含义 | 关键状态或副作用 | 主要实现位置 |
|---|---|---|---|
| 群开关与帮助 | `银趴` 根命令把开启/开始、禁止/关闭直接解析为一个布尔参数，帮助/介绍保留独立子命令；compact 允许有/无空格，开关限管理员、群主或超级用户 | 一个 toggle dispatch 和 Handler 持久化场景级 `allow` 状态；帮助 dispatch 保留独立权限与优先级；完整帮助文本来自 `PluginMetadata.usage` | [`__init__.py`](../../src/nonebot_plugin_impart_plus/__init__.py)、[`bot/matchers.py`](../../src/nonebot_plugin_impart_plus/bot/matchers.py)、[`bot/handlers/control.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/control.py) |
| 长度成长与查询 | `打胶/开导` 增加本人长度，`嗦牛子/嗦/suo` 增加本人或被 `@` 用户长度；`银趴/impart` 根命令下的 `查询` 子命令显示本人或被 `@` 用户的长度状态 | 查询使用独立 dispatch 并在匹配后阻断传播；应用层处理冷却、创建用户、状态读取和保存，bot 只生成原有回复 | [`impart/app.py`](../../src/nonebot_plugin_impart_plus/impart/app.py)、[`bot/handlers/game.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/game.py) |
| PK 与登神挑战 | `pk/对决` 需要 `@` 对手；按发起者战力判定胜负，并调整双方长度和内部战力值 | 保持原有多次独立数据库提交；纯胜负与增量计算位于 core | [`impart/app.py`](../../src/nonebot_plugin_impart_plus/impart/app.py)、[`impart/core.py`](../../src/nonebot_plugin_impart_plus/impart/core.py)、[`bot/handlers/game.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/game.py) |
| 群友互动 | `透` 为根命令、`日` 为 alias，群友/管理/群主使用参数结构独立的子命令；只有群友接受可选 At，compact 允许有/无空格 | Uninfo 提供成员、角色、昵称与头像；群友可指定或随机，管理和群主只按角色自动选择；找不到角色时返回对应提示，最终目标为发起者时统一拒绝；应用层处理冷却、反透和注入写入 | [`bot/matchers.py`](../../src/nonebot_plugin_impart_plus/bot/matchers.py)、[`bot/handlers/interaction.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/interaction.py)、[`impart/app.py`](../../src/nonebot_plugin_impart_plus/impart/app.py) |
| 排行榜与注入查询 | 在当前 `UserRef.namespace` 内显示长度前五、后五和本人排名；查询当天或历史注入量 | DataManager 通过 namespace 索引分榜，应用层返回类型化 Ref 条目，bot 调用 Pillow renderer 生成 PNG | [`impart/app.py`](../../src/nonebot_plugin_impart_plus/impart/app.py)、[`bot/handlers/records.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/records.py)、[`infra/chart_renderer.py`](../../src/nonebot_plugin_impart_plus/infra/chart_renderer.py) |
| `Config` | 配置四类冷却时长、不活跃惩罚和长度别名 | 只描述插件启动配置；帮助文案属于插件元数据，机器人昵称读取 NoneBot 全局配置，可变冷却状态属于 infra | [`config.py`](../../src/nonebot_plugin_impart_plus/config.py)、[`bot/dependencies.py`](../../src/nonebot_plugin_impart_plus/bot/dependencies.py)、[`infra/cooldown.py`](../../src/nonebot_plugin_impart_plus/infra/cooldown.py) |

## 逻辑组件与实现映射

| 逻辑组件 | 当前职责 | 主要协作与边界 | 拥有的数据或状态 | 主要实现位置 |
|---|---|---|---|---|
| 插件入口与 bot 接入 | `matchers.py` 共同定义 grammar、matcher 和 dispatch，各 matcher 直接把 Uninfo `GROUP | GUILD` 作为公开场景 Rule checker；`handlers/` 用模块级装饰器按游戏、互动、记录、控制拆分事件处理；`bot/__init__.py` 只管理启动和定时任务 | Uninfo 解析场景、成员与权限；Handler 统一注入 UniRef `RefContext`，从属性取得当前 UserRef/SceneRef，并用 `build_user_ref()` 将 Alconna At 的用户 ID 限定到当前 identity family；身份上下文不适用时跳过当前 Handler，事件传播继续遵循 matcher 自身的 `block` 设置；UniMessage 发送回复 | 单次事件上下文；模块级机器人昵称 | [`__init__.py`](../../src/nonebot_plugin_impart_plus/__init__.py)、[`bot/matchers.py`](../../src/nonebot_plugin_impart_plus/bot/matchers.py)、[`bot/handlers/__init__.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/__init__.py) |
| 应用用例 | 按原有顺序执行场景开关、Ref 冷却、随机、数据读取、core 计算和持久化，返回语义化 outcome | 身份参数只接受 `UserRef`/`SceneRef`；当前直接依赖具体 infra，实现单入口传统分层，没有 ports | 无独立持久状态；持有 `CooldownManager` | [`impart/app.py`](../../src/nonebot_plugin_impart_plus/impart/app.py) |
| 核心规则 | 分类长度状态，计算挑战、xnn、非正长度状态转换，以及 PK 结果和反透条件 | 只依赖标准库；不导入 NoneBot、SQLAlchemy 或 Pillow | 不持有运行状态 | [`impart/core.py`](../../src/nonebot_plugin_impart_plus/impart/core.py) |
| 数据库与数据访问 | 定义全新 v1 Ref ORM、执行 CRUD，并把 ORM 用户状态映射给 core 后写回转换结果 | DataManager 独占 `encode_ref()`/`decode_ref()`，同步维护 namespace/type 查询投影；不接受裸 ID，也不包含旧 schema 兼容；每个方法保持独立提交 | UserRef 用户状态、SceneRef 开关和注入记录 | [`infra/database.py`](../../src/nonebot_plugin_impart_plus/infra/database.py)、[`infra/data_manager.py`](../../src/nonebot_plugin_impart_plus/infra/data_manager.py) |
| 运行时与媒体基础设施 | 以 `UserRef` 保存四类冷却时间戳；使用 Pillow 和内置字体绘制图片 | 由 `bot/dependencies.py` 组装并提供给应用或 bot | 进程内 Ref 冷却字典；renderer 实例的调色板和字体路径 | [`infra/cooldown.py`](../../src/nonebot_plugin_impart_plus/infra/cooldown.py)、[`infra/chart_renderer.py`](../../src/nonebot_plugin_impart_plus/infra/chart_renderer.py) |

主要代码依赖方向是 `bot → impart.app → impart.core/infra`，同时 bot 为呈现排行榜和历史记录而直接调用 `infra.chart_renderer`。`bot/dependencies.py` 是 composition root，可以同时引用配置、应用和具体基础设施。

## 运行时数据流

1. Alconna 解析结构化命令、子命令、Option 与 At；Uninfo 提供场景、用户、成员和角色。
2. Handler 注入 UniRef `RefContext`，在业务副作用前取得当前 UserRef/SceneRef，并通过 `build_user_ref()` 构造 Alconna At 目标；上下文本身无法建立时当前 Handler 被跳过，属性或目标构造失败则保留异常。
3. `GameApplication` 按原实现顺序检查场景开关和 Ref 冷却，通过注入的 `DataManager` 读取状态。
4. 需要纯计算时，application 将普通数值传给 `impart/core.py`，取得状态分类、PK 增量或反透结果。
5. application 调用 `DataManager` 方法保存变化，并返回不包含 NoneBot 事件对象的 outcome。
6. bot 根据 outcome 选择文案；需要图片时再调用 `ChartRenderer`，最后通过 UniMessage 以 AUTO fallback 发送。

## 数据和状态放在哪里

- `UserData` 以编码 `user_ref` 为主键，保存 `user_namespace` 查询投影、长度、最后活动时间、内部战力，以及挑战、xnn 临界区和非正长度标记。
- `SceneData` 以编码 `scene_ref` 为主键，保存 `scene_namespace`、`scene_type` 查询投影和场景开关。
- `EjaculationData` 按编码 UserRef 和日期保存注入量；同一天的记录累加到同一数值。
- SQLite 文件位于 `nonebot-plugin-localstore` 提供的插件数据目录，文件名为 `impart.db`。启动时只按当前 v1 模型建表，不探测或升级旧 schema。
- 打胶、PK、嗦和群友互动冷却保存在 `CooldownManager` 的四个 UserRef 字典中，进程重启后清空；所有用户使用相同冷却规则，不提供超级用户豁免。
- 每日零点任务调用 application 的不活跃惩罚用例；开启惩罚时，各主要命令也按原行为在处理前执行同一检查。

## 当前稳定状态语义

- 新用户初始长度为 `10.0`，内部战力为 `0.5`。
- `25 <= length < 30` 会进入登神挑战并把内部战力乘以 `0.8`；挑战期间禁止打胶和嗦。
- 挑战中跌到 `length < 25` 会退出挑战、恢复内部战力系数并额外减少 5；达到 `length >= 30` 会完成挑战。
- `0 < length <= 5` 被标记为 xnn 临界区，`length <= 0` 显示为女孩子状态；当前没有与负长度对应的独立成长、PK 或群友互动命令体系。
- PK 只使用发起者自身的内部战力判定胜负；胜者内部战力减 `0.01`，败者增加 `0.01`。双方长度和战力继续通过多次独立数据库提交更新。
- xnn 发起群友互动时有 50% 概率被反透，非正长度发起者必定成为被注入方；注入记录本身不会改变长度。

## 当前质量边界与维护风险

- 当前测试覆盖插件与 13 个 Alconna matcher 注册、严格 grammar、Uninfo 场景/成员/角色、Ref Handler 参数、namespace schema/排行榜、冷却隔离、能力降级和 UniMessage 文本/图片结构；OneBot 以外 Adapter 的完整事件 fixture 仍待补齐。
- `bot/handlers/` 已按 `game`、`interaction`、`records`、`control` 拆分；`yinpa` 由群友、管理、群主三个 dispatch matcher 复用，因为三者共享同一互动用例，只在 grammar 与目标选择上分支；其他业务 Handler 仍与 matcher 一一对应。跨功能共享只保留未开启文案与用户目录辅助函数，`game.py` 因 PK 分支文案仍是其中最大的模块。
- PK 和挑战结算继续由多个 `DataManager` 方法分别提交；中途异常可能留下双方状态只更新一部分的结果。
- `get_jj_length()` 和 `get_win_probability()` 使用真假值回退默认值，持久化的精确 `0` 与“没有查询结果”不能被区分。
- 用户文案已使用“战力”，内部字段和计算仍沿用 `win_probability`；后续设计需要明确战力是展示名称还是新的数值语义。
- UniRef 0.4 的 QQAPI 群成员和频道用户使用复合完整 `UserRef.id`；排行榜当前不能据此可靠查询 Uninfo 用户资料，查询失败时退回 Ref ID 展示，不拆解上游私有格式，等待 UniRef 提供 Ref 到资料的公开查询入口。
- 当前 Ref schema 不兼容旧开发数据库，也没有迁移、回填、v2 表或 legacy 分支；首次进入 NoneBot 插件市场前直接重建开发数据库，发布后再建立正式迁移策略。
