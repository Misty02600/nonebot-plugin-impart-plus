def test_growth_mode_boundaries_and_signed_delta() -> None:
    from nonebot_plugin_impart_plus.impart.core import (
        GrowthMode,
        growth_delta,
        supports_growth_mode,
    )

    assert supports_growth_mode(1.0, GrowthMode.LENGTH)
    assert not supports_growth_mode(0.0, GrowthMode.LENGTH)
    assert supports_growth_mode(0.0, GrowthMode.DEPTH)
    assert supports_growth_mode(-1.0, GrowthMode.DEPTH)
    assert growth_delta(1.25, GrowthMode.LENGTH) == 1.25
    assert growth_delta(1.25, GrowthMode.DEPTH) == -1.25
