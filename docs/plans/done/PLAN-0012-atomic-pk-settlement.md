# PLAN-0012：让 PK 结算原子提交

| 状态 | 完成时间 |
|---|---|
| 已完成 | 2026-09-04 |

## 问题与最终结果

PK 原先分别提交双方胜率、长度和挑战状态，中途异常会留下半局结果，不同发起者同时选择同一目标时也可能覆盖状态。现在 core 一次计算双方完整结果，DataManager 在一个标准 SQLAlchemy 事务中写回双方；任何 flush 或 commit 失败都会整体回滚。

`GameApplication` 同时拥有一把短时状态结算锁。PK、打胶、开扣、嗦和舔从用户状态读取到写入完成共用该锁，因此单个 NoneBot 进程中的多个 Bot 和并发事件按顺序观察已提交状态。

## 关键改动

| 模块或路径 | 最终改动 |
|---|---|
| `impart/core.py` | 新增完整 PK 纯结算，保留双方结算前、基础变化后和挑战处理后的状态，以及模式、胜负结果和状态事件 |
| `infra/data_manager.py` | 复用模型与领域状态映射，在一个 `AsyncSession` 事务中读取、计算、flush 并提交双方最终状态 |
| `impart/app.py` | PK 改为一次数据结算并继续返回原 `PkOutcome`；新增 application 级 `asyncio.Lock`，PK 与两个成长用例共用 |
| Handler | 无需修改；既有正负 PK、挑战和胜率文案继续消费相同 outcome 字段 |
| 架构与测试 | 记录事务和单进程锁所有权；新增且仅新增纯结算顺序、事务回滚、共享目标串行化三项聚焦测试 |

## 验证结果

| 成功标准 | 证据或结果 |
|---|---|
| 行为保真 | 既有正负 PK、世界门禁、挑战状态、冷却、随机次数和 Handler 文案测试原样通过 |
| 原子回滚 | 在双方状态 flush 后注入异常，数据库中的双方长度与胜率全部保持结算前值 |
| 单进程并发 | 两个不同发起者同时 PK 同一目标时，第二局等待第一局提交，最终状态等价于串行执行且两局均保留 |
| 后端边界 | 业务实现只使用 `asyncio.Lock`、`AsyncSession` 和普通 ORM 事务，不包含 SQLite/PostgreSQL/MySQL 方言分支；现有三方言 DDL 编译继续通过 |
| 全量质量 | 134 项 pytest、Ruff lint/format、BasedPyright、lock、build 与 `git diff --check` 全部通过 |

## 已知边界与后续

- 并发保证只覆盖同一个 `GameApplication` 所在的 NoneBot 进程；不协调多个进程、外部脚本或直接数据库写入。
- SQLite 是实际数据库测试后端；PostgreSQL 和 MySQL 当前只保持标准 SQLAlchemy 路径及方言编译边界，不宣称真实集成验证。
- 状态锁会让不同群的 PK 与成长在短暂数据库临界区内串行；不包含 Handler 回复、图片处理或互动等待。没有真实吞吐瓶颈前不增加按用户分片锁。
- 数据库失败时双方状态回滚，但已经记录的进程内冷却不撤销。
- 本轮未改变零点、XNN、胜率和玩法；后续 [PLAN-0010](PLAN-0010-xnn-feminization.md) 已扩展该结算结果，并让雌堕复用同一把锁。

## 相关文档

- [当前项目架构](../../architecture/overview.md)
- [PLAN-0010：实现 XNN 概率雌堕并合并查询](PLAN-0010-xnn-feminization.md)
- [PLAN-0005：让 PK 按正负世界结算](PLAN-0005-same-world-pk.md)
- [PLAN-0006：为负值世界补齐挑战](PLAN-0006-negative-challenge.md)
