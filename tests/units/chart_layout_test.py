from datetime import date, timedelta


def test_ranking_keeps_self_neighbors_and_duplicate_names() -> None:
    from nonebot_plugin_impart_plus.infra.chart_layout import (
        RankEntry,
        make_ranking_context,
        select_indices,
    )

    indices = select_indices(32, 11)
    assert indices == [0, 1, 2, 3, 4, 10, 11, 12, 27, 28, 29, 30, 31]
    entries = [RankEntry(str(i), "同名用户", 20.0 - i, i + 1, i == 11) for i in indices]
    context = make_ranking_context(entries)
    assert len(context["entries"]) == 13
    assert [row["rank"] for row in context["entries"] if row["is_self"]] == [12]
    assert len(context["gaps"]) == 2
    assert select_indices(7, 3) == list(range(7))


def test_signed_bars_share_scale() -> None:
    from nonebot_plugin_impart_plus.infra.chart_layout import (
        RankEntry,
        make_ranking_context,
    )

    context = make_ranking_context(
        [
            RankEntry("a", "甲", 0.001, 1, True),
            RankEntry("b", "乙", -0.001, 2),
        ]
    )
    positive, negative = context["entries"]
    assert positive["value"] == "0.001"
    assert negative["value"] == "-0.001"
    assert positive["bar_height"] == negative["bar_height"]


def test_history_limits_details_but_keeps_all_points() -> None:
    from nonebot_plugin_impart_plus.infra.chart_layout import make_history_context

    history = {
        (date(2026, 1, 1) + timedelta(days=i)).isoformat(): float(i) for i in range(365)
    }
    context = make_history_context(history)
    assert len(context["points"]) == 365
    assert len(context["segments"]) == 364
    assert len(context["records"]) == 19
    assert context["records"][9] is None
    assert context["records"][0]["date"] == "2026-01-01"
    assert context["records"][-1]["date"] == "2026-12-31"
    assert context["canvas_height"] == 1098


def test_sparse_dates_and_small_ticks() -> None:
    import pytest

    from nonebot_plugin_impart_plus.infra.chart_layout import make_history_context

    context = make_history_context(
        {"2026-09-05": 0.001, "2026-09-01": 0, "2026-09-02": 0.001}
    )
    first, middle, last = context["points"]
    assert last["x"] - middle["x"] == pytest.approx(3 * (middle["x"] - first["x"]))
    labels = [tick["label"] for tick in context["y_ticks"]]
    assert len(labels) == len(set(labels))
