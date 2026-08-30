"""Impart 图表渲染器。

使用 Jinja2 模板 + Playwright 将排行榜和注入历史数据渲染为图片。

架构设计：
    - 与 draw_img.py 保持相同的依赖注入接口
    - 使用 HTML/CSS 替代 Pillow 手绘，提升视觉质量
    - 参考 migut-help/render_help.py 的实现模式
"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from jinja2 import Environment, FileSystemLoader
from nonebot import logger

# region 路径常量
_PKG_DIR = Path(__file__).resolve().parent
_TEMPLATES_DIR = _PKG_DIR / "templates" / "charts"
# endregion


class RankEntry(TypedDict):
    """排行榜条目数据结构。"""

    rank: int  # 排名（1-indexed）
    userid: str  # 用户ID
    nickname: str  # 昵称
    avatar_url: str  # 头像URL
    jj_length: float  # 长度
    is_self: bool  # 是否为查询者
    bar_width: float  # 柱状条宽度百分比（0-100）


class InjectionPoint(TypedDict):
    """注入历史数据点。"""

    date: str  # 日期字符串（YYYY-MM-DD）
    volume: float  # 注入量


class ChartRenderer:
    """图表渲染器，生成排行榜和注入历史图片。

    保持与 DrawBarChart 相同的公开接口，便于无缝替换。
    """

    def __init__(self) -> None:
        """初始化渲染器，加载 Jinja2 环境。"""
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._css = (_TEMPLATES_DIR / "style.css").read_text(encoding="utf-8")

    async def draw_bar_chart(
        self,
        rank_data: list[tuple[int, str, str, str, float]],
        user_rank: int,
        user_id: str,
        total: int,
    ) -> bytes:
        """渲染排行榜图片。

        Args:
            rank_data: 排名数据列表，每项为 (rank, userid, nickname, avatar_url, jj_length)
            user_rank: 查询者的排名（1-indexed）
            user_id: 查询者的用户ID
            total: 总人数

        Returns:
            PNG 图片 bytes
        """
        # 计算柱状条宽度（基于绝对值）
        max_abs_length = max((abs(entry[4]) for entry in rank_data), default=1.0)

        # 构建 RankEntry 列表
        entries: list[RankEntry] = []
        for rank, userid, nickname, avatar_url, jj_length in rank_data:
            bar_width = (
                (abs(jj_length) / max_abs_length * 100) if max_abs_length > 0 else 0
            )
            entries.append(
                {
                    "rank": rank,
                    "userid": userid,
                    "nickname": nickname,
                    "avatar_url": avatar_url,
                    "jj_length": jj_length,
                    "is_self": userid == user_id,
                    "bar_width": bar_width,
                }
            )

        # 分组数据：前5名、你的位置（条件）、倒数5名（互不重叠）
        # 当 total <= 10 时 threshold == 5，bottom5 不会与 top5 交叉
        bottom5_threshold = max(5, total - 5)
        top5 = [e for e in entries if e["rank"] <= 5]
        bottom5 = [e for e in entries if e["rank"] > bottom5_threshold]

        # 如果用户不在前5/后5，显示"你的位置"段
        middle: list[RankEntry] = []
        if user_rank > 5 and user_rank <= bottom5_threshold:
            middle = [e for e in entries if 5 < e["rank"] <= bottom5_threshold]

        template = self._env.get_template("bar_chart.jinja2")
        body_html = template.render(
            top5=top5,
            middle=middle,
            bottom5=bottom5,
            total=total,
        )

        return await self._render_to_png(body_html)

    async def draw_line_chart(
        self,
        user_name: str,
        user_avatar: str,
        data: dict[str, float],
    ) -> bytes:
        """渲染注入历史折线图。

        Args:
            user_name: 用户昵称
            user_avatar: 用户头像URL
            data: {日期: 注入量} 字典

        Returns:
            PNG 图片 bytes
        """
        # 按日期排序并转换为数据点列表
        sorted_dates = sorted(data.keys())
        data_points: list[InjectionPoint] = [
            {"date": date, "volume": data[date]} for date in sorted_dates
        ]

        total_volume = sum(data.values())
        max_volume = max(data.values(), default=1.0)

        template = self._env.get_template("line_chart.jinja2")
        body_html = template.render(
            user_name=user_name,
            user_avatar=user_avatar,
            total_volume=total_volume,
            data_points=data_points,
            max_volume=max_volume,
        )

        return await self._render_to_png(body_html)

    async def _render_to_png(self, body_html: str) -> bytes:
        """将 HTML 渲染为 PNG 图片。

        参考 migut-help/render_help.py：
        1. 写入临时 HTML 文件到模板目录（使 CSS 字体相对路径生效）
        2. 使用 page.goto(file://) 而非 set_content（保持 file:// origin）
        3. 自适应内容高度后截图
        """
        html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <style>
{self._css}
    </style>
</head>
<body>
{body_html}
</body>
</html>"""

        # 写入临时文件到模板目录
        render_html = _TEMPLATES_DIR / "_render_tmp.html"
        render_html.write_text(html_doc, encoding="utf-8")

        file_url = render_html.as_uri()

        # 延迟导入 htmlrender，避免在不需要图表渲染的测试中触发 Playwright 启动。
        from nonebot_plugin_htmlrender.browser import get_new_page

        async with get_new_page(device_scale_factor=2) as page:
            await page.goto(file_url, wait_until="networkidle")
            await page.wait_for_timeout(500)

            # 获取页面实际内容高度
            content_height = await page.evaluate(
                "Math.max(document.body.scrollHeight, document.body.offsetHeight,"
                " document.documentElement.scrollHeight)"
            )
            # 设置 viewport 宽度 510px（480 + 2*15 padding），高度自适应，上限 8000px
            viewport_h = min(content_height + 30, 8000)
            logger.debug(
                f"[impart-chart] content_height={content_height}, viewport_h={viewport_h}"
            )
            await page.set_viewport_size({"width": 510, "height": viewport_h})
            pic = await page.screenshot(full_page=True, type="png")
            logger.debug(f"[impart-chart] screenshot size: {len(pic)} bytes")
            return pic
