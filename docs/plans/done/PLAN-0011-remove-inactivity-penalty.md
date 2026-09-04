# PLAN-0011：移除不活跃惩罚机制

| 状态 | 完成时间 |
|---|---|
| 已完成 | 2026-09-04 |

## 问题与最终结果

上游插件的不活跃惩罚会在用户超过一天未活动且长度大于 `1cm` 时随机扣减长度，并由普通命令与每日定时任务重复触发。该默认关闭的单边玩法现已完整移除：任何命令都不会再扫描或随机修改其他用户，也不再保存仅为惩罚服务的活动时间。

## 关键改动

| 模块或路径 | 最终改动 |
|---|---|
| `config.py`、`impart/app.py`、`bot/dependencies.py` | 删除 `isalive`、`penalties_enabled`、惩罚用例及全部调用点；应用用例继续保持原有初始化、世界、冷却、随机与结算顺序 |
| `bot/__init__.py`、`pyproject.toml` | 删除每日任务和 APScheduler 依赖；插件生命周期只保留 ORM 后的上游数据导入回调 |
| `infra/database.py`、`infra/data_manager.py`、初始 migration | 删除 `last_masturbation_time`、活动更新时间和全表惩罚；三个业务表及其其他字段和约束保持不变 |
| `infra/legacy_import.py` | 上游用户表只要求 `userid` 与 `jj_length`；源库是否带活动时间列都能导入，其余业务数据边界不变 |
| README、架构文档与测试 | 删除公开配置和当前架构中的不活跃机制说明；测试聚焦验证字段消失、旧库兼容读取及既有玩法回归 |

## 验证结果

| 成功标准 | 证据或结果 |
|---|---|
| 运行时与依赖 | 项目环境同步后移除 `nonebot-plugin-apscheduler`、`apscheduler` 与孤立的 `tzlocal`；NoneBot 仍可正常加载插件 |
| ORM 生命周期 | 临时 SQLite 通过 `upgrade → check → downgrade → upgrade → check`；用户表确认不含活动时间，三个业务表均存在 |
| 上游导入 | 源用户表缺少活动时间仍可导入；完整旧库中原有活动时间被忽略，长度、胜率、状态、群开关和注入记录保持原规则 |
| 回归与质量 | 131 项 pytest、Ruff lint/format、BasedPyright、lock、build 与 `git diff --check` 全部通过 |

## 边界与后续

- 不新增替代惩罚、定时任务、最后活动查询或兼容配置；遗留的 `ISALIVE` 环境变量由配置模型忽略。
- 插件尚未发布到市场，本次直接修改 v1 初始 migration；已经运行旧开发 schema 的本地数据库不提供升级兼容。
- [PLAN-0010](../todo/PLAN-0010-xnn-feminization.md) 可在没有隐式全局扣减和额外随机消费的基础上实现 XNN 雌堕。

## 相关文档

- [当前项目架构](../../architecture/overview.md)
- [PLAN-0009：导入上游插件数据](PLAN-0009-import-upstream-data.md)
- [PLAN-0010：实现 XNN 概率雌堕并合并查询](../todo/PLAN-0010-xnn-feminization.md)
