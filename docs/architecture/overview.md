# 项目架构

## 先建立一个印象

`nonebot_plugin_impart_plus` 是面向 NoneBot2 与 OneBot V11 群聊的互动游戏插件。管理员先为群聊开启功能，群成员再通过命令创建和改变长度、进行 PK、与群友互动，以及查询排行榜和注入记录。

当前 `feature` 实现以少量模块直接协作为主：插件入口注册 matcher 和定时任务，`Impart` 集中编排全部命令，数据库模块同时保存 ORM 模型、数据访问和挑战状态规则。这里记录的是当前代码事实，不把 `main` 分支的分层结构或新增玩法视为既定目标。

## 核心能力与公开入口

插件当前对外承诺的是 NoneBot 命令、配置项和已有 SQLite 数据，不提供独立的 Python 业务 API 稳定性承诺。

| 核心能力或公开入口 | 对外含义 | 关键状态或副作用 | 主要实现位置 |
|---|---|---|---|
| 群开关与帮助 | 管理员、群主或超级用户开启和关闭群内玩法；成员查看命令说明 | 持久化群级 `allow` 状态 | [`__init__.py`](../../src/nonebot_plugin_impart_plus/__init__.py)、[`handle.py`](../../src/nonebot_plugin_impart_plus/handle.py) |
| 长度成长与查询 | `打胶/开导` 增加本人长度，`嗦牛子/嗦/suo` 增加本人或被 `@` 用户长度，`查询` 显示长度状态 | 创建或更新用户、记录冷却和最后活动时间、评估挑战状态 | [`handle.py`](../../src/nonebot_plugin_impart_plus/handle.py)、[`data_sheet.py`](../../src/nonebot_plugin_impart_plus/data_sheet.py) |
| PK 与登神挑战 | `pk/对决` 需要 `@` 对手；按发起者战力判定胜负，并调整双方长度和内部胜率值 | 多次独立写入双方状态；跨越 25、30、5、1、0 等边界时组合状态文案 | [`handle.py`](../../src/nonebot_plugin_impart_plus/handle.py)、[`data_sheet.py`](../../src/nonebot_plugin_impart_plus/data_sheet.py) |
| 群友互动 | `日/透群友`、`日/透群主`、`日/透管理` 选择目标并记录注入量 | 读取群成员角色与白名单；xnn 或非正长度发起者可能被反透；调用外部 QQ 头像地址 | [`handle.py`](../../src/nonebot_plugin_impart_plus/handle.py) |
| 排行榜与注入查询 | 显示长度前五、后五和本人排名；查询当天或历史注入量 | 读取 SQLite，使用 Pillow 和内置字体生成 PNG | [`handle.py`](../../src/nonebot_plugin_impart_plus/handle.py)、[`draw_img.py`](../../src/nonebot_plugin_impart_plus/draw_img.py) |
| `Config` | 配置帮助文案、四类冷却、白名单、不活跃惩罚和长度别名 | 配置实例还持有进程内冷却字典；运行中不热重载 | [`config.py`](../../src/nonebot_plugin_impart_plus/config.py) |

## 逻辑组件与实现映射

| 逻辑组件 | 当前职责 | 主要协作与边界 | 拥有的数据或状态 | 主要实现位置 |
|---|---|---|---|---|
| 插件入口与生命周期 | 声明插件元数据、注册 matcher、在启动时初始化数据库、注册每日任务 | 把 matcher 直接绑定到 `Impart` 方法 | 无长期业务状态 | [`__init__.py`](../../src/nonebot_plugin_impart_plus/__init__.py) |
| 配置与运行时工具 | 解析 `@`、生成随机增量、执行冷却检查并读取配置 | 被所有命令直接调用；配置与可变运行时状态尚未分离 | 四个冷却字典和配置值 | [`config.py`](../../src/nonebot_plugin_impart_plus/config.py) |
| 命令编排 | 完成权限和群开关检查、目标选择、业务分支、数据库调用与回复文案 | 同时依赖 NoneBot、配置、数据访问和图表；当前没有 handler 级模块边界 | 单次事件上下文；模块级白名单和机器人昵称 | [`handle.py`](../../src/nonebot_plugin_impart_plus/handle.py) |
| 持久化与状态规则 | 定义三张 ORM 表、初始化和兼容旧字段、执行 CRUD、评估挑战与长度状态 | 业务规则与 SQLAlchemy 会话位于同一模块；各 helper 自行提交事务 | 用户、群开关和注入记录 | [`data_sheet.py`](../../src/nonebot_plugin_impart_plus/data_sheet.py) |
| 图表渲染 | 用 Pillow 绘制排行榜柱状图和注入历史折线图 | 读取包内字体，向命令层返回 PNG 字节 | 无持久状态；`DrawBarChart` 实例持有调色板和字体路径 | [`draw_img.py`](../../src/nonebot_plugin_impart_plus/draw_img.py) |

当前主要依赖方向是 `__init__ → handle → config/data_sheet/draw_img`。`data_sheet.py` 内部同时包含模型、规则和存储操作，所以目前不存在独立领域层或数据服务边界。

## 数据和状态放在哪里

- `UserData` 保存 `userid`、长度 `jj_length`、最后活动时间、内部胜率 `win_probability`，以及挑战、xnn 临界区和非正长度标记。
- `GroupData` 保存群聊是否允许使用插件。
- `EjaculationData` 按用户和日期保存注入量；同一天的记录累加到同一数值。
- SQLite 文件位于 `nonebot-plugin-localstore` 提供的插件数据目录，文件名为 `impart.db`。启动时建表，并为旧 `userdata` 表补充缺失字段。
- 打胶、PK、嗦和群友互动冷却保存在 `Config` 实例的四个字典中，进程重启后清空；只有群友互动冷却明确允许超级用户绕过。
- 每日零点任务调用不活跃惩罚；开启惩罚时，各主要命令也会在处理前执行同一检查。

## 当前稳定状态语义

- 新用户初始长度为 `10.0`，内部胜率为 `0.5`。
- `25 <= length < 30` 会进入登神挑战并把内部胜率乘以 `0.8`；挑战期间禁止打胶和嗦。
- 挑战中跌到 `length < 25` 会退出挑战、恢复内部胜率系数并额外减少 5；达到 `length >= 30` 会完成挑战。
- `0 < length <= 5` 被标记为 xnn 临界区，`length <= 0` 显示为女孩子状态；当前没有与负长度对应的独立成长、PK 或群友互动命令体系。
- PK 只使用发起者自身的内部胜率判定胜负；胜者内部胜率减 `0.01`，败者增加 `0.01`。双方长度和胜率通过多次独立数据库提交更新。
- xnn 发起群友互动时有 50% 概率被反透，非正长度发起者必定成为被注入方；注入记录本身不会改变长度。

## 运行与外部依赖

- Python 支持下限为 3.11，适配器边界固定为 OneBot V11。
- SQLite 使用 SQLAlchemy async 与 `aiosqlite`，数据目录由 `nonebot-plugin-localstore` 提供。
- 定时任务由 `nonebot-plugin-apscheduler` 注册。
- 图表使用 Pillow 和包内 `SIMYOU.TTF`，不依赖浏览器环境。
- 群友互动结果引用 `q1.qlogo.cn` 的 QQ 头像；网络不可用时消息中的远程图片可能无法显示。

## 当前质量边界与维护风险

- 现有测试只验证插件可加载、配置默认值和测试事件构造，没有锁定命令行为、状态边界或数据库写入语义。
- `handle.py` 同时承担命令校验、业务规则、数据编排和文案，局部修改容易影响多个玩法。
- PK 和挑战结算由多个 helper 分别提交；中途异常可能留下双方状态只更新一部分的结果。
- `get_jj_length()` 和 `get_win_probability()` 使用真假值回退默认值，持久化的精确 `0` 与“没有查询结果”不能被区分。
- 用户文案已使用“战力”，内部字段和计算仍沿用 `win_probability`；后续设计需要明确战力是展示名称还是新的数值语义。
- 当前数据库已有兼容旧表的启动逻辑。任何模型或状态语义调整都应先明确已有 `impart.db` 的兼容边界。
