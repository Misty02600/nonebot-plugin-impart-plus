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
| 同世界 PK 与正负挑战 | `pk/对决` 必须 `@` 同世界其他用户；无阶最多1人，一/二/三阶最多2/3/4人，整场共用一次胜负 | 三阶个人基础变动倍率为2/3/4，挑战区间为25→30、300→320、1000→1050，系数0.9/0.8/0.7；从开始时持有阶级决定倍率与人数，最多五人一次事务提交 | [`impart/app.py`](../../src/nonebot_plugin_impart_plus/impart/app.py)、[`impart/core.py`](../../src/nonebot_plugin_impart_plus/impart/core.py)、[`bot/handlers/game.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/game.py) |
| 群友互动与雌堕 | `透/日/榨` 共用一个命令头；普通男性透、女性榨，XNN 对普通男性榨、对女性透，双 XNN 自动贴贴；错误动作由目标反制一次 | 普通互动一笔收量，贴贴双方互收；共用无类型当日总量。实际接收且结算时仍是 XNN 的成员独立判定雌堕，覆盖透、榨与贴贴；所有人的累计量和转换同日、同事务提交 | [`bot/handlers/interaction.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/interaction.py)、[`impart/app.py`](../../src/nonebot_plugin_impart_plus/impart/app.py)、[`impart/core.py`](../../src/nonebot_plugin_impart_plus/impart/core.py)、[`infra/data_manager.py`](../../src/nonebot_plugin_impart_plus/infra/data_manager.py) |
| 夺舍 | 持有一阶的负值用户可 `夺舍 @用户`，目标须为正值、未在挑战且长度短于自身深度；只取首个At，无别名 | 向上保留三位小数平分目标长度；发起者直接转正并按半长授予可满足的阶级、退出旧挑战不受惩罚，目标掉阶时承受一次对应称号惩罚；无额外冷却或成功率随机，双方原子提交 | [`bot/handlers/possession.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/possession.py)、[`impart/core.py`](../../src/nonebot_plugin_impart_plus/impart/core.py)、[`infra/data_manager.py`](../../src/nonebot_plugin_impart_plus/infra/data_manager.py) |
| 排行榜 | 在当前 `UserRef.namespace` 内显示长度前五、后五和本人；本人处于中段时追加左右各一位 | DataManager 通过 namespace 索引分榜；bot 按真实名次去重后获取 Uninfo 名称和头像，交给 HTMLKit 生成正蓝、负粉的柱状图；同名用户不合并 | [`impart/app.py`](../../src/nonebot_plugin_impart_plus/impart/app.py)、[`bot/handlers/records.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/records.py)、[`infra/chart_renderer.py`](../../src/nonebot_plugin_impart_plus/infra/chart_renderer.py) |
| `Config` | 配置四类冷却时长与可选绘图字体名称 `IMPART_FONT_FAMILY` | 字体选择只影响本插件的两种图，不管理字体文件或共享 Fontconfig；牛牛与负值部位名称是代码内玩法常量，帮助文案属于插件元数据，机器人昵称读取 NoneBot 全局配置，可变冷却状态属于 infra | [`config.py`](../../src/nonebot_plugin_impart_plus/config.py)、[`bot/dependencies.py`](../../src/nonebot_plugin_impart_plus/bot/dependencies.py)、[`infra/cooldown.py`](../../src/nonebot_plugin_impart_plus/infra/cooldown.py) |

## 逻辑组件与实现映射

| 逻辑组件 | 当前职责 | 主要协作与边界 | 拥有的数据或状态 | 主要实现位置 |
|---|---|---|---|---|
| 插件入口与 bot 接入 | `matchers.py` 共同定义 grammar、matcher 和 dispatch；所有顶层 matcher 显式启用 `use_cmd_start=True`，由 NoneBot `COMMAND_START` 决定可用前缀；各 matcher 直接把 Uninfo `GROUP | GUILD` 作为公开场景 Permission；`handlers/` 用模块级装饰器按游戏、互动、记录、控制拆分事件处理 | Uninfo 解析场景、成员与权限；Handler 统一注入 UniRef `RefContext`，从属性取得当前 UserRef/SceneRef，并用 `build_user_ref()` 将 Alconna At 的用户 ID 限定到当前 identity family；身份上下文不适用时跳过当前 Handler，事件传播继续遵循 matcher 自身的 `block` 设置；UniMessage 发送回复 | 单次事件上下文；模块级机器人昵称 | [`__init__.py`](../../src/nonebot_plugin_impart_plus/__init__.py)、[`bot/matchers.py`](../../src/nonebot_plugin_impart_plus/bot/matchers.py)、[`bot/handlers/__init__.py`](../../src/nonebot_plugin_impart_plus/bot/handlers/__init__.py) |
| 应用用例 | 依次执行场景和命令语义检查、缺失用户初始化、世界与 Ref 冷却检查、随机、core 计算和持久化，返回语义化 outcome | 身份参数只接受 `UserRef`/`SceneRef`；初始化后不继续其他副作用；一个 `asyncio.Lock` 从状态读取保护到写入完成，由 PK、成长、夺舍和互动结算共用；互动的两秒等待和资料查询位于锁外 | 持有 `CooldownManager` 与进程内用户状态结算锁 | [`impart/app.py`](../../src/nonebot_plugin_impart_plus/impart/app.py) |
| 核心规则 | 分类长度状态和正负成长模式，计算阶级挑战、个人倍率、世界锁、统一PK、互动反制及雌堕概率 | 只依赖标准库；`is_xnn()` 是唯一 XNN 边界；PK每个参与者保留结算前、基础变化后和挑战处理后状态，并从中计算实际基础变化，同一轮只处理每位参与者一次；成长返回实际增长量、最终状态及挑战事件，互动量结算显式携带风险警告与雌堕事件 | 不持有运行状态 | [`impart/core.py`](../../src/nonebot_plugin_impart_plus/impart/core.py) |
| 数据库与数据访问 | 三个模型继承 NoneBot ORM `Model`，由包内 Alembic migration 管理全新 v1 Ref schema；DataManager 原子提交成长、最多五人的PK、夺舍双方，以及互动总量与雌堕长度；旧库导入器负责一次性复制上游数据 | 默认 SQLite 但可切换 ORM 支持的其他默认数据库后端；单进程 application 锁负责串行化，不实现多进程重试。查询用一条 SQL 获取长度、阶级及当天或完整有序记录；导入把旧挑战标记规范化为阶级和对应胜率，并把 `0/-0.0` 规范化为 `-0.001` | UserRef 用户状态、SceneRef 开关和按用户/日期唯一的互动总量 | [`infra/database.py`](../../src/nonebot_plugin_impart_plus/infra/database.py)、[`infra/data_manager.py`](../../src/nonebot_plugin_impart_plus/infra/data_manager.py)、[`infra/legacy_import.py`](../../src/nonebot_plugin_impart_plus/infra/legacy_import.py)、[`migrations/`](../../src/nonebot_plugin_impart_plus/migrations/) |
| 运行时与媒体基础设施 | 以 `UserRef` 保存四类冷却时间戳；HTMLKit 按只读模板绘制排行榜与个人历史图 | 冷却由 `bot/dependencies.py` 组装；bot 传入展示条目及查询快照，媒体层不查库。原生渲染最多并发两次，头像下载最多并发四次，图片/CSS 外部加载关闭 | 进程内 Ref 冷却字典、渲染并发额度；昵称测量与头像仅保存在本次请求内，字体发现与初始化归 HTMLKit 管理 | [`infra/cooldown.py`](../../src/nonebot_plugin_impart_plus/infra/cooldown.py)、[`infra/chart_layout.py`](../../src/nonebot_plugin_impart_plus/infra/chart_layout.py)、[`infra/chart_renderer.py`](../../src/nonebot_plugin_impart_plus/infra/chart_renderer.py) |

主要代码依赖方向是 `bot → impart.app → impart.core/infra`，同时 bot 为呈现排行榜和历史记录而直接调用 `infra.chart_renderer`。`bot/dependencies.py` 是 composition root，可以同时引用配置、应用和具体基础设施。

两种图均为左侧人物或明细、右侧图表，刻度朝内。长度正负共用统一线性刻度；历史图以真实日期间隔绘制完整记录，缺失日期不补零，超过十八条时明细仅保留最早、最近各九条。历史查询仍至少两天才附图；图片累计量直接使用应用层同一查询快照的总量，不为绘图重新读取或结算。

HTMLKit 是唯一图片实现。模板以 rem 表示布局单位，由 2px 根字号统一按两倍分辨率渲染；排行榜输出 3200×1880，历史图宽 3200、高度随明细调整。昵称先按原布局字号测量换行，成图同步放大；DPI 保持 96，不通过放大已有 PNG 提高清晰度。资料查询失败退回用户 ID、头像获取失败留空；仅绘图阶段失败会保留原文字并提示“图表生成失败”，业务查询和发送异常不在此处捕获。字体发现与初始化交给 HTMLKit，本插件不生成 Fontconfig 配置、不修改共享配置或环境变量、不扫描额外字体目录。模板和包目录保持只读。

`IMPART_FONT_FAMILY` 在 Config 中默认设为 `Noto Sans CJK SC`，正文、数字及昵称测量统一使用；可以填写一个字体名称，或以英文逗号分隔多个候选，不接受字体文件路径。自定义字体缺失或配置留空时保留 Config 中的默认回退。每个字体名称分别转义为 CSS 字符串，字宽测量与最终正文使用同一套字体候选、字号和字重。插件不分发字体文件。

## 运行时数据流

1. NoneBot ORM 先完成 schema 启动检查或同步；随后插件启动时检查上游 LocalStore `nonebot_plugin_impart/impart.db`。源文件不存在、三个业务表任一非空或源库没有记录时跳过；只有目标全空且源库有数据时，才在一个目标 Session 中从同一个 SQLite 只读事务取得用户、群开关和注入记录快照并整体提交。多个 Bot 共用同一进程启动流程；不承诺多个 NoneBot 进程同时执行首次导入。
2. 所有顶层 matcher 先把 NoneBot `COMMAND_START` 作为命令前缀，再由 Alconna 解析结构化命令、子命令、Option 与 At；Uninfo 提供场景、用户、成员和角色。
3. Handler 注入 UniRef `RefContext`，在业务副作用前取得当前 UserRef/SceneRef，并通过 `build_user_ref()` 构造 Alconna At 目标；上下文本身无法建立时当前 Handler 被跳过，属性或目标构造失败则保留异常。
4. `GameApplication` 先检查场景与命令语义；PK、嗦或舔缺少目标以及 At 自己时先返回，不创建用户或执行其他副作用。PK先按发起者阶级截取前1/2/3/4个At，在选定窗口内去重且不从后续At补位；缺失参与者全部初始化并返回后，下一次调用才检查世界。有效目标与打胶、开扣、查询所涉及的缺失用户会创建默认状态；只要这些长度相关用例发生创建就返回实际 Ref，不执行冷却或结算。群友互动同样会在发起者首次创建后立即返回，但缺失目标会初始化为默认正值并继续本次互动。
5. PK 与成长从状态读取起取得 application 的共享结算锁。多人资格在锁内复核；若当前上限低于实际选定人数则整场拒绝，不裁剪，实际人数仍合法则继续；全部目标通过世界检查后才占用发起者的一次冷却并各生成一次胜负随机和基础量。互动早期初始化发起者也使用该锁；目标选择在锁外，选定后在锁内复核发起者冷却、初始化目标、批量读取双方并固定动作、流向、液体与数量档位，再记录冷却。资料查询、前置提示和两秒等待均在锁外；不会占用目标冷却。
6. 互动最终阶段按流向顺序生成一至两份数量，再生成一次耗时；重新取得同一把锁、批量读取实际接收者最新状态，按发起者→目标顺序只为当前 XNN 接收者各抽一次雌堕随机值。DataManager 的 `settle_interaction_volumes()` 只捕获一次日期，以一个事务同时提交所有人的总量与转换；任一写入失败共同回滚。开始快照不因等待期间的成长、PK 或夺舍而重解析。
7. 成长在一个事务中写回长度、胜率和阶级；PK以同一份开始快照和一次胜负写回发起者及一至四个目标；夺舍也一次写回双方。普通查询只联接当天记录，历史查询读取按日期升序排列的全部记录。bot 先发送结算，再按发起者、目标顺序独立At本轮实际通关升阶者说明已解锁能力；互动事件同样按发起者→目标追加。消息发送失败不回滚或重放已提交状态，既有冷却不因失败回滚。

## 数据和状态放在哪里

- `UserData` 以编码 `user_ref` 为主键，保存 `user_namespace` 查询投影、长度、内部胜率和当前持有的 `challenge_tier`；挑战中状态由阶级与长度推导，XNN 与正负世界也完全由长度推导，不保存展示缓存或历史最高阶。
- `SceneData` 以编码 `scene_ref` 为主键，保存 `scene_namespace`、`scene_type` 查询投影和场景开关。
- `EjaculationData` 按编码 UserRef 和日期保存透、榨或贴贴产生的无类型互动总量；`(user_ref, date)` 具有唯一约束，记录归属实际获得液体者，公开查询统一称为“注入量”。贴贴双方各累计对方输出，无额外逐次互动日志或状态字段。
- 数据库连接、Engine 和 Session 由 NoneBot ORM 管理；默认未配置时使用 `[default]` extra 提供的 SQLite，也可安装其他驱动并用 `SQLALCHEMY_DATABASE_URL` 切换默认连接。包内 generic migration 管理 schema；自动化在 SQLite 执行 migration、旧库导入和并发持久化测试，并为 PostgreSQL、MySQL 编译模型 DDL，但不连接这两种数据库做集成验证。
- 打胶、PK、目标成长和群友互动冷却保存在 `CooldownManager` 的四个 UserRef 字典中；嗦与舔共享现有 `suo_cd_data`，进程重启后清空。所有用户使用相同冷却规则，不提供超级用户豁免。
- PK、打胶、开扣、嗦、舔、夺舍和互动最终结算通过同一个 application 级锁串行访问用户游戏状态；查询的缺失用户初始化，以及排行榜的读取、人数检查与初始化也共用该锁，避免并发重复创建用户。普通或历史查询的一致快照读取、资料请求、绘图与消息发送均在锁外。多个 Bot 在同一进程共享该锁；锁和冷却一样不跨进程，数据库后端可以替换，但多进程或外部直接写库不属于并发保证。

## 当前稳定状态语义

| 持有阶级 | 正值称号 | 负值称号 |
|---|---|---|
| 一阶 | 日耀の柱 | 虛空の眼 |
| 二阶 | 贯星长枪 | 世界大穴 |
| 三阶 | 牛々の神 | 深淵の主 |

- 新用户初始长度为 `10.0`，内部胜率为 `0.5`。打胶、开扣、查询，或带有效非自身目标的嗦、舔和 PK 发现本次涉及的用户缺失时，只创建缺失者并回复，不消耗冷却或执行其他结算；缺少目标或 At 自己时不创建用户。群友互动的发起者也遵循“只创建并回复”，互动目标缺失时则创建后继续，排行榜维持自己的初始化路径。
- 挑战状态由当前持有阶级及下一阶区间推导：一阶25→30、二阶300→320、三阶1000→1050。进入时分别将当前胜率乘0.9/0.8/0.7一次，退出分别乘10/9、1.25、10/7恢复；每次只应用本次挑战系数。正负各阶试炼名统一为“登神长阶／深渊试炼”。同世界挑战者禁止自身成长、主动嗦/舔及被嗦/舔，仍可使用另一世界的目标成长命令或已解锁的夺舍。
- 进入/保级门槛包含等号，严格低于门槛才失败或掉阶；完成目标包含等号并保留超出数值。失败与掉阶朝零方向施加一次对应固定惩罚5/20/50cm，正常保留低阶，无连锁罚退。除 XNN 外，无阶/一/二/三阶的个人基础增减倍率分别为1/2/3/4；XNN 为0.5，覆盖自成长、被目标成长及PK收益和损失，只影响数值变化的接收者。固定罚退、雌堕减5cm、夺舍平分、初始长度、注入量与冷却不乘倍率。升掉阶及进出 XNN 本局仍按开始状态结算，下次使用新倍率和人数上限。达到5cm或雌堕转负均解除 XNN 减益。三阶为当前最高阶，但不是长度上限。
- `0 < length < 5` 是唯一 XNN 范围，恰好 `5cm` 属于普通正值；负值状态查询显示固定名称“小学”和绝对深度；称号按实际持有阶级呈现，不只根据绝对长度推断。XNN 当日总量超过 `200ml` 时，查询改为提示“快要变成女孩子”。PK 结算产生 `length_near_zero` 时，先发送结果及原有升阶通知，再按参与者顺序独立艾特本轮进入 XNN 的用户，提示特殊互动规则；结果正文不重复提示。持续处于 XNN 时不重复通知，查询和夺舍不补播。
- PK只使用发起者的当前有效胜率判一次胜负，所有目标同赢或同输；胜者胜率减0.01、败者加0.01，每位参与者只变一次，再处理挑战进出。发起者按实际目标数合计基础份额后应用自己的倍率，目标各用自身倍率。整场只占发起者一次冷却；所有长度、胜率与阶级同时提交或回滚。基础变化和固定惩罚分别呈现，零点锁保持在±0.001；雌堕和夺舍是显式转换入口。
- 普通男性的合法动作是透，女性是榨；XNN 对普通男性榨、对女性透。双方 XNN 优先贴贴，其他错误动作由目标选择其合法动作反制一次，不存在反制随机数。群友、管理和群主选定成员后共用该规则；贴贴不是公开命令。
- XNN 的实际透或反透为1～10ml，贴贴每方向独立1～10ml；其他动作均为1～100ml，包括女性榨 XNN。数量保留三位小数，贴贴共用一次1～20秒耗时。普通报告沿用原格式，贴贴先写双方输出、再写各自累计；两者顺序不能混用。
- 当前 XNN 接收者按包含本次数量的当日总量，以 `clamp((total - 200) / 800, 0, 1)` 独立判定雌堕，命中后长度减去 `5cm`；不超过200不触发、达到1000必定触发。风险警告仅在 `previous_total <= 200 < total` 且未转换时产生，转换覆盖本人的警告。未收量或已离开 XNN 者不抽该随机数；一人的转换不会取消另一人的收量或判定。

- 夺舍资格由负值长度及`challenge_tier >= 1`决定，没有正负各一套阶级或永久能力字段。发起者按目标半长直接转正并取得当前规则可满足的最高阶级；即使原本处于更高阶挑战，也只解除对应胜率减益，不算成功或失败且不承受固定惩罚。目标半长低于原持有阶级时只承受一次该阶固定惩罚，并按惩罚后的长度重新确定阶级。半长向上保留三位小数后再判断，因此49.999平分成25，49.998平分成24.999。
- 夺舍不因一阶而翻倍，不清空当日/历史注入量，不触发雌堕随机，也不额外播报XNN；目标称号惩罚会使双方最终长度不同。普通游戏结算仍锁住原世界，夺舍是负转正的显式入口。
- 正常通关任一阶后，应用结果将成员Ref映射到其本次取得阶级；bot先发结算，再依次独立At实际通关者，说明对应2/3/4倍基础变动及2/3/4个PK目标，负值仅一阶额外解锁夺舍。多人可在同一场取得不同阶级。重新通关可再提示；查询、启动、导入和夺舍直授不补播，发送失败不重放。掉阶保留正值“跌落神坛”、负值“被深渊拒绝了”并明确失去的旧称号，尾句沿用原文，无额外退阶倍率说明。

## 当前质量边界与维护风险

- 当前测试覆盖插件与 11 个 Alconna matcher 注册、ORM schema 与三种目标方言 DDL、SQLite migration、旧库导入、PK 与互动事务回滚、单进程并发结算、command start 与查询 grammar、XNN/零点/概率边界、首次初始化、正负成长与挑战、互动归属及关键文案、Uninfo 查询和 UniMessage 文本/图片结构；这些聚焦测试是当前 OneBot V11 验收边界，不计划增加 Adapter 事件级 fixture。
- 英文根命令 alias `impart` 只接受小写；排行榜自身的 `rank` 正则仍保持大小写不敏感。上游 `IMPART帮助` 等大小写变体不再作为兼容入口。
- `bot/handlers/` 已按 `game`、`interaction`、`possession`、`query`、`records`、`control` 拆分；普通查询和历史查询共享一个 Handler，`records.py` 只负责排行榜。群友、管理、群主共享互动 Handler，打胶与开扣共享成长 Handler。
- `get_jj_length()` 和 `get_win_probability()` 使用真假值回退默认值，持久化的精确 `0` 与“没有查询结果”不能被区分。
- 用户文案与底层字段均保留“胜率”语义；当前 PK 仅使用发起者的有效胜率判定，XNN 在本局开始时将存储胜率乘0.5，被攻击者的胜率不参与判定。普通与历史查询从同一 SQL 快照取得长度和存储胜率，再按当前形态计算有效值；PK 播报按结算后形态计算，均显示百分比（最多三位小数）。存储胜率保留每局±0.01与已生效的挑战减益；进出 XNN 不修改存储值、不重置冷却，达到5cm或雌堕转负后直接恢复当前存储胜率。双方胜率归一化延后为独立玩法改动。
- UniRef 0.4 的 QQAPI 群成员和频道用户使用复合完整 `UserRef.id`；排行榜当前不能据此可靠查询 Uninfo 用户资料，查询失败时退回 Ref ID 展示，不拆解上游私有格式，等待 UniRef 提供 Ref 到资料的公开查询入口。
- Discord 的群主身份不能从普通角色权限可靠推导；Uninfo 0.11.1 的 `OWNER` 映射尚不足以证明真实 Guild owner。该限制仅作为理论兼容边界记录，不是当前发布闸门，本插件也不添加 Discord 专用查询分支。
- 旧库导入只识别 `nonebot_plugin_impart` 在当前 LocalStore 配置下的标准 `impart.db`，不提供手工路径、合并、覆盖或反向同步；源库缺少必要表或基础列时启动失败，后加的挑战列缺失时使用上游默认值，派生展示列会被忽略，零长度统一导入为 `-0.001`。
- 上游首次导入按已启用的完成目标赋阶，并处理所处挑战区间的系数。旧一阶挑战标记对应原0.8，必要时先乘1.25解除旧减益，再应用新系数；例如26cm旧挑战胜率0.4规范为0.45，310cm无旧挑战胜率0.5规范为二阶挑战胜率0.4。实际系数相同直接保留。导入授阶依据完成目标30/320/1050，夺舍直授依据保级门槛25/300/1000，两者有意不同。导入不补罚长度，两种直授都不补发通关通知；夺舍目标掉阶仍受对应固定惩罚。
