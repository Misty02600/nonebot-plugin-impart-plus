"""图表展示数据与几何计算，不读取用户目录、数据库或渲染资源。"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from itertools import pairwise
from typing import Any, TypedDict

CANVAS_WIDTH = 1600
CANVAS_HEIGHT = 940
CHART_WIDTH = 1064
GAP_WIDTH = 24
BAR_WIDTH = 42
PLOT_TOP = 48
PLOT_HEIGHT = 624
VALUE_LABEL_SPACE = 40
NAME_FONT_SIZE = 22
NAME_WIDTH = 234
PERSON_ROW_HEIGHT = 56
PERSON_GROUP_GAP = 12
ROW_HEIGHT = 42
DATE_LABEL_WIDTH = 110
DATE_LABEL_GAP = 12


@dataclass(frozen=True)
class RankEntry:
    user_id: str
    name: str
    length: float
    rank: int
    is_self: bool = False
    avatar_url: str | None = None


def select_indices(total: int, self_index: int) -> list[int]:
    """合并前五、后五以及中段本人的左右各一位，重叠名次只保留一次。"""
    if not 0 <= self_index < total:
        raise ValueError("本人索引必须落在排行榜内")
    indices = set(range(min(5, total))) | set(range(max(0, total - 5), total))
    if 5 <= self_index < total - 5:
        indices.update(range(self_index - 1, self_index + 2))
    return sorted(indices)


def axis_range(
    positive: float,
    negative: float,
    *,
    plot_height: int = PLOT_HEIGHT,
    label_space: int = VALUE_LABEL_SPACE,
) -> tuple[float, float, list[float]]:
    """生成共享比例尺的等距刻度，并为极值标签预留空间。

    Args:
        positive: 非负的正值极值。
        negative: 非负的负值极值绝对值。
        plot_height: 绘图区高度，单位为像素。
        label_space: 每侧极值标签的预留高度，需小于绘图区高度的一半。

    Returns:
        上界、下界与降序刻度列表；全零输入使用 [-1, 1]。

    Raises:
        ValueError: 极值不是非负有限数，或高度与标签空间无效。
    """
    if any(not math.isfinite(value) or value < 0 for value in (positive, negative)):
        raise ValueError("轴极值必须是非负有限数")
    if plot_height <= 0 or not 0 <= label_space < plot_height / 2:
        raise ValueError("标签空间必须非负且小于绘图区高度的一半")
    if positive == negative == 0:
        return 1.0, -1.0, [1.0, 0.5, 0.0, -0.5, -1.0]
    rough_step = (positive + negative) / 7
    magnitude = 10 ** math.floor(math.log10(rough_step))
    step = magnitude * next(
        x for x in (1, 2, 2.5, 5, 10) if x >= rough_step / magnitude
    )
    above = math.ceil(positive / step)
    below = math.ceil(negative / step)
    while True:
        scale = plot_height / ((above + below) * step)
        extend_above = positive > 0 and (above * step - positive) * scale < label_space
        extend_below = negative > 0 and (below * step - negative) * scale < label_space
        if not extend_above and not extend_below:
            break
        above += int(extend_above)
        below += int(extend_below)
    return above * step, -below * step, [i * step for i in range(above, -below - 1, -1)]


def make_ranking_context(ranking: Sequence[RankEntry]) -> dict[str, Any]:
    """计算同一比例尺下的正负柱体、分段留白和本人高亮位置。

    Args:
        ranking: 按真实名次升序排列的展示条目，身份唯一且有且仅有一条本人记录。

    Returns:
        可直接交给模板的几何和显示数据；柱高保持线性，零值不伪造柱高。
    """
    if any(not math.isfinite(entry.length) for entry in ranking):
        raise ValueError("长度必须是有限值")
    if len({entry.user_id for entry in ranking}) != len(ranking):
        raise ValueError("用户身份不能重复")
    if any(a.length < b.length for a, b in pairwise(ranking)):
        raise ValueError("排行榜必须按长度降序排列")
    if not ranking or len(ranking) > 13:
        raise ValueError("排行榜展示条目必须为 1 到 13 人")
    if sum(item.is_self for item in ranking) != 1:
        raise ValueError("排行榜必须包含且只包含一条本人记录")
    if ranking[0].rank < 1 or any(a.rank >= b.rank for a, b in pairwise(ranking)):
        raise ValueError("展示名次必须为正整数且严格递增")
    positive = max(0.0, *(item.length for item in ranking))
    negative = max(0.0, *(-item.length for item in ranking))
    upper, lower, ticks = axis_range(positive, negative)
    scale = PLOT_HEIGHT / (upper - lower)
    baseline = PLOT_TOP + upper * scale
    tick_labels = [f"{tick:g}" for tick in ticks]
    axis_left = max(64, max(map(len, tick_labels)) * 10 + 14)
    plot_width = CHART_WIDTH - axis_left - 16
    breaks = sum(b.rank > a.rank + 1 for a, b in pairwise(ranking))
    column_width = min(118.0, (plot_width - breaks * GAP_WIDTH) / len(ranking))
    left = (
        axis_left + (plot_width - len(ranking) * column_width - breaks * GAP_WIDTH) / 2
    )
    entries: list[dict[str, Any]] = []
    gaps: list[dict[str, float]] = []
    legend_gap = 0
    for offset, item in enumerate(ranking):
        if offset and item.rank > ranking[offset - 1].rank + 1:
            gaps.append({"left": round(left, 2), "width": GAP_WIDTH})
            left += GAP_WIDTH
            legend_gap += PERSON_GROUP_GAP
        is_self = item.is_self
        height = abs(item.length) * scale
        top = baseline - height if item.length >= 0 else baseline + 2
        entries.append(
            {
                "rank": item.rank,
                "user_id": item.user_id,
                "full_name": " ".join(item.name.split()),
                "name_lines": [],
                "legend_top": offset * PERSON_ROW_HEIGHT + legend_gap,
                "avatar": "",
                "value": f"{item.length:.3f}".rstrip("0").rstrip(".")
                if item.length
                else "0",
                "negative": item.length < 0,
                "is_self": is_self,
                "left": round(left, 2),
                "bar_left": round(left + (column_width - BAR_WIDTH) / 2, 2),
                "bar_top": round(top, 2),
                "bar_height": round(height, 2),
                "value_top": round(
                    max(
                        PLOT_TOP + 2, top - 36 if item.length >= 0 else top + height + 8
                    ),
                    2,
                ),
                "bar_class": "bar-negative" if item.length < 0 else "bar-positive",
                "rank_text": f"#{item.rank}",
            }
        )
        left += column_width
    return {
        "entries": entries,
        "gaps": gaps,
        "baseline": round(baseline, 2),
        "axis_left": axis_left,
        "axis_top": PLOT_TOP,
        "axis_height": PLOT_HEIGHT,
        "chart_rank_top": PLOT_TOP + PLOT_HEIGHT + 52,
        "plot_width": plot_width,
        "axis_ticks": [
            {"label": label, "y": round(PLOT_TOP + (upper - value) * scale, 2)}
            for value, label in zip(ticks, tick_labels, strict=True)
        ],
        "column_width": round(column_width, 2),
        "name_width": NAME_WIDTH,
        "name_font_size": NAME_FONT_SIZE,
        "bar_width": BAR_WIDTH,
    }


class HistoryPoint(TypedDict):
    date: str
    volume: float
    x: float
    y: float


def format_volume(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".") if value else "0"


def line_segment(first: HistoryPoint, second: HistoryPoint) -> dict[str, float]:
    """用垂直于线段的窄渐变色带画斜线，兼容没有 SVG/transform 的 HTMLKit。

    Args:
        first: 起点的 x/y 坐标。
        second: 终点坐标，x 必须大于起点。

    Returns:
        线段矩形、CSS 渐变角度与边缘透明度停止点；线宽为 3px。

    Raises:
        ValueError: 终点未位于起点右侧。
    """
    dx, dy = second["x"] - first["x"], second["y"] - first["y"]
    if dx <= 0:
        raise ValueError("折线终点必须位于起点右侧")
    angle = math.atan2(dy, dx)
    width, height = dx + 4, abs(dy) + 4
    gradient_length = width * abs(math.sin(angle)) + height * abs(math.cos(angle))
    inner, outer = 100 / gradient_length, 200 / gradient_length
    return {
        "left": round(first["x"] - 2, 3),
        "top": round(min(first["y"], second["y"]) - 2, 3),
        "width": round(width, 3),
        "height": round(height, 3),
        "angle": round(math.degrees(angle), 5),
        "outer_start": round(50 - outer, 5),
        "inner_start": round(50 - inner, 5),
        "inner_end": round(50 + inner, 5),
        "outer_end": round(50 + outer, 5),
    }


def make_history_context(history: Mapping[str, float]) -> dict[str, Any]:
    """按真实日期间隔生成每日明细与折线，缺失日期不补零。

    Args:
        history: ISO 日期到当日注入总量的映射，值应为非负有限数。

    Returns:
        明细、折线、时间轴及画布尺寸；超过十八天的明细仅展示最早、最近各九条，
        折线仍使用全部记录，累计量由调用方传入渲染器。

    Raises:
        ValueError: 日期无法解析，或总量为负数/非有限值。
    """
    ordered = sorted((date.fromisoformat(key), value) for key, value in history.items())
    if any(not math.isfinite(value) or value < 0 for _, value in ordered):
        raise ValueError("历史注入总量必须是非负有限值")
    upper, _, ticks = axis_range(
        max((value for _, value in ordered), default=0) or 1,
        0,
        plot_height=PLOT_HEIGHT,
    )
    scale = PLOT_HEIGHT / upper
    tick_labels = [f"{value:g}" for value in ticks]
    axis_left = max(64, max(map(len, tick_labels)) * 10 + 14)
    plot_width = CHART_WIDTH - axis_left - 16
    baseline = PLOT_TOP + PLOT_HEIGHT
    x_start, x_end = axis_left + 16, axis_left + plot_width - 16
    points: list[HistoryPoint] = []
    x_ticks: list[dict[str, Any]] = []
    if ordered:
        start, end = ordered[0][0], ordered[-1][0]
        days = (end - start).days

        def x_at(day: date) -> float:
            return (
                (x_start + x_end) / 2
                if not days
                else x_start + (day - start).days / days * (x_end - x_start)
            )

        points = [
            {
                "date": day.isoformat(),
                "volume": value,
                "x": x_at(day),
                "y": baseline - value * scale,
            }
            for day, value in ordered
        ]
        offsets = (
            sorted({round(i * days / min(7, days)) for i in range(min(7, days) + 1)})
            if days
            else [0]
        )
        for i, offset in enumerate(offsets):
            day = start + timedelta(days=offset)
            x = x_at(day)
            align = (
                "center"
                if len(offsets) == 1
                else "left"
                if i == 0
                else "right"
                if i == len(offsets) - 1
                else "center"
            )
            x_ticks.append(
                {
                    "x": round(x, 3),
                    "label_left": round(
                        x
                        if align == "left"
                        else x - DATE_LABEL_WIDTH
                        if align == "right"
                        else x - DATE_LABEL_WIDTH / 2,
                        3,
                    ),
                    "align": align,
                    "label": day.strftime(
                        "%Y-%m-%d" if start.year != end.year else "%m-%d"
                    ),
                }
            )
    if len(x_ticks) > 2:
        spacing = DATE_LABEL_WIDTH + DATE_LABEL_GAP
        last = x_ticks[-1]
        spaced = [x_ticks[0]]
        for tick in x_ticks[1:-1]:
            if (
                tick["label_left"] >= spaced[-1]["label_left"] + spacing
                and tick["label_left"] + spacing <= last["label_left"]
            ):
                spaced.append(tick)
        x_ticks = [*spaced, last]
    records: list[dict[str, str] | None] = [
        {"date": day.isoformat(), "volume": format_volume(value)}
        for day, value in ordered
    ]
    if len(records) > 18:
        records = [*records[:9], None, *records[-9:]]
    return {
        "canvas_height": max(CANVAS_HEIGHT, 244 + len(records) * ROW_HEIGHT + 56),
        "row_height": ROW_HEIGHT,
        "date_label_width": DATE_LABEL_WIDTH,
        "records": records,
        "points": points,
        "segments": [line_segment(first, second) for first, second in pairwise(points)],
        "axis_left": axis_left,
        "plot_top": PLOT_TOP,
        "plot_height": PLOT_HEIGHT,
        "plot_width": plot_width,
        "baseline": baseline,
        "y_ticks": [
            {"label": label, "y": round(baseline - value * scale, 3)}
            for value, label in zip(ticks, tick_labels, strict=True)
        ],
        "x_ticks": x_ticks,
    }
