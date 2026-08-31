"""跨平台事件上下文转换。"""

from nonebot_plugin_alconna import At, Match, UniMessage
from nonebot_plugin_uninfo import Session, Uninfo


def public_scene(session: Uninfo) -> bool:
    return session.scene.is_group or session.scene.is_guild or session.scene.is_channel


def legacy_scene_id(session: Session) -> int:
    """把当前场景转换为 UniRef 接入前的整数数据库键。"""
    return int(session.scene.id)


def mentioned_user_id(
    target: Match[At],
    tail: Match[UniMessage],
) -> str | None:
    if target.available and target.result.flag == "user":
        return target.result.target
    if tail.available:
        return next(
            (
                segment.target
                for segment in tail.result
                if isinstance(segment, At) and segment.flag == "user"
            ),
            None,
        )
    return None
