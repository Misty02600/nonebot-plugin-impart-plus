def test_config_can_be_instantiated():
    from nonebot_plugin_impart_plus.config import Config

    config = Config()

    assert config.dj_cd_time == 600
    assert config.pk_cd_time == 600
    assert config.suo_cd_time == 600
    assert config.fuck_cd_time == 1200
    assert not hasattr(config, "jj_variable")
    assert not hasattr(config, "isalive")
