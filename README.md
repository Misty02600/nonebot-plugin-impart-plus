<div align="center">

## ✨ nonebot_plugin_impart_plus ✨
[![LICENSE](https://img.shields.io/github/license/Misty02600/nonebot_plugin_impart_plus.svg)](./LICENSE)
[![python](https://img.shields.io/badge/python-3.11+-blue.svg?logo=python&logoColor=white)](https://www.python.org)
![Adapters](https://img.shields.io/badge/Adapters-OneBot%20v11-blue)
<br/>

[![uv](https://img.shields.io/badge/package%20manager-uv-black?logo=uv)](https://github.com/astral-sh/uv)
[![ruff](https://img.shields.io/badge/code%20style-ruff-black?logo=ruff)](https://github.com/astral-sh/ruff)

</div>

本项目的 Just recipes 需要 Just 1.56 或更高版本；Windows 下还需要 PowerShell 7，并通过 `pwsh` 命令调用。直接运行对应的 `uv`、`gh` 等命令不受 PowerShell 要求影响。

## 🛠️ 开发与模板更新

- `just sync`：同步全部开发依赖组。
- `just lint`：只检查 Ruff lint 和格式，不修改文件；`just format` 才会应用修复和格式化。
- `just test`、`just check`：运行 pytest 和 BasedPyright。
- `just update-hooks`：更新 prek hook revisions，并保留七天 cooldown。
- `just update-template`：只在干净工作树中运行 Copier 更新，并自动进入完整收尾验证。
- `just finish-template-update`：解决 Copier 冲突或接管 Renovate PR 后，检查 `.rej`、刷新本地 lock，并重跑 hooks 与全部质量检查。

Hosted Renovate 仍是常规模板升级入口。手工命令用于本地复现、冲突处理和恢复，不要编辑 `.copier-answers.yml` 或手工指定模板版本。

## 🚀 发布

待发布的源码通过 CI 后，在 `main` 分支运行 `just bump`。Commitizen 会创建版本提交和 annotated tag，Just 会将当前提交及其可达的 annotated tags 整体原子推送到 `origin`，由版本 tag 触发远端 release workflow。

## 📖 介绍

`nonebot_plugin_impart_plus` 是面向 NoneBot2 与 OneBot V11 的群聊互动插件，
围绕群内数值成长、PK、状态挑战和群友互动提供完整玩法。

当前版本包含以下玩法：

- PK 胜率与登神挑战；
- 长度状态检测，以及 xnn、女孩子等状态文案；
- “透群友”与长度状态联动产生的反透；
- 群友、群主和管理目标选择；
- 长度排行榜、每日及历史注入量查询；
- 对旧版 `impart.db` 数据表的增量字段兼容。

## 💿 安装

<details open>
<summary>使用 nb-cli 安装</summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

    nb plugin install nonebot_plugin_impart_plus --upgrade
使用 **pypi** 源安装

    nb plugin install nonebot_plugin_impart_plus --upgrade -i "https://pypi.org/simple"
使用**清华源**安装

    nb plugin install nonebot_plugin_impart_plus --upgrade -i "https://pypi.tuna.tsinghua.edu.cn/simple"


</details>

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

<details open>
<summary>uv</summary>

    uv add nonebot_plugin_impart_plus
安装仓库 main 分支

    uv add git+https://github.com/Misty02600/nonebot_plugin_impart_plus@main
</details>

<details>
<summary>pdm</summary>

    pdm add nonebot_plugin_impart_plus
安装仓库 main 分支

    pdm add git+https://github.com/Misty02600/nonebot_plugin_impart_plus@main
</details>
<details>
<summary>poetry</summary>

    poetry add nonebot_plugin_impart_plus
安装仓库 main 分支

    poetry add git+https://github.com/Misty02600/nonebot_plugin_impart_plus@main
</details>

打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分追加写入

    plugins = ["nonebot_plugin_impart_plus"]

</details>

<details>
<summary>使用 nbr 安装(使用 uv 管理依赖可用)</summary>

[nbr](https://github.com/fllesser/nbr) 是一个基于 uv 的 nb-cli，可以方便地管理 nonebot2

    nbr plugin install nonebot_plugin_impart_plus
使用 **pypi** 源安装

    nbr plugin install nonebot_plugin_impart_plus -i "https://pypi.org/simple"
使用**清华源**安装

    nbr plugin install nonebot_plugin_impart_plus -i "https://pypi.tuna.tsinghua.edu.cn/simple"

</details>

## 🗃️ 沿用已有数据库

插件通过 `nonebot-plugin-localstore` 保存 `impart.db`。如需沿用旧版
`nonebot_plugin_impart` 或 `nonebot_plugin_impact` 的数据：

1. 停止 NoneBot；
2. 找到原插件的 `impart.db`，旧 `impact.db` 需先重命名；
3. 使用 `nb localstore` 确认当前插件数据目录；
4. 将数据库复制到 `nonebot_plugin_impart_plus` 的数据目录后再启动 NoneBot。

操作前请备份数据库；插件启动时会为旧表补充缺失字段。


## ⚙️ 配置

| 配置项 | 默认值 | 说明 |
|:--|:--|:--|
| `DJ_CD_TIME` | `300` | 打胶冷却时间（秒） |
| `PK_CD_TIME` | `60` | PK 冷却时间（秒） |
| `SUO_CD_TIME` | `300` | 嗦牛子冷却时间（秒） |
| `FUCK_CD_TIME` | `3600` | 透群友冷却时间（秒） |
| `ISALIVE` | `False` | 是否启用不活跃惩罚 |

## 🎉 使用

使用 `银趴帮助` 或 `impart帮助` 查看插件内置指令说明。

| 指令 | 权限 | 目标 | 说明 |
|:--|:--|:--|:--|
| `开启银趴`、`禁止银趴` | 管理员、群主或超级用户 | 当前群 | 开启或关闭群内玩法 |
| `日/透群友`、`日/透群主`、`日/透管理` | 群成员 | 群友、群主或管理 | 随机选择或通过 `@` 指定群友 |
| `pk`、`对决` | 群成员 | 需要 `@` 对手 | 根据双方胜率结算长度变化 |
| `打胶`、`开导` | 群成员 | 自己 | 增加自己的长度 |
| `嗦牛子`、`嗦`、`suo` | 群成员 | 自己或 `@` 用户 | 增加目标长度 |
| `查询` | 群成员 | 自己或 `@` 用户 | 查询长度和当前状态 |
| `jj排行榜`、`jj排名`、`jj榜单`、`jjrank` | 群成员 | 全部用户 | 显示前五、后五及自己的排名 |
| `注入查询`、`摄入查询`、`射入查询` | 群成员 | 自己或 `@` 用户 | 查询当天注入量；附加“历史”或“全部”可查询累计记录 |

## ✨ 特别感谢

- [`Special-Week/nonebot_plugin_impact`](https://github.com/Special-Week/nonebot_plugin_impact) 提供原始创意与代码基础。
