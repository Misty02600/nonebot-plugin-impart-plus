"""成长与查询相关文案。"""

from __future__ import annotations

from pydantic import BaseModel

# region 共享基类


class _JJBase(BaseModel, frozen=True):
    """牛子名称 — 所有 JJ 功能共享。新增共享字段只需改这里。"""

    jj_name: str


class _JJBotBase(_JJBase, frozen=True):
    """牛子 + 机器人昵称 — 打胶/嗦/PK 共享。"""

    botname: str = ""


class _HoleBase(BaseModel, frozen=True):
    """深渊名称 — 所有负值功能共享。新增共享字段只需改这里。"""

    hole_name: str


class _HoleBotBase(_HoleBase, frozen=True):
    """深渊 + 机器人昵称 — 开扣/舔/PK 共享。"""

    botname: str = ""


# endregion

# region 正值成长


def dajiao_cd(*, remaining: float) -> str:
    """CD 冷却提示（独立上下文）。"""
    return f"你已经打不动了喵, 请等待{remaining:.0f}秒后再打喵"


class DajiaoCopy(_JJBotBase, frozen=True):
    """打胶文案上下文。"""

    delta: float = 0
    length: float = 0

    def create(self) -> str:
        return f"你还没有创建{self.jj_name}, 咱帮你创建了喵, 目前长度是10cm喵"

    def challenging(self) -> str:
        return f"你的{self.jj_name}长度在任务范围内，不允许打胶，请专心与群友pk！"

    def finish(self) -> str:
        return f"打胶结束喵, 你的{self.jj_name}很满意喵, 长了{self.delta}cm喵, 目前长度为{self.length}cm喵"

    def trigger_challenge(self) -> str:
        return (
            f"打胶结束喵, 你的{self.jj_name}很满意喵, 长了{self.delta}cm喵"
            f"\n由于你无休止的打胶，触犯到了神秘的禁忌，"
            f"{self.botname}检测到你的{self.jj_name}长度超过25cm，"
            f'已为你开启✨"登神长阶"✨'
            f'\n你现在的获胜概率变为当前的80%，且无法使用"打胶"与"嗦"指令，'
            f"请以将{self.jj_name}长度提升至30cm为目标与他人pk吧！"
        )


def suo_cd(*, remaining: float) -> str:
    """CD 冷却提示（独立上下文）。"""
    return f"你已经嗦不动了喵, 请等待{remaining:.0f}秒后再嗦喵"


class SuoCopy(_JJBotBase, frozen=True):
    """嗦牛子文案上下文。"""

    pronoun: str
    delta: float = 0
    length: float = 0

    def create(self) -> str:
        return f"{self.pronoun}还没有创建{self.jj_name}喵, 咱帮{self.pronoun}创建了喵, 目前长度是10cm喵"

    def challenging(self) -> str:
        return (
            f"{self.pronoun}的{self.jj_name}长度在任务范围内，不准嗦！请专心与群友pk！"
        )

    def finish(self) -> str:
        return f"{self.pronoun}的{self.jj_name}很满意喵, 嗦长了{self.delta}cm喵, 目前长度为{self.length}cm喵"

    def trigger_challenge(self) -> str:
        return (
            f"{self.pronoun}的{self.jj_name}很满意喵, 嗦长了{self.delta}cm喵"
            f"\n由于{self.pronoun}无休止的嗦与被嗦，触犯到了神秘的禁忌，"
            f"{self.botname}检测到{self.pronoun}的{self.jj_name}长度超过25cm，"
            f'\n已为{self.pronoun}开启✨"登神长阶"✨，'
            f"{self.pronoun}现在的获胜概率变为80%，且无法使用"
            f'"打胶"与"嗦"指令，请以将{self.jj_name}长度提升至30cm为目标与他人pk吧！'
        )


class QueryCopy(_JJBase, frozen=True):
    """查询文案上下文。不需要 botname，直接继承 _JJBase。"""

    pronoun: str
    length: float = 0
    prob: float = 0.5

    def _prob_text(self) -> str:
        return f"\n{self.pronoun}的当前胜率为{self.prob * 100:.0f}%"

    def create(self) -> str:
        return f"{self.pronoun}还没有创建{self.jj_name}喵, 咱帮{self.pronoun}创建了喵, 目前长度是10cm喵"

    def god(self) -> str:
        return f"✨牛々の神✨\n{self.pronoun}的{self.jj_name}目前长度为{self.length}cm喵{self._prob_text()}"

    def normal(self) -> str:
        return f"{self.pronoun}的{self.jj_name}目前长度为{self.length}cm喵{self._prob_text()}"

    def near_girl(self) -> str:
        return f"{self.pronoun}快要变成女孩子啦！\n{self.pronoun}的{self.jj_name}目前长度为{self.length}cm喵{self._prob_text()}"


# endregion

# region 负值成长


def kaikou_cd(*, remaining: float) -> str:
    """CD 冷却提示（独立上下文）。"""
    return f"你已经扣不动了喵, 请等待{remaining:.0f}秒后再扣喵"


class KaikouCopy(_HoleBotBase, frozen=True):
    """挖矿文案上下文。"""

    delta: float = 0
    depth: float = 0

    def challenging(self) -> str:
        return "深渊的试炼尚未结束！请专心与群友去磨豆腐吧喵！"

    def finish(self) -> str:
        return f"挖矿结束喵, 你的{self.hole_name}很满意喵, 挖深了{self.delta}cm喵, 目前深度为{self.depth}cm喵"

    def trigger_challenge(self) -> str:
        return (
            f"挖矿结束喵, 你的{self.hole_name}很满意喵, 挖深了{self.delta}cm喵"
            f"\n深渊在凝视你……{self.botname}检测到你的{self.hole_name}深度超过25cm，"
            f"已为你开启🕳️「深渊试炼」🕳️"
            f'\n你现在的获胜概率变为当前的80%，且无法使用"挖矿"与"舔"指令，'
            f"请以将{self.hole_name}深度提升至30cm为目标与他人pk吧！"
        )


def tian_cd(*, remaining: float) -> str:
    """CD 冷却提示（独立上下文）。"""
    return f"你已经舔不动了喵, 请等待{remaining:.0f}秒后再舔喵"


class TianCopy(_HoleBotBase, frozen=True):
    """舔小学文案上下文。"""

    pronoun: str
    delta: float = 0
    depth: float = 0

    def challenging(self) -> str:
        return "深渊的试炼尚未结束！请专心与群友磨豆腐喵！"

    def finish(self) -> str:
        return f"{self.pronoun}的{self.hole_name}很满意喵, 舔深了{self.delta}cm喵, 目前深度为{self.depth}cm喵"

    def trigger_challenge(self) -> str:
        return (
            f"{self.pronoun}的{self.hole_name}很满意喵, 舔深了{self.delta}cm喵"
            f"\n深渊在凝视{self.pronoun}……{self.botname}检测到{self.pronoun}的{self.hole_name}深度超过25cm，"
            f"\n已为{self.pronoun}开启🕳️「深渊试炼」🕳️，"
            f"{self.pronoun}现在的获胜概率变为80%，且无法使用"
            f'"挖矿"与"舔"指令，请以将{self.hole_name}深度提升至30cm为目标与他人pk吧！'
        )


class NegQueryCopy(_HoleBase, frozen=True):
    """负值查询文案上下文。不需要 botname，直接继承 _HoleBase。"""

    pronoun: str
    depth: float = 0
    prob: float = 0.5

    def _prob_text(self) -> str:
        return f"\n{self.pronoun}的当前胜率为{self.prob * 100:.0f}%"

    def abyss_lord(self) -> str:
        """深渊之主称号。"""
        return f"🕳️深淵の主🕳️\n{self.pronoun}的{self.hole_name}目前深度为{self.depth}cm喵{self._prob_text()}"

    def girl(self) -> str:
        """一般负值 / 浅负值（统一显示\"\u5973\u5b69\u5b50\"\uff09。"""
        return f"{self.pronoun}已经是女孩子啦！\n{self.pronoun}的{self.hole_name}目前深度为{self.depth}cm喵{self._prob_text()}"


# endregion
