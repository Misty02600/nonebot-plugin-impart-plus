# PLAN-0014：实现夺舍与试炼能力提示

| 状态 | 完成时间 |
|---|---|
| 已完成 | 2026-09-05 |

## 问题与最终结果

完成深渊试炼的负值用户现在可以使用 `夺舍 @用户` 转回正值世界。只取首个At，无别名；正值用户或未完成者统一提示未解锁。目标必须为正值、未在挑战，且长度严格小于发起者深度。自目标不设特例，自然按负值目标拒绝；首次涉及的缺失用户沿用只创建并提示的规则。

目标原长度按整数千分位平分并向上保留三位小数，双方取得相同基础半长。发起者直接写入 `length=half, is_challenging=False, challenge_completed=(half >= 25)`；低于25不承受旧称号惩罚，达到25直接取得正值称号。目标半长达到25直接持有称号，低于25且原本持有完成标记时沿用额外减5cm及零点保护。

正负世界共用已有完成标记，不保存永久能力。夺舍不修改胜率、互动记录或冷却，不生成结算随机数，不额外播报XNN。后续普通PK继续适用原有挑战规则。整个夺舍在现有共享锁内，以一个数据库事务提交双方状态。

## 关键改动

| 位置 | 最终改动 |
|---|---|
| `impart/core.py::resolve_possession()` | 纯检查与结算，区分明确拒绝和完整双方结果；发起者直接决定新完成状态，仅目标调用既有称号后处理 |
| `infra/data_manager.py::settle_possession()`、`impart/app.py::execute_possession()` | 场景及初始化检查、共享状态锁、双方完整状态读取与原子保存；拒绝不写回 |
| `bot/matchers.py`、`bot/handlers/possession.py` | Alconna命令、全局前缀、首At处理及用户确认的成功/失败文案；无吸阳alias |
| `impart/core.py::classify_length()`、`get_user_query_data()` | 同一查询快照包含完成标记，正负25～30cm已完成者能正确显示称号 |
| `StateEvaluation`、`PkOutcome`、`GrowthOutcome` | 本次结果携带首次完成/获能力成员信息，均为瞬时结果而非数据库新字段 |
| `bot/handlers/game.py::_finish_game_reply()` | 正常回复在前，独立真实At解锁通知在后，最后结束matcher；涵盖PK本人/对手和成长刷新 |
| `bot/handlers/shared.py::OPPONENT_TITLE_LOSS` | PK和夺舍复用原有正值对手跌落文案；夺舍只替换起因并固定同条昵称 |
| 插件帮助、README、架构 | 同步命令说明、资格、事务、称号及通知边界 |

## 文案与行为约束

- 成功回复使用用户确认的两行原文，见 `bot/handlers/possession.py`，先展示惩罚前半长；目标失去称号的额外5cm随后追加说明，所以双方最终长度不保证相同。
- 未解锁提示为「你尚未解锁此禁忌之术...」，目标挑战提示为「一股神秘的力量庇护着TA，你的夺舍之术被无效化了...」。
- 首次完成深渊试炼的成员收到独立消息：真实At后接「你感到深渊的禁忌力量正涌入体内...\n现在可以使用指令「夺舍」了！」。已有称号持续检查、查询和启动不补发。
- 「25以上」包含25；49.999cm平分为25，49.998cm平分为24.999。允许奇数千分位产生0.001cm总量增量，0.001cm目标不额外拒绝。
- 发送失败不撤销已提交状态，不保存或重放通知；数据库事务失败则双方共同回滚。
- 不增加schema、依赖、成功率、额外冷却或多进程协调。OneBot V11优先；PostgreSQL/MySQL保持标准ORM路径及DDL编译边界，未宣称真实后端集成验证。

## 验证结果

- 159项pytest通过：覆盖舍入和称号边界、检查顺序、首At与无alias、初始化、双方持久化与回滚、重复夺舍和目标成长交错、独立At通知及称号快照。
- Ruff lint/format、BasedPyright、`uv lock --check`、`uv build`、`git diff --check`通过。pytest仅保留既有两项Alembic配置弃用警告。
- PLAN-0013及其工作内容未改动，本计划不依赖HTML渲染；后续图表工作应保留新增完成标记的查询快照。

## 相关文档

- [当前架构](../../architecture/overview.md)
- [PLAN-0010：XNN转换与合并查询](PLAN-0010-xnn-feminization.md)
- [PLAN-0012：PK原子结算](PLAN-0012-atomic-pk-settlement.md)
