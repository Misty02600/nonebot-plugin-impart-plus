# 项目架构

## 先建立一个印象

`nonebot_plugin_impart_plus` 是面向 NoneBot2 群聊与频道场景的互动游戏插件。管理员先为场景开启功能，成员再通过命令创建和改变长度或深度、进行 PK、与群友互动，以及查询排行榜和注入记录。bot 接入使用 Alconna、Uninfo、UniRef 和 UniMessage，数据基础设施使用 NoneBot ORM；metadata 通过 `inherit_supported_adapters()` 动态继承三项消息接入依赖的 Adapter 交集。实际实现与回归验收优先保证 OneBot V11，其他 Adapter 仅保持理论兼容边界。

当前 `feature` 使用粗粒度传统分层：bot 接收入站事件并生成回复，`impart/app.py` 编排完整游戏用例，`impart/core.py` 保存框架无关的纯规则，infra 封装数据库、冷却和图表等具体技术。这里记录当前代码事实，不把 `main` 分支的新增玩法视为既定目标。

## 核心能力与公开入口

插件当前对外承诺的是 NoneBot 命令和配置项，不提供独立的 Python 业务 API 稳定性承诺。首次发布到 NoneBot 插件市场前，数据库 schema 始终视为开发中的 v1，现有开发数据库不属于兼容承诺。数据库必须位于最新 ORM revision；默认启动检查可在交互式终端确认后升级，非交互部署应提前运行 `nb orm upgrade`。

| 核心能力或公开入口 | 对外含义 | 关键状态或副作用 | 主要实现位置 |
|---|---|---|---|
| 群开关与帮助 | `银趴` 根命令把开启/开始、禁止/关闭直接解析为一个布尔参数，帮助/介绍保留独立子命令；compact 允许有/无空格，开关限管理员、群主或超级用户 | 一个 toggle dispatch 和 Handler 持久化场景级 `allow` 状态；帮助 dispatch 保留独立权限与优先级；完整帮助文本来自 `PluginMetadata.usage`；与其他顶层命令一样从 NoneBot `COMMAND_START` 取得前缀 | [`__init__.py`](../../src/nonebot_plugin_impart_plus/__init__.py)、[`bot/matchers.py`](../../src/nonebot_plugin_impart_plus/bot/matchers.py)、[`bot/handlers/control.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/control.py) |
| 长度与深度成长、查询 | `打胶/开导` 服务 `length > 0` 并增加本人长度，`开扣/挖矿` 服务 `length <= 0` 并增加绝对深度；`嗦` 只增加被 `@` 正值用户的长度，`舔` 只增加被 `@` 非正值用户的深度；`银趴查询` 显示状态和当日注入量，`查询历史/全部` 再显示历史总量和折线图 | 自我成长和目标成长分别各用一个 Alconna matcher；目标成长允许多个 At 但只使用第一个。状态与记录查询共用 `query.py` Handler，DataManager 按普通/历史模式取得一致快照 | [`bot/matchers.py`](../../src/nonebot_plugin_impart_plus/bot/matchers.py)、[`bot/handlers/game.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/game.py)、[`bot/handlers/query.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/query.py)、[`impart/app.py`](../../src/nonebot_plugin_impart_plus/impart/app.py) |
| 同世界 PK 与正负挑战 | `pk/对决` 必须 `@` 同世界其他用户；允许多个用户 At，但严格只使用第一个。正值双方结算长度，负值双方以相反方向结算深度，跨世界拒绝；胜负继续由发起者胜率判定 | 正负世界都按绝对量级评估挑战；PK 与挑战惩罚被锁在原世界的 `±0.001cm`，普通玩法不能跨零。core 一次计算双方完整结果，DataManager 在一个事务中提交双方状态 | [`impart/app.py`](../../src/nonebot_plugin_impart_plus/impart/app.py)、[`impart/core.py`](../../src/nonebot_plugin_impart_plus/impart/core.py)、[`bot/handlers/game.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/game.py) |
| 群友互动与雌堕 | `透/日/榨` 由同一个命令头解析；正值用户主动透，负值用户主动榨，动作与自身世界不匹配或 XNN 透触发反制时，由目标按其世界反制一次 | 透与榨共用无类型当日总量。只有实际被透且结算时仍满足 `0 < length < 5` 的接收者会按当日总量判定雌堕：`200ml` 后概率线性增加，`1000ml` 必定触发；累计量和长度转换在一个事务内提交 | [`bot/handlers/interaction.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/interaction.py)、[`impart/app.py`](../../src/nonebot_plugin_impart_plus/impart/app.py)、[`impart/core.py`](../../src/nonebot_plugin_impart_plus/impart/core.py)、[`infra/data_manager.py`](../../src/nonebot_plugin_impart_plus/infra/data_manager.py) |
| 排行榜 | 在当前 `UserRef.namespace` 内显示长度前五、后五和本人排名 | DataManager 通过 namespace 索引分榜，bot 调用 Pillow renderer 生成 PNG | [`impart/app.py`](../../src/nonebot_plugin_impart_plus/impart/app.py)、[`bot/handlers/records.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/records.py)、[`infra/chart_renderer.py`](../../src/nonebot_plugin_impart_plus/infra/chart_renderer.py) |
| `Config` | 配置四类冷却时长 | 牛牛与负值部位名称是代码内玩法常量，不属于部署配置；帮助文案属于插件元数据，机器人昵称读取 NoneBot 全局配置，可变冷却状态属于 infra | [`config.py`](../../src/nonebot_plugin_impart_plus/config.py)、[`bot/dependencies.py`](../../src/nonebot_plugin_impart_plus/bot/dependencies.py)、[`infra/cooldown.py`](../../src/nonebot_plugin_impart_plus/infra/cooldown.py) |

## 逻辑组件与实现映射

| 逻辑组件 | 当前职责 | 主要协作与边界 | 拥有的数据或状态 | 主要实现位置 |
|---|---|---|---|---|
| 插件入口与 bot 接入 | `matchers.py` 共同定义 grammar、matcher 和 dispatch；所有顶层 matcher 显式启用 `use_cmd_start=True`，由 NoneBot `COMMAND_START` 决定可用前缀；各 matcher 直接把 Uninfo `GROUP | GUILD` 作为公开场景 Rule checker；`handlers/` 用模块级装饰器按游戏、互动、记录、控制拆分事件处理 | Uninfo 解析场景、成员与权限；Handler 统一注入 UniRef `RefContext`，从属性取得当前 UserRef/SceneRef，并用 `build_user_ref()` 将 Alconna At 的用户 ID 限定到当前 identity family；身份上下文不适用时跳过当前 Handler，事件传播继续遵循 matcher 自身的 `block` 设置；UniMessage 发送回复 | 单次事件上下文；模块级机器人昵称 | [`__init__.py`](../../src/nonebot_plugin_impart_plus/__init__.py)、[`bot/matchers.py`](../../src/nonebot_plugin_impart_plus/bot/matchers.py)、[`bot/handlers/__init__.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/__init__.py) |
| 应用用例 | 依次执行场景和命令语义检查、缺失用户初始化、世界与 Ref 冷却检查、随机、core 计算和持久化，返回语义化 outcome | 身份参数只接受 `UserRef`/`SceneRef`；初始化后不继续其他副作用；一个 `asyncio.Lock` 从状态读取保护到写入完成，由 PK、成长和互动结算共用；互动的两秒等待和资料查询位于锁外 | 持有 `CooldownManager` 与进程内用户状态结算锁 | [`impart/app.py`](../../src/nonebot_plugin_impart_plus/impart/app.py) |
| 核心规则 | 分类长度状态和正负成长模式，计算世界锁、挑战、PK、互动反制及雌堕概率 | 只依赖标准库；`is_xnn()` 是唯一 XNN 边界；PK 结果保留结算前、基础变化后和挑战处理后状态，互动量结算结果显式携带风险警告与雌堕事件 | 不持有运行状态 | [`impart/core.py`](../../src/nonebot_plugin_impart_plus/impart/core.py) |
| 数据库与数据访问 | 三个模型继承 NoneBot ORM `Model`，由包内 Alembic migration 管理全新 v1 Ref schema；DataManager 原子提交 PK，以及互动总量与雌堕长度；旧库导入器负责一次性复制上游数据 | 默认 SQLite 但可切换 ORM 支持的其他默认数据库后端；单进程 application 锁负责串行化，不实现多进程重试。查询用一条 SQL 获取长度及当天或完整有序记录；导入忽略上游派生状态列并把 `0/-0.0` 规范化为 `-0.001` | UserRef 用户状态、SceneRef 开关和按用户/日期唯一的互动总量 | [`infra/database.py`](../../src/nonebot_plugin_impart_plus/infra/database.py)、[`infra/data_manager.py`](../../src/nonebot_plugin_impart_plus/infra/data_manager.py)、[`infra/legacy_import.py`](../../src/nonebot_plugin_impart_plus/infra/legacy_import.py)、[`migrations/`](../../src/nonebot_plugin_impart_plus/migrations/) |
| 运行时与媒体基础设施 | 以 `UserRef` 保存四类冷却时间戳；使用 Pillow 和内置字体绘制图片 | 由 `bot/dependencies.py` 组装并提供给应用或 bot | 进程内 Ref 冷却字典；renderer 实例的调色板和字体路径 | [`infra/cooldown.py`](../../src/nonebot_plugin_impart_plus/infra/cooldown.py)、[`infra/chart_renderer.py`](../../src/nonebot_plugin_impart_plus/infra/chart_renderer.py) |

主要代码依赖方向是 `bot → impart.app → impart.core/infra`，同时 bot 为呈现排行榜和历史记录而直接调用 `infra.chart_renderer`。`bot/dependencies.py` 是 composition root，可以同时引用配置、应用和具体基础设施。

## 运行时数据流

1. NoneBot ORM 先完成 schema 启动检查或同步；随后插件启动时检查上游 LocalStore `nonebot_plugin_impart/impart.db`。源文件不存在、三个业务表任一非空或源库没有记录时跳过；只有目标全空且源库有数据时，才在一个目标 Session 中从同一个 SQLite 只读事务取得用户、群开关和注入记录快照并整体提交。多个 Bot 共用同一进程启动流程；不承诺多个 NoneBot 进程同时执行首次导入。
2. 所有顶层 matcher 先把 NoneBot `COMMAND_START` 作为命令前缀，再由 Alconna 解析结构化命令、子命令、Option 与 At；Uninfo 提供场景、用户、成员和角色。
3. Handler 注入 UniRef `RefContext`，在业务副作用前取得当前 UserRef/SceneRef，并通过 `build_user_ref()` 构造 Alconna At 目标；上下文本身无法建立时当前 Handler 被跳过，属性或目标构造失败则保留异常。
4. `GameApplication` 先检查场景与命令语义；PK、嗦或舔缺少目标以及 At 自己时先返回，不创建用户或执行其他副作用。有效目标与打胶、开扣、查询所涉及的缺失用户会创建默认状态；只要这些长度相关用例发生创建就返回实际 Ref，不执行冷却或结算。群友互动同样会在发起者首次创建后立即返回，但缺失目标会初始化为默认正值并继续本次互动。
5. 用户均已存在时，PK 与成长从状态读取起取得 application 的共享结算锁。互动先完成目标选择、提示和两秒等待，再按“数量、耗时”的顺序生成原有随机值并取得同一把锁；锁内重新读取实际接收者长度，只有实际被透的 XNN 才额外生成一次雌堕随机值。
6. PK 由 DataManager 在一个事务中写回双方完整状态；互动由另一个事务同时累计当日总量并按 core 结果更新长度，异常时各自整体回滚。普通查询只联接当天记录，历史查询读取按日期升序排列的全部记录。
7. bot 根据 outcome 选择文案；风险警告或雌堕文案追加在正常互动结算之后，需要图片时再调用 `ChartRenderer`，最后通过 UniMessage 发送。消息发送失败不回滚已经提交的游戏状态。

## 数据和状态放在哪里

- `UserData` 以编码 `user_ref` 为主键，保存 `user_namespace` 查询投影、长度、内部胜率和两项挑战状态；XNN 与正负世界完全由长度推导，不保存展示缓存。
- `SceneData` 以编码 `scene_ref` 为主键，保存 `scene_namespace`、`scene_type` 查询投影和场景开关。
- `EjaculationData` 按编码 UserRef 和日期保存透或榨产生的无类型互动总量；`(user_ref, date)` 具有唯一约束，记录归属实际获得液体者，公开查询统一称为“注入量”。
- 数据库连接、Engine 和 Session 由 NoneBot ORM 管理；默认未配置时使用 `[default]` extra 提供的 SQLite，也可安装其他驱动并用 `SQLALCHEMY_DATABASE_URL` 切换默认连接。包内 generic migration 管理 schema；自动化在 SQLite 执行 migration、旧库导入和并发持久化测试，并为 PostgreSQL、MySQL 编译模型 DDL，但不连接这两种数据库做集成验证。
- 打胶、PK、目标成长和群友互动冷却保存在 `CooldownManager` 的四个 UserRef 字典中；嗦与舔共享现有 `suo_cd_data`，进程重启后清空。所有用户使用相同冷却规则，不提供超级用户豁免。
- PK、打胶、开扣、嗦、舔和互动最终结算通过同一个 application 级锁串行访问用户游戏状态；多个 Bot 在同一进程共享该锁。锁和冷却一样不跨进程，数据库后端可以替换，但多进程或外部直接写库不属于并发保证。

## 当前稳定状态语义

- 新用户初始长度为 `10.0`，内部胜率为 `0.5`。打胶、开扣、查询，或带有效非自身目标的嗦、舔和 PK 发现本次涉及的用户缺失时，只创建缺失者并回复，不消耗冷却或执行其他结算；缺少目标或 At 自己时不创建用户。群友互动的发起者也遵循“只创建并回复”，互动目标缺失时则创建后继续，排行榜维持自己的初始化路径。
- `25 <= abs(length) < 30` 会进入挑战并把内部胜率乘以 `0.8`；正值世界开启“登神长阶”，负值世界开启“深渊试炼”。挑战期间正值用户不能打胶或嗦，负值用户不能开扣或舔，挑战中的目标也不能被嗦或舔，只能通过同世界 PK 推进挑战。
- 挑战中跌到 `abs(length) < 25` 会退出挑战、恢复内部胜率系数，并向零方向额外惩罚 5cm；达到 `abs(length) >= 30` 会完成挑战。完成后再次跌破 25cm 会取消称号并执行同方向惩罚。
- `0 < length < 5` 是唯一 XNN 范围，恰好 `5cm` 属于普通正值；负值状态查询显示固定名称“小学”和绝对深度，`length <= -30` 显示“深淵の主”。XNN 当日总量超过 `200ml` 时，查询改为提示“快要变成女孩子”。
- PK 只使用发起者自身的内部胜率判定胜负；胜者内部胜率减 `0.01`，败者增加 `0.01`。PK 与挑战惩罚不能改变正负号，跨零候选值分别钳制为 `0.001/-0.001`；只有雌堕可以把正值转换为负值。
- XNN 主动透时仍有 50% 概率被反制。正值主动榨或负值主动透时必定反制；目标按其世界反透或反榨，最多反制一次。实际被透的 XNN 使用包含本次数量的当日总量按 `clamp((total - 200) / 800, 0, 1)` 判定雌堕，命中后长度减去 `5cm`；实际榨不检查也不消费该随机数。

## 当前质量边界与维护风险

- 当前测试覆盖插件与 10 个 Alconna matcher 注册、ORM schema 与三种目标方言 DDL、SQLite migration、旧库导入、PK 与互动事务回滚、单进程并发结算、command start 与查询 grammar、XNN/零点/概率边界、首次初始化、正负成长与挑战、互动归属及关键文案、Uninfo 查询和 UniMessage 文本/图片结构；这些聚焦测试是当前 OneBot V11 验收边界，不计划增加 Adapter 事件级 fixture。
- 英文根命令 alias `impart` 只接受小写；排行榜自身的 `rank` 正则仍保持大小写不敏感。上游 `IMPART帮助` 等大小写变体不再作为兼容入口。
- `bot/handlers/` 已按 `game`、`interaction`、`query`、`records`、`control` 拆分；普通查询和历史查询共享一个 Handler，`records.py` 只负责排行榜。群友、管理、群主共享互动 Handler，打胶与开扣共享成长 Handler。
- `get_jj_length()` 和 `get_win_probability()` 使用真假值回退默认值，持久化的精确 `0` 与“没有查询结果”不能被区分。
- 用户文案与底层字段均保留“胜率”语义；当前 PK 直接使用发起者的 `win_probability` 判定，查询暂不展示该值，双方胜率归一化延后为独立玩法改动。
- UniRef 0.4 的 QQAPI 群成员和频道用户使用复合完整 `UserRef.id`；排行榜当前不能据此可靠查询 Uninfo 用户资料，查询失败时退回 Ref ID 展示，不拆解上游私有格式，等待 UniRef 提供 Ref 到资料的公开查询入口。
- Discord 的群主身份不能从普通角色权限可靠推导；Uninfo 0.11.1 的 `OWNER` 映射尚不足以证明真实 Guild owner。该限制仅作为理论兼容边界记录，不是当前发布闸门，本插件也不添加 Discord 专用查询分支。
- 旧库导入只识别 `nonebot_plugin_impart` 在当前 LocalStore 配置下的标准 `impart.db`，不提供手工路径、合并、覆盖或反向同步；源库缺少必要表或基础列时启动失败，后加的挑战列缺失时使用上游默认值，派生展示列会被忽略，零长度统一导入为 `-0.001`。
