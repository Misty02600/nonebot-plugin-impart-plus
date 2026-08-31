from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from nonebot.exception import FinishedException

if TYPE_CHECKING:
    from nonebot_plugin_uninfo import Session


def make_session(scene_type: int, scene_id: str = "42") -> "Session":
    from nonebot_plugin_uninfo import Scene, SceneType, Session, User

    return Session(
        self_id="10000",
        adapter="OneBot V11",
        scope="QQClient",
        scene=Scene(id=scene_id, type=SceneType(scene_type)),
        user=User(id="10001"),
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
