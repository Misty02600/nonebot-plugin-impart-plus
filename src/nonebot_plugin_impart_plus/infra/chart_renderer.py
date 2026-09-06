"""HTMLKit 图表渲染；模板只读，用户资料与游戏数据由 Handler 传入。"""

import asyncio
import base64
import math
import struct
from collections.abc import Mapping, Sequence
from contextlib import suppress
from html import escape as escape_html
from pathlib import Path
from typing import Any

import httpx
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from nonebot import get_plugin_config
from nonebot_plugin_htmlkit import html_to_pic, none_fetcher

from ..config import Config
from .chart_layout import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    NAME_FONT_SIZE,
    RankEntry,
    format_volume,
    make_history_context,
    make_ranking_context,
)

TEMPLATES = Path(__file__).parent / "templates"
ENV = Environment(
    loader=FileSystemLoader(TEMPLATES), autoescape=True, undefined=StrictUndefined
)
RENDER_SLOTS = asyncio.Semaphore(2)
AVATAR_SLOTS = asyncio.Semaphore(4)
MAX_AVATAR_BYTES = 2 * 1024 * 1024
RENDER_SCALE = 2


def _font_family() -> str:
    configured = get_plugin_config(Config).impart_font_family
    # 自定义字体缺失或配置留空时，仍使用 Config 声明的默认回退。
    names = [
        name.strip()
        for name in f"{configured},{Config().impart_font_family}".split(",")
        if name.strip()
    ]
    families: list[str] = []
    for name in dict.fromkeys(names):
        if name in {"serif", "sans-serif", "monospace", "cursive", "fantasy"}:
            families.append(name)
            continue
        # 每个名称单独转义，不能注入 CSS 规则或结束 HTML style 标签。
        escaped = "".join(
            f"\\{ord(char):x} "
            if char in '\\"<>' or ord(char) < 32 or ord(char) == 127
            else char
            for char in name
        )
        families.append(f'"{escaped}"')
    return ", ".join(families)


def _chart_css(filename: str, font_family: str) -> str:
    # 模板以 rem 表示布局单位，根字号控制最终像素倍率；昵称仍按 1 倍 px 测量。
    return (
        f"html {{ font-size: {RENDER_SCALE}px; }}\n"
        f"body {{ font-family: {font_family}; }}\n"
    ) + (TEMPLATES / filename).read_text(encoding="utf-8")


def png_dimensions(png: bytes) -> tuple[int, int]:
    if len(png) < 24 or png[:8] != b"\x89PNG\r\n\x1a\n" or png[12:16] != b"IHDR":
        raise ValueError("渲染结果缺少有效 PNG 尺寸头")
    return struct.unpack(">II", png[16:24])


async def _render_png(
    html: str, *, width: int = CANVAS_WIDTH * RENDER_SCALE, refit: bool = False
) -> bytes:
    async with RENDER_SLOTS:
        # 取消命令时等待本次原生任务结束，再归还并发名额。
        task = asyncio.create_task(
            html_to_pic(
                html,
                max_width=width,
                allow_refit=refit,
                dpi=96,
                img_fetch_fn=none_fetcher,
                css_fetch_fn=none_fetcher,
            )
        )
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            with suppress(Exception):
                await task
            raise


async def _load_avatars(urls: Sequence[str | None]) -> dict[str, str]:
    unique_urls = {url for url in urls if url}
    if not unique_urls:
        return {}
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:

        async def load(url: str) -> tuple[str, str]:
            async with AVATAR_SLOTS:
                try:
                    if httpx.URL(url).scheme not in ("http", "https"):
                        return url, ""
                    async with (
                        asyncio.timeout(10),
                        client.stream("GET", url) as response,
                    ):
                        response.raise_for_status()
                        data = bytearray()
                        async for chunk in response.aiter_bytes():
                            data.extend(chunk)
                            if len(data) > MAX_AVATAR_BYTES:
                                return url, ""
                    if data.startswith(b"\x89PNG\r\n\x1a\n"):
                        mime = "image/png"
                    elif data.startswith(b"\xff\xd8"):
                        mime = "image/jpeg"
                    elif data.startswith((b"GIF87a", b"GIF89a")):
                        mime = "image/gif"
                    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
                        mime = "image/webp"
                    else:
                        return url, ""
                    return url, f"data:{mime};base64," + base64.b64encode(data).decode(
                        "ascii"
                    )
                except (httpx.HTTPError, httpx.InvalidURL, TimeoutError):
                    return url, ""

        return dict(await asyncio.gather(*(load(url) for url in unique_urls)))


class NicknameLayout:
    """用当前 HTMLKit 字体的实际宽度排两行昵称，并缓存重复测量结果。"""

    def __init__(self, font_family: str) -> None:
        self.font_family = font_family
        self.widths: dict[tuple[str, bool], int] = {}

    async def measure(self, text: str, bold: bool) -> int:
        if not text:
            return 0
        key = text, bold
        if key not in self.widths:
            html = (
                "<html><head><style>*{margin:0;padding:0;}"
                f"span{{font-family:{self.font_family};"
                f"font-size:{NAME_FONT_SIZE}px;font-weight:{600 if bold else 400};"
                "white-space:nowrap;}</style></head><body>"
                f"<span>{escape_html(text)}</span></body></html>"
            )
            png = await _render_png(html, width=2048, refit=True)
            self.widths[key] = png_dimensions(png)[0]
        return self.widths[key]

    async def fit(self, text: str, width: int, bold: bool) -> list[str]:
        if await self.measure(text, bold) <= width:
            return [text]

        async def prefix(value: str, suffix: str = "") -> int:
            left, right = 0, len(value)
            while left < right:
                middle = (left + right + 1) // 2
                if await self.measure(value[:middle].rstrip() + suffix, bold) <= width:
                    left = middle
                else:
                    right = middle - 1
            return left

        first_end = await prefix(text)
        if not first_end:
            return ["…"]
        first, rest = text[:first_end].rstrip(), text[first_end:].lstrip()
        if await self.measure(rest, bold) <= width:
            return [first, rest]
        second_end = await prefix(rest, "…")
        return [first, rest[:second_end].rstrip() + "…"]

    async def apply(self, context: dict[str, Any]) -> None:
        for entry in context["entries"]:
            lines = await self.fit(
                entry["full_name"], context["name_width"], entry["is_self"]
            )
            widths = [await self.measure(line, entry["is_self"]) for line in lines]
            if len(lines) > 2 or any(width > context["name_width"] for width in widths):
                raise RuntimeError("昵称超过了人物列表的可用宽度")
            entry["name_lines"] = lines
            entry["name_top"] = 13 if len(lines) == 1 else 0


async def render_ranking(entries: Sequence[RankEntry]) -> bytes:
    context = make_ranking_context(entries)
    avatars = await _load_avatars([entry.avatar_url for entry in entries])
    font_family = _font_family()
    await NicknameLayout(font_family).apply(context)
    for source, row in zip(entries, context["entries"], strict=True):
        row["avatar"] = avatars.get(source.avatar_url or "", "")
    html = ENV.get_template("ranking.html.jinja").render(
        css=_chart_css("ranking.css", font_family),
        **context,
    )
    png = await _render_png(html)
    if png_dimensions(png) != (
        CANVAS_WIDTH * RENDER_SCALE,
        CANVAS_HEIGHT * RENDER_SCALE,
    ):
        raise RuntimeError("排行榜图片尺寸异常")
    return png


async def render_history(
    history: Mapping[str, float],
    *,
    name: str,
    avatar_url: str | None = None,
    total: float,
) -> bytes:
    """渲染同一查询快照中的个人历史，保留应用层给出的累计值。"""
    if not math.isfinite(total) or total < 0:
        raise ValueError("历史累计量必须是非负有限值")
    context = make_history_context(history)
    context["total"] = format_volume(total)
    avatars = await _load_avatars([avatar_url])
    font_family = _font_family()
    names = await NicknameLayout(font_family).fit(" ".join(name.split()), 280, True)
    html = ENV.get_template("history.html.jinja").render(
        css=_chart_css("history.css", font_family),
        avatar=avatars.get(avatar_url or "", ""),
        user_name_lines=names,
        **context,
    )
    png = await _render_png(html)
    if png_dimensions(png) != (
        CANVAS_WIDTH * RENDER_SCALE,
        context["canvas_height"] * RENDER_SCALE,
    ):
        raise RuntimeError("历史图片尺寸异常")
    return png
