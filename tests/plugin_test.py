import pytest
from nonebug import App
from tests.fake import fake_group_message_event_v11


@pytest.mark.asyncio
async def test_plugin_metadata(app: App):
    """测试插件元数据加载是否正常"""
    from nonebot_plugin_impart_plus import __plugin_meta__

    assert __plugin_meta__.name == "nonebot_plugin_impart_plus"


@pytest.mark.asyncio
async def test_fake_event():
    """测试虚拟事件创建"""
    from nonebot.adapters.onebot.v11 import Message

    event = fake_group_message_event_v11(message=Message("测试消息"))
    assert event.message_type == "group"
    assert event.user_id == 12345678
    assert str(event.message) == "测试消息"
