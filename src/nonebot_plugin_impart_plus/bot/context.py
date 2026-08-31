"""跨平台事件上下文转换。"""

from nonebot_plugin_alconna import At, AtAll, Match, UniMessage, UniMsg
from nonebot_plugin_uninfo import Session, Uninfo


def public_scene(session: Uninfo) -> bool:
    return session.scene.is_group or session.scene.is_guild or session.scene.is_channel


def legacy_scene_id(session: Session) -> int:
    """把当前场景转换为 UniRef 接入前的整数数据库键。"""
    return int(session.scene.id)


def member_parent_scene_id(session: Session) -> str:
    return session.scene.parent.id if session.scene.parent else session.scene.id


def mentioned_user_id(
    target: Match[At],
    tail: Match[UniMessage],
) -> str | None:
    if target.available and target.result.flag == "user":
        return target.result.target
    if tail.available:
        return first_mentioned_user_id(tail.result)
    return None


def first_mentioned_user_id(message: UniMessage) -> str | None:
    for segment in message:
        if isinstance(segment, AtAll):
            return None
        if isinstance(segment, At):
            return segment.target if segment.flag == "user" else None
    return None


def has_user_mention(message: UniMsg) -> bool:
    return first_mentioned_user_id(message) is not None
