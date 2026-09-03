from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

from nonebot.exception import FinishedException

if TYPE_CHECKING:
    from nonebot_plugin_uninfo import Session
    from nonebot_plugin_uniref import RefContext, SceneRef, UserRef


def make_session(scene_type: int, scene_id: str = "42") -> "Session":
    from nonebot_plugin_uninfo import Scene, SceneType, Session, User

    return Session(
        self_id="10000",
        adapter="OneBot V11",
        scope="QQClient",
        scene=Scene(id=scene_id, type=SceneType(scene_type)),
        user=User(id="10001"),
    )


def make_user_ref(
    user_id: str = "10001",
    namespace: str = "QQClient",
) -> "UserRef":
    from nonebot_plugin_uniref import UserRef

    return UserRef(namespace=namespace, id=user_id)


def make_scene_ref(
    scene_id: str = "42",
    namespace: str = "QQClient",
) -> "SceneRef":
    from nonebot_plugin_uniref import SceneKind, SceneRef

    return SceneRef(
        namespace=namespace,
        type=SceneKind.GROUP,
        id=scene_id,
    )


class RefContextStub:
    def __init__(
        self,
        user_ref: "UserRef",
        scene_ref: "SceneRef",
    ) -> None:
        self.user_ref = user_ref
        self.scene_ref = scene_ref
        self.parent_scene_ref: SceneRef | None = None

    def build_user_ref(self, user_id: str) -> "UserRef":
        return make_user_ref(user_id, self.user_ref.namespace)

    def build_scene_ref(self, scene_id: str) -> "SceneRef":
        from nonebot_plugin_uniref import SceneRef

        return SceneRef(
            namespace=self.scene_ref.namespace,
            type=self.scene_ref.type,
            id=scene_id,
        )


def make_ref_context(
    scene_id: str = "42",
    user_id: str = "10001",
    namespace: str = "QQClient",
) -> "RefContext":
    return cast(
        "RefContext",
        RefContextStub(
            make_user_ref(user_id, namespace),
            make_scene_ref(scene_id, namespace),
        ),
    )


@dataclass
class MatcherStub:
    messages: list[str] = field(default_factory=list)
    raw_messages: list[object] = field(default_factory=list)
    options: list[dict[str, object]] = field(default_factory=list)

    async def send(self, message: object, **kwargs: object) -> None:
        self.raw_messages.append(message)
        self.messages.append(str(message))
        self.options.append(kwargs)

    async def finish(self, message: object, **kwargs: object) -> None:
        self.raw_messages.append(message)
        self.messages.append(str(message))
        self.options.append(kwargs)


class FinishingMatcherStub(MatcherStub):
    async def finish(self, message: object, **kwargs: object) -> None:
        self.raw_messages.append(message)
        self.messages.append(str(message))
        self.options.append(kwargs)
        raise FinishedException
