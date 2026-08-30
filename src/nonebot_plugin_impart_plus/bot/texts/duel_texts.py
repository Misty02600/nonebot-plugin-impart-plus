"""对决相关文案（正值 + 负值）。"""

from __future__ import annotations

import random

from .progression_texts import _HoleBotBase, _JJBotBase

# region 正值 PK


def pk_cd(*, remaining: float) -> str:
    """CD 冷却提示（独立上下文）。"""
    return f"你已经pk不动了喵, 请等待{remaining:.0f}秒后再pk喵"


class PkCopy(_JJBotBase, frozen=True):
    """PK 文案上下文。构造一次，所有结果/挑战消息共享同一组参数。"""

    jj_name2: str = ""
    inc: float = 0
    dec: float = 0
    prob: float = 0
    bonus: float = 1.0

    def create(self) -> str:
        return f"你或对面还没有创建{self.jj_name}喵, 咱帮忙创建了喵, 初始{self.jj_name2}长度为10cm喵"

    @property
    def _is_upset(self) -> bool:
        return self.bonus > 1.0

    def win(self) -> str:
        if self._is_upset:
            return random.choice(
                [
                    f"对决胜利喵, 你的{self.jj_name}以弱胜强击败了对手, 增加了{self.inc}cm喵, 对面则在你的阴影笼罩下减小了{self.dec}cm喵",
                    f"对决胜利喵, 在危急时刻你的{self.jj_name}化险为夷, 增加了{self.inc}cm喵, 对面则在你的阴影笼罩下减小了{self.dec}cm喵",
                    f"对决胜利喵, 你的{self.jj_name}爆发出惊人的力量, 增加了{self.inc}cm喵, 对面则在你的阴影笼罩下减小了{self.dec}cm喵",
                    f"对决胜利喵, 对面大意了没有闪, 你的{self.jj_name}趁势增加了{self.inc}cm喵, 对面则在你的阴影笼罩下减小了{self.dec}cm喵",
                ]
            )
        return f"对决胜利喵, 你的{self.jj_name}增加了{self.inc}cm喵, 对面则在你的阴影笼罩下减小了{self.dec}cm喵"

    def lose(self) -> str:
        if self._is_upset:
            return random.choice(
                [
                    f"对决失败喵, 对面的{self.jj_name2}以弱胜强击败了你, 在对面{self.jj_name2}的阴影笼罩下，你的{self.jj_name}减小了{self.dec}cm喵, 对面增加了{self.inc}cm喵",
                    f"对决失败喵, 对面的{self.jj_name2}在绝境中逆袭, 在对面{self.jj_name2}的阴影笼罩下，你的{self.jj_name}减小了{self.dec}cm喵, 对面增加了{self.inc}cm喵",
                    f"对决失败喵, 你轻敌了喵! 对面的{self.jj_name2}爆发出惊人的力量, 在对面{self.jj_name2}的阴影笼罩下，你的{self.jj_name}减小了{self.dec}cm喵, 对面增加了{self.inc}cm喵",
                ]
            )
        return (
            f"对决失败喵, 在对面{self.jj_name2}的阴影笼罩下"
            f"你的{self.jj_name}减小了{self.dec}cm喵, "
            f"对面增加了{self.inc}cm喵"
        )

    def probability(self) -> str:
        return f"\n你的胜率现在为{self.prob:.0%}喵"

    # region 自己的状态

    def self_challenge_start(self) -> str:
        return (
            f"\n{self.botname}检测到你的{self.jj_name}长度超过25cm，"
            f'已为你开启✨"登神长阶"✨'
            f'\n你现在的获胜概率变为当前的80%，且无法使用"打胶"与"嗦"指令，'
            f"请以将{self.jj_name2}长度提升至30cm为目标与他人pk吧!"
        )

    def self_challenge_success(self) -> str:
        return (
            f"\n🎉恭喜你完成登神挑战🎉\n你的{self.jj_name}长度已超过30cm，"
            f'授予你🎊"牛々の神"🎊称号'
            f'\n你的获胜概率已恢复，"打胶"与"嗦"指令已重新开放，'
            f"切记不忘初心，继续冲击更高的境界喵！"
        )

    def self_challenge_failed(self) -> str:
        return (
            "\n很遗憾，登神挑战失败，别气馁啦！"
            f"\n你的{self.jj_name}长度缩短了5cm喵，获胜概率已恢复，"
            f'"打胶"与"嗦"指令已重新开放喵！'
        )

    def self_fall(self) -> str:
        return f"\n很遗憾，你跌落神坛，别气馁啦！\n你的{self.jj_name}长度缩短了5cm喵，请不忘初心，再次冲击更高的境界喵！"

    # endregion

    # region 对方的状态

    def opp_challenge_failed(self) -> str:
        return (
            f"\n由于你对决的胜利，{self.botname}检测到TA的{self.jj_name}长度已不足25cm，"
            f"很遗憾，TA的登神挑战失败，{self.botname}替TA感谢你的鞭策喵！"
            f"\nTA的{self.jj_name2}长度缩短了5cm喵，获胜概率已恢复，"
            f'"打胶"与"嗦"指令已重新开放喵！'
        )

    def opp_fall(self) -> str:
        return (
            f"\n由于你对决的胜利，{self.botname}检测到TA的{self.jj_name}长度已不足25cm，"
            f"很遗憾，TA跌落神坛，{self.botname}替TA感谢你的鞭策喵！"
            f"\nTA的{self.jj_name2}长度缩短了5cm喵，请不忘初心，再次冲击更高的境界喵！"
        )

    def opp_challenge_start(self) -> str:
        return (
            f"\n由于你对决的失败，触犯到了神秘的禁忌，"
            f"{self.botname}检测到TA的{self.jj_name}长度超过25cm，"
            f'已为TA开启✨"登神长阶"✨'
            f'\n现在TA的获胜概率变为当前的80%，且无法使用"打胶"与"嗦"指令，'
            f"请通知TA以将{self.jj_name2}长度提升至30cm为目标与群友pk吧！"
        )

    def opp_challenge_success(self) -> str:
        return (
            f"\n🎉恭喜你帮助TA完成登神挑战🎉\nTA的{self.jj_name}长度超过30cm，"
            f'授予TA🎊"牛々の神"🎊称号'
            f'\nTA的获胜概率已恢复，"打胶"与"嗦"指令已重新开放，'
            f"请提醒TA不忘初心，继续冲击更高的境界喵！"
        )

    # endregion


# endregion

# region 负值 PK


class NegPkCopy(_HoleBotBase, frozen=True):
    """负值 PK 文案上下文。构造一次，所有结果/挑战消息共享同一组参数。"""

    hole_name2: str = ""
    inc: float = 0
    dec: float = 0
    prob: float = 0
    bonus: float = 1.0

    @property
    def _is_upset(self) -> bool:
        return self.bonus > 1.0

    # TODO 此处文案还需要优化，不要全是深渊抽象，由于是女同磨豆腐/互扣，可以具现一点，像牛子pk那样

    def win(self) -> str:
        if self._is_upset:
            return random.choice(
                [
                    f"对决胜利喵, 你的{self.hole_name}在绝境中觉醒, 加深了{self.inc}cm喵, 对面在你的吞噬下变浅了{self.dec}cm喵",
                    f"对决胜利喵, 深渊回应了你的呼唤, 你的{self.hole_name}加深了{self.inc}cm喵, 对面变浅了{self.dec}cm喵",
                    f"对决胜利喵, 黑暗中你的{self.hole_name}蚕食了对手, 加深了{self.inc}cm喵, 对面变浅了{self.dec}cm喵",
                    f"对决胜利喵, 对面小看了深渊的力量, 你的{self.hole_name}加深了{self.inc}cm喵, 对面变浅了{self.dec}cm喵",
                ]
            )
        return f"对决胜利喵, 你的{self.hole_name}加深了{self.inc}cm喵, 对面则在你的吞噬下变浅了{self.dec}cm喵"

    def lose(self) -> str:
        if self._is_upset:
            return random.choice(
                [
                    f"对决失败喵, 对面的{self.hole_name2}在绝境中觉醒, 你的{self.hole_name}变浅了{self.dec}cm喵, 对面加深了{self.inc}cm喵",
                    f"对决失败喵, 深渊回应了对面的呼唤, 你的{self.hole_name}变浅了{self.dec}cm喵, 对面加深了{self.inc}cm喵",
                    f"对决失败喵, 你轻敌了喵! 对面的{self.hole_name2}从黑暗中反噬, 你的{self.hole_name}变浅了{self.dec}cm喵, 对面加深了{self.inc}cm喵",
                ]
            )
        return f"对决失败喵, 在对面的侵蚀下你的{self.hole_name}变浅了{self.dec}cm喵, 对面加深了{self.inc}cm喵"

    def probability(self) -> str:
        return f"\n你的pk胜率现在为{self.prob:.0%}喵"

    # region 自己的状态

    def self_challenge_start(self) -> str:
        return (
            f"\n{self.botname}检测到你的{self.hole_name}深度超过25cm，"
            f"已为你开启🕳️「坠入深渊」🕳️"
            f'\n你现在的获胜概率变为当前的80%，且无法使用"挖矿"与"舔"指令，'
            f"请以将{self.hole_name}深度提升至30cm为目标与他人pk吧！"
        )

    def self_challenge_success(self) -> str:
        return (
            f"\n🎉恭喜你完成深渊挑战🎉\n你的{self.hole_name}深度已超过30cm，"
            f'授予你🎊"深淵の主"🎊称号'
            f'\n你的获胜概率已恢复，"挖矿"与"舔"指令已重新开放，'
            f"继续探索更深的深渊吧喵！"
        )

    def self_challenge_failed(self) -> str:
        return (
            "\n很遗憾，深渊挑战失败，别气馁啦！"
            f"\n你的{self.hole_name}深度减少了5cm喵，获胜概率已恢复，"
            f'"挖矿"与"舔"指令已重新开放喵！'
        )

    def self_fall(self) -> str:
        return f"\n很遗憾，你从深渊边缘跌落了，别气馁啦！\n你的{self.hole_name}深度减少了5cm喵，请再次向深渊进发吧喵！"

    # endregion

    # region 对方的状态

    def opp_challenge_failed(self) -> str:
        return (
            f"\n由于你对决的胜利，{self.botname}检测到TA的{self.hole_name}深度已不足25cm，"
            f"深渊拒绝了弱者……TA的深渊挑战失败，{self.botname}替TA感谢你的鞭策喵！"
            f"\nTA的{self.hole_name2}深度减少了5cm喵，获胜概率已恢复，"
            f'"挖矿"与"舔"指令已重新开放喵！'
        )

    def opp_fall(self) -> str:
        return (
            f"\n由于你对决的胜利，{self.botname}检测到TA的{self.hole_name}深度已不足25cm，"
            f"深渊拒绝了弱者……TA从深渊边缘跌落了，{self.botname}替TA感谢你的鞭策喵！"
            f"\nTA的{self.hole_name2}深度减少了5cm喵，请通知TA再次向深渊进发吧喵！"
        )

    def opp_challenge_start(self) -> str:
        return (
            f"\n由于你对决的失败，深渊的力量在涌动，"
            f"{self.botname}检测到TA的{self.hole_name}深度超过25cm，"
            f"已为TA开启🕳️「坠入深渊」🕳️"
            f'\n现在TA的获胜概率变为当前的80%，且无法使用"挖矿"与"舔"指令，'
            f"请通知TA以将{self.hole_name2}深度提升至30cm为目标与群友pk吧！"
        )

    def opp_challenge_success(self) -> str:
        return (
            f"\n🎉恭喜你帮助TA完成深渊挑战🎉\nTA的{self.hole_name}深度超过30cm，"
            f'授予TA🎊"深淵の主"🎊称号'
            f'\nTA的获胜概率已恢复，"挖矿"与"舔"指令已重新开放，'
            f"请提醒TA继续探索更深的深渊吧喵！"
        )

    # endregion


# endregion
