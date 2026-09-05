"""Handler 共享文案与用户目录辅助函数。"""

from random import choice

from nonebot import logger
from nonebot.exception import SkippedException
from nonebot_plugin_alconna import At
from nonebot_plugin_uninfo import Interface, Member, Uninfo, User
from nonebot_plugin_uniref import UserRef

NOT_ALLOWED_TEXT = (
    '当前未开启impart游戏, 请管理员发送"银趴开启", "银趴禁止"以开启/关闭该功能'
)
JJ_NAMES = ("牛子", "牛牛", "newnew")
HOLE_NAME = "小学"
OPPONENT_TITLE_LOSS = (
    "\n由于{cause}，{botname}检测到TA的{name}长度已不足25cm，很遗憾，TA跌落神坛，"
    "{botname}替TA感谢你的鞭策喵！"
    "\nTA的{penalty_name}长度缩短了5cm喵，请不忘初心，再次冲击更高的境界喵！"
)


def created_user_message(
    created_users: tuple[UserRef, ...],
    user_ref: UserRef,
    *target_refs: UserRef,
) -> str:
    user_created = user_ref in created_users
    target_count = sum(
        target != user_ref and target in created_users for target in target_refs
    )
    jj_name = choice(JJ_NAMES)
    if user_created and target_count:
        return f"你们还没有{jj_name}喵，咱帮你们创建了喵，目前长度都是10cm喵"
    if user_created:
        return f"你还没有{jj_name}喵，咱帮你创建了喵，目前长度是10cm喵"
    if target_count > 1:
        return f"TA们还没有{jj_name}喵，咱帮TA们创建了喵，目前长度都是10cm喵"
    if target_count == 1:
        return f"TA还没有{jj_name}喵，咱帮TA创建了喵，目前长度是10cm喵"
    raise ValueError("创建结果不包含命令用户")


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
