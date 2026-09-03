# PLAN-0004：统一正负目标成长与目标选择

| 状态 | 完成时间 |
|---|---|
| 已完成 | 2026-09-03 |

## 问题与最终结果

原“嗦”会对任意目标累加正数，无 At 时默认作用于自己，也无法为负值目标提供对称的深度成长；PK 则要求恰好一个 At，无法在群开关检查后统一提示缺少目标。

现在目标成长由一个 Alconna matcher 和 Handler 处理：`嗦` 只增加其他正值用户的长度，`舔` 只增加其他非正值用户的深度。两种模式都必须 At 其他用户，允许多个 At 但严格只使用第一个，共享现有 `suo_*` 冷却，并在缺少目标或 At 自己时于用户初始化前结束。PK 使用相同的 At 选择规则；缺少目标时在场景检查后提示，PK 结算本身没有改变。

## 关键改动

| 模块或路径 | 最终改动 |
|---|---|
| `bot/matchers.py` | 自我成长与目标成长均使用 Bracket Header 捕获 `action`，由 Handler 共用的转换函数映射为 `GrowthMode`；目标成长只识别 `嗦/舔`，移除 `嗦牛子/舔小学/suo` 且不增加 `tian`。目标成长与 PK 都使用可选 `MultiVar(At)` |
| `impart/app.py` | 为 PK 和目标成长增加缺少目标 outcome；目标成长增加自目标与正负世界门禁，深度模式写入负增量并跳过挑战，正负模式共享原嗦冷却 |
| `bot/handlers/game.py` | 合并嗦与舔 Handler，按类型化 outcome 输出缺目标、自目标、世界不符、冷却和完成文案；PK 只构造首个 At 的 Ref |
| `README.md`、插件元数据与 `docs/architecture/overview.md` | 同步两个目标成长命令、目标必填、PK 多 At、共享冷却、正负目标成长语义，以及所有顶层命令遵循 `COMMAND_START` 的统一策略 |

Alconna 1.8.44 的字典型命令头与 `use_cmd_start=True` 组合后无法解析，因此自我成长与目标成长统一使用 Alconna 原生 Bracket Header 捕获 `action`，再由共享函数映射为 `GrowthMode`。所有顶层 matcher 都显式启用 command start，前缀只取自 NoneBot `COMMAND_START`；Handler 不读取原始消息，也没有为成长命令引入 shortcut。

## 验证结果

| 成功标准 | 证据或结果 |
|---|---|
| 两个目标成长命令、command start 和严格 grammar | 聚合 parser 测试覆盖 `嗦/舔`、无空格 At、`/舔`、多个 At 的顺序、移除的 `嗦牛子/舔小学/suo/tian` 与尾随文本 |
| 全部顶层命令遵循 command start | parser 测试分别覆盖 PK、自我成长、目标成长、排行榜、互动、银趴控制/查询/帮助和注入查询的带前缀形式；alias 与 compact 语义保持有效 |
| 缺目标、自目标和首次初始化无额外副作用 | application 与 Handler 测试确认对应 outcome、回复、用户创建和冷却边界 |
| 正负世界、增量方向、共享冷却与挑战边界 | application 测试确认错误模式不消费结算随机或冷却，舔写负增量且不调用挑战，嗦与舔按发起者共享冷却，正值嗦仍调用既有挑战路径 |
| PK 与目标成长使用相同 At 选择规则 | parser、Handler 与 application 测试确认缺目标提示、多 At 顺序和只使用第一个目标 |
| 项目质量门 | `pytest` 88 项通过；Ruff lint 与格式检查通过；BasedPyright 0 错误；sdist 与 wheel 构建成功；`git diff --check` 通过 |

## 已知缺口与后续事项

- PK 与目标成长都只检查第一个 At；它不是用户 At 时命令无效，不向后寻找。
- 第一阶段不增加负值挑战或负值 PK 规则，其他 Adapter 仍只维持理论兼容边界。

## 相关文档

- [当前项目架构](../../architecture/overview.md)
- [负值状态自我成长](PLAN-0003-negative-self-growth.md)
