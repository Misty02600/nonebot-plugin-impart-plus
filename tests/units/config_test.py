def test_config_can_be_instantiated():
    from nonebot_plugin_impart_plus.config import Config

    config = Config()

    assert config.dj_cd_time == 300
    assert config.pk_cd_time == 60
    assert config.suo_cd_time == 300
    assert config.fuck_cd_time == 3600
    assert not hasattr(config, "jj_variable")
