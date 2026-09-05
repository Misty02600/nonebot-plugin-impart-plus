import httpx
import pytest


@pytest.mark.parametrize(
    "family", [None, "  ", "Maple Mono NF CN", 'A"</style><script>x</script>\\B']
)
async def test_chart_fonts_match_measurement_and_keep_fallbacks(
    monkeypatch: pytest.MonkeyPatch, family: str | None
) -> None:
    import struct

    from nonebot_plugin_impart_plus.config import Config
    from nonebot_plugin_impart_plus.infra import chart_renderer
    from nonebot_plugin_impart_plus.infra.chart_layout import RankEntry

    monkeypatch.setattr(
        chart_renderer,
        "get_plugin_config",
        lambda _: Config() if family is None else Config(impart_font_family=family),
    )
    rendered: list[str] = []
    measured: list[str] = []

    async def render(html: str, *, width: int = 1600, refit: bool = False) -> bytes:
        (measured if refit else rendered).append(html)
        return (
            b"\x89PNG\r\n\x1a\n"
            + struct.pack(">I", 13)
            + b"IHDR"
            + struct.pack(">II", 100 if refit else width, 30 if refit else 940)
        )

    async def avatars(_):
        return {}

    monkeypatch.setattr(chart_renderer, "_render_png", render)
    monkeypatch.setattr(chart_renderer, "_load_avatars", avatars)
    await chart_renderer.render_ranking([RankEntry("1", "六个汉字昵称", 1.0, 1, True)])
    await chart_renderer.render_history(
        {"2026-09-01": 1, "2026-09-02": 2}, name="六个汉字昵称", total=12.345
    )

    font_family = chart_renderer._font_family()
    defaults = '"Noto Sans CJK SC"'
    assert font_family.endswith(defaults)
    if not family or not family.strip():
        assert font_family == defaults
    elif family == "Maple Mono NF CN":
        assert font_family == f'"Maple Mono NF CN", {defaults}'
    assert len(rendered) == 2
    assert "累计 12.345" in rendered[1]
    assert measured
    assert all(f"span{{font-family:{font_family};" in html for html in measured)
    for html in rendered:
        assert f"body {{ font-family: {font_family}; }}" in html
        assert html.count("font-family:") == 1
        assert html.count("</style>") == 1
        assert "<script>" not in html


@pytest.mark.parametrize("urls", [[], [None, ""]])
async def test_empty_avatars_do_not_create_http_client(
    monkeypatch: pytest.MonkeyPatch, urls: list[str | None]
) -> None:
    from nonebot_plugin_impart_plus.infra import chart_renderer

    def unexpected_client(**_):
        pytest.fail("没有头像时不应创建 HTTP 客户端")

    monkeypatch.setattr(chart_renderer.httpx, "AsyncClient", unexpected_client)
    assert await chart_renderer._load_avatars(urls) == {}


async def test_avatar_failures_leave_empty_without_loading_local_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_impart_plus.infra import chart_renderer

    requested: list[str] = []
    png = b"\x89PNG\r\n\x1a\n" + bytes(16)

    def response(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.path)
        if request.url.path == "/failure":
            raise httpx.ConnectError("unavailable", request=request)
        if request.url.path == "/large":
            return httpx.Response(200, content=png + bytes(32))
        if request.url.path == "/html":
            return httpx.Response(200, content=b"<html>error</html>")
        return httpx.Response(200, content=png)

    client_type = httpx.AsyncClient
    monkeypatch.setattr(chart_renderer, "MAX_AVATAR_BYTES", 32)
    monkeypatch.setattr(
        chart_renderer.httpx,
        "AsyncClient",
        lambda **kwargs: client_type(transport=httpx.MockTransport(response), **kwargs),
    )
    urls = [
        f"https://example.com/{path}" for path in ("ok", "failure", "large", "html")
    ]
    avatars = await chart_renderer._load_avatars(
        [*urls, urls[0], "file:///private.png", None]
    )
    assert avatars[urls[0]].startswith("data:image/png;base64,")
    assert all(avatars[url] == "" for url in urls[1:])
    assert avatars["file:///private.png"] == ""
    assert sorted(requested) == ["/failure", "/html", "/large", "/ok"]
