# 核心游戏状态流

## 这条流程保证什么

核心玩法围绕一个带符号的长度值运行。正负号决定玩家所属世界，绝对值决定挑战进度；命令层只负责校验、上下文解析和回复，状态计算集中在领域规则，持久化更新集中在 `DataManager`。

## 世界与边界语义

| 条件 | 语义 |
|---|---|
| `length > 0` | 正值世界 |
| `length <= 0` | 负值世界，零归负值 |
| `0 < length <= 5` | xnn 区间 |

写入结果恰好为 `0` 时，数据层使用 `-0.01` 代替。正值 PK 中，原本处于 xnn 的败者不会跌破 `0.01`；负值 PK 的败者不会因结算翻到正值，越界时钳到 `-0.01`。

实现依据：[`core/world.py`](../../../src/nonebot_plugin_impart_plus/core/world.py)、[`infra/data_manager.py`](../../../src/nonebot_plugin_impart_plus/infra/data_manager.py)、[`core/rules.py`](../../../src/nonebot_plugin_impart_plus/core/rules.py)。

## 一次命令的稳定顺序

1. matcher 接收 OneBot V11 群事件，先检查群开关。
2. 依赖注入解析发起者、目标和世界状态；无效目标、自己作为 PK 对手或跨世界组合在执行前结束。
3. 检查命令所属冷却。PK、嗦/舔、透/榨在其他校验成功后才记录冷却；打胶/开扣在冷却检查后立即记录。
4. handler 调用纯规则计算增量、胜率或事件结果，再由 `DataManager` 写入 SQLite。
5. 长度变化后评估挑战、xnn 和跨零状态，最后根据状态结果组合回复。

PK 和透/榨使用 `handlers=[]` 形成 guard 到 execute 的有序 pipeline；共享上下文通过 NoneBot `Depends` 在同一事件处理中缓存。

## 挑战状态变化

挑战统一使用 `abs(length)` 比较正负两个世界的量级：

| 当前条件 | 状态变化 |
|---|---|
| 未挑战且 `25 <= abs(length) < 30` | 进入挑战，胜率乘 `0.8` |
| 挑战中且 `abs(length) >= 30` | 挑战成功，退出挑战并恢复胜率系数 `1.25` |
| 挑战中且 `abs(length) < 25` | 挑战失败，退出挑战、恢复胜率，并向零方向惩罚 5 |
| 已完成后跌到 `abs(length) < 25` | 取消完成标记，并向零方向惩罚 5 |

挑战判定由纯函数 [`evaluate_challenge`](../../../src/nonebot_plugin_impart_plus/core/game.py) 返回更新描述，数据层负责在独立写入或 PK 事务内应用这些变化。

## PK 结算

1. 双方必须存在且属于同一世界。
2. 正值世界会先把每个 xnn 玩家本局的有效胜率乘 `0.5`；负值世界没有该修正。
3. 发起者获胜概率为 `Wa / (Wa + Wb)`；双方有效胜率都为零时回退到 `0.5`。
4. 弱方获胜时使用 `max(1, loser_w / winner_w)` 放大赢家收益；赢家收益还乘配置项 `pk_rake_ratio`。
5. 正值 xnn 败者损失乘 `1.5`；负值世界按深度方向反向写入。
6. 胜者基础胜率下降、败者基础胜率上升；向 0 或 1 边界移动时使用 `4w(1-w)` 阻尼，向 0.5 移动时使用完整的 `pk_win_rate_k`。
7. `DataManager.execute_pk` 在同一事务中更新双方长度、胜率和挑战状态。

本局 xnn 修正只影响胜负判定，不写回基础胜率。实现依据：[`core/rules.py`](../../../src/nonebot_plugin_impart_plus/core/rules.py) 与 [`bot/handlers/pk.py`](../../../src/nonebot_plugin_impart_plus/bot/handlers/pk.py)。

## 注入与雌堕

`日/透` 只允许正值玩家，`榨` 只允许负值玩家且目标必须处于正值世界。群友命令可以读取 `@` 目标，群主和管理命令按成员角色选择目标。

正值分支会根据发起者和目标是否处于 xnn 决定实际被注入者；每个实际被注入者随后执行雌堕检查。当目标仍处于 xnn 且当日累计注入量达到 `500 ml` 时，新长度按 `current - 5` 计算，并继续遵守零值保护。负值“榨”分支记录目标注入量，但不执行雌堕检查。

实现依据：[`bot/handlers/yinpa.py`](../../../src/nonebot_plugin_impart_plus/bot/handlers/yinpa.py) 与 [`core/rules.py`](../../../src/nonebot_plugin_impart_plus/core/rules.py)。

## 失败与重启语义

- guard 失败通过 `matcher.finish()` 结束当前命令；在“校验后记录冷却”的命令中不会消耗冷却。
- SQLite 状态跨重启保留，启动时会补齐旧表缺少的状态列。
- 冷却使用内存时间戳，进程重启后不会恢复。
- 图表生成需要浏览器渲染；该外部能力失败不改变已经持久化的游戏数据。
