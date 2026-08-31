"""跨平台事件上下文转换。"""

from nonebot_plugin_uninfo import Session, Uninfo


def public_scene(session: Uninfo) -> bool:
    return session.scene.is_group or session.scene.is_guild or session.scene.is_channel


def legacy_scene_id(session: Session) -> int:
    """把当前场景转换为 UniRef 接入前的整数数据库键。"""
    return int(session.scene.id)
