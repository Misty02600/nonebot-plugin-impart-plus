"""Handler 共享文案与用户目录辅助函数。"""

from nonebot import logger
from nonebot.exception import SkippedException
from nonebot_plugin_alconna import At
from nonebot_plugin_uninfo import Interface, Member, Uninfo, User

NOT_ALLOWED_TEXT = (
    '当前未开启impart游戏, 请管理员发送"银趴开启", "银趴禁止"以开启/关闭该功能'
)
JJ_NAMES = ("牛子", "牛牛", "newnew")
HOLE_NAME = "小学"


def user_display_name(user: User | None, fallback: str) -> str:
    if user is None:
        return fallback
    return str(user.nick or user.name or fallback)


def member_display_name(member: Member | None, fallback: str) -> str:
    if member is None:
        return fallback
    return str(member.nick or member.user.nick or member.user.name or fallback)


def member_has_role(member: Member, role_id: str) -> bool:
    return any(role.id == role_id for role in member.roles)


def user_at_target(target: At) -> str:
    if target.flag != "user":
        raise SkippedException
    return target.target


async def get_user_or_none(interface: Interface, user_id: str) -> User | None:
    try:
        return await interface.get_user(user_id)
    except Exception:
        return None


async def get_member_or_none(
    interface: Interface,
    session: Uninfo,
    user_id: str,
) -> Member | None:
    try:
        return await interface.get_member(
            session.scene.type,
            session.scene.parent.id if session.scene.parent else session.scene.id,
            user_id,
        )
    except Exception:
        return None


async def get_members_or_empty(
    interface: Interface,
    session: Uninfo,
) -> list[Member]:
    try:
        return await interface.get_members(
            session.scene.type,
            session.scene.parent.id if session.scene.parent else session.scene.id,
        )
    except Exception as error:
        logger.opt(exception=error).warning(
            "获取成员列表失败: adapter={}, scene_type={}",
            session.adapter,
            session.scene.type.name,
        )
        return []
