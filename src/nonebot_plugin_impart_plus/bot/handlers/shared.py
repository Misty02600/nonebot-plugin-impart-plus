"""Handler 共享文案与用户目录辅助函数。"""

from nonebot_plugin_uninfo import Interface, Member, Uninfo, User

from ..context import member_parent_scene_id

NOT_ALLOWED_TEXT = (
    '当前未开启impart游戏, 请管理员发送"银趴开启", "银趴禁止"以开启/关闭该功能'
)


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
            member_parent_scene_id(session),
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
            member_parent_scene_id(session),
        )
    except Exception:
        return []
