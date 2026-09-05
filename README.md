<div align="center">

## ✨ nonebot_plugin_impart_plus ✨
[![LICENSE](https://img.shields.io/github/license/Misty02600/nonebot_plugin_impart_plus.svg)](./LICENSE)
[![python](https://img.shields.io/badge/python-3.11+-blue.svg?logo=python&logoColor=white)](https://www.python.org)
![Adapters](https://img.shields.io/badge/Adapters-OneBot%20v11-blue)
<br/>

[![uv](https://img.shields.io/badge/package%20manager-uv-black?logo=uv)](https://github.com/astral-sh/uv)
[![ruff](https://img.shields.io/badge/code%20style-ruff-black?logo=ruff)](https://github.com/astral-sh/ruff)

</div>

## 📖 介绍

`nonebot_plugin_impart_plus` 是面向 NoneBot2 群聊场景的互动插件，围绕群内数值成长、PK、状态挑战和群友互动提供完整玩法

当前优先保证 OneBot V11 的实际实现与回归验收；其他 Adapter 仅保持通用接入设计，不提供逐平台测试承诺。

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

## ⚙️ 配置

| 配置项         | 默认值 | 说明                    |
| :------------- | :----- | :---------------------- |
| `DJ_CD_TIME`   | `600`  | 打胶冷却时间（秒）      |
| `PK_CD_TIME`   | `600`  | PK 冷却时间（秒）       |
| `SUO_CD_TIME`  | `600`  | 嗦与舔冷却时间（秒）    |
| `FUCK_CD_TIME` | `1200` | 透/榨群友冷却时间（秒） |

## 🎉 使用

所有命令均遵循 NoneBot 的 `COMMAND_START` 配置

| 指令                                             | 权限                   | 目标              | 说明                                              |
| :----------------------------------------------- | :--------------------- | :---------------- | :------------------------------------------------ |
| `银趴开启`、`银趴禁止`                           | 管理员、群主或超级用户 | 当前群            | 开启或关闭群内玩法；`开始/关闭`是对应动作的 alias |
| `银趴帮助`                                       | 群成员                 | 当前群            | 输出插件命令说明；`介绍`是子命令 alias            |
| `透/日/榨` + `群友/管理/群主`                    | 群成员                 | 群友、管理或群主  | 群友可随机或 `@` 指定                             |
| `pk`、`对决`                                     | 群成员                 | 需要 `@` 其他用户 | 根据发起者胜率结算长度或深度变化                  |
| `打胶`、`开导`、`开扣`、`挖矿`                   | 群成员                 | 自己              | 增加自己的长度或深度                              |
| `嗦/舔`                                          | 群成员                 | 需要 `@` 其他用户 | 增加目标长度或深度                                |
| `夺舍`                                           | 群成员                 | 需要 `@` 其他用户 | 完成深渊试炼，夺取对方牛子的一半长度              |
| `银趴查询`                                       | 群成员                 | 自己或 `@` 用户   | 查询长度或深度状态及当天注入量                    |
| `银趴查询历史`、`银趴查询全部`                   | 群成员                 | 自己或 `@` 用户   | 查询状态、当天及历史总注入量                      |
| `银趴排行榜`、`银趴排名`、`银趴榜单`、`银趴rank` | 群成员                 | 当前平台          | 显示前五、后五及自己的排名                        |

## ✨ 特别感谢

- [`YuuzukiRin/nonebot_plugin_impart`](https://github.com/YuuzukiRin/nonebot_plugin_impart) 提供的玩法。
