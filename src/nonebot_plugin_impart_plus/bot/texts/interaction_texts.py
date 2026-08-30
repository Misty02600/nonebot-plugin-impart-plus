"""群交互、跨状态提示与事件播报文案。"""

from __future__ import annotations

from pydantic import BaseModel

# region 透群友（正值世界）


class YinpaMenuCopy(BaseModel, frozen=True):
    """透群友菜单文案上下文。新增字段后所有菜单方法自动可用。"""

    botname: str = ""
    user_card: str = ""
    target_card: str = ""

    def member(self) -> str:
        return f"现在咱将随机抽取一位幸运群友\n送给{self.user_card}色色！"

    def reverse_member(self) -> str:
        return f"{self.botname}发现你是xnn~现在咱将{self.user_card}\n送给{self.target_card}色色！"

    def xnn_both(self) -> str:
        return f"{self.botname}发现你俩都是xnn喵~现在咱将{self.user_card}\n送给{self.target_card}色色！"

    def owner(self) -> str:
        return f"现在咱将把群主\n送给{self.user_card}色色！"

    def admin(self) -> str:
        return f"现在咱将随机抽取一位幸运管理\n送给{self.user_card}色色！"

    def reverse_owner(self) -> str:
        return f"{self.botname}发现你是xnn~现在咱将{self.user_card}\n送给群主色色！"

    def reverse_admin(self) -> str:
        return f"{self.botname}发现你是xnn~现在咱将{self.user_card}\n送给随机一位管理色色！"


class YinpaReport(BaseModel, frozen=True):
    """透群友结算上下文。构造一次即可调用各场景方法。"""

    req_user_card: str
    uid: int
    seconds: int
    target_card: str
    target_id: str
    ejaculation: float
    today_total: float

    def active(self) -> str:
        """主动方视角：发起者 → 目标 注入。"""
        return (
            f"好欸！{self.req_user_card}({self.uid})用时{self.seconds}秒 \n"
            f"给 {self.target_card}({self.target_id}) "
            f"注入了{self.ejaculation}毫升的脱氧核糖核酸, "
            f"当日总注入量为：{self.today_total}毫升\n"
        )

    def reversed(self) -> str:
        """被动方视角：目标 → 发起者 反向注入。"""
        return (
            f"好欸！{self.target_card}({self.target_id})用时{self.seconds}秒 \n"
            f"给 {self.req_user_card}({self.uid}) "
            f"注入了{self.ejaculation}毫升的脱氧核糖核酸, "
            f"当日总注入量为：{self.today_total}毫升\n"
        )

    def squeeze(self) -> str:
        """被反手榨到腿软的结算文案。"""
        return (
            f"好欸！{self.target_card}({self.target_id})用时{self.seconds}秒 \n"
            f"把 {self.req_user_card}({self.uid}) 榨到腿软, "
            f"榨出了{self.ejaculation}毫升的精华, "
            f"当日总注入量为：{self.today_total}毫升\n"
        )

    def xnn_both(
        self,
        *,
        reverse_ejaculation: float,
        self_total: float,
        target_total: float,
    ) -> str:
        """两个 xnn 互透的结算。双方各自注入对方。"""
        return (
            f"好欸！{self.req_user_card}({self.uid})和"
            f"{self.target_card}({self.target_id})"
            f"贴贴蹭蹭了{self.seconds}秒\n"
            f"{self.req_user_card}给{self.target_card}"
            f"注入了{self.ejaculation}毫升， "
            f"{self.target_card}也给{self.req_user_card}"
            f"注入了{reverse_ejaculation}毫升，"
            f"当日总注入量分别为：{self_total}毫升、{target_total}毫升\n"
        )


def zha_no_male_target() -> str:
    """榨群友找不到男性目标时的提示。"""
    return "找不到男孩子送给你涩涩了喵，群友全是白河豚喵~"


# endregion

# region 榨群友（負値）


class ZhaMenuCopy(BaseModel, frozen=True):
    """榨群友菜单文案上下文。"""

    user_card: str = ""

    def member(self) -> str:
        return f"现在咱将随机抽取一位幸运群友\n送给{self.user_card}榨汁！"

    def owner(self) -> str:
        return f"现在咱将把群主\n送给{self.user_card}榨汁！"

    def admin(self) -> str:
        return f"现在咱将随机抽取一位幸运管理\n送给{self.user_card}榨汁！"


class ZhaReport(BaseModel, frozen=True):
    """榨群友结算上下文。"""

    req_user_card: str
    uid: int
    seconds: int
    target_card: str
    target_id: str
    ejaculation: float
    today_total: float

    def finish(self) -> str:
        """正常榨汁结算。"""
        return (
            f"好欸！{self.req_user_card}({self.uid})用时{self.seconds}秒\n"
            f"把 {self.target_card}({self.target_id}) "
            f"榨出了{self.ejaculation}毫升的脱氧核糖核酸, "
            f"当日总注入量为：{self.today_total}毫升\n"
        )


# endregion

# region 跨状态提示与事件


class CiduoEvent(BaseModel, frozen=True):
    """雌堕事件播报上下文。"""

    user_card: str
    uid: int
    req_user_card: str
    depth: float
    jj_name: str
    hole_name: str

    def announce(self) -> str:
        """雌堕发生时的播报。"""
        return (
            f"\n{self.user_card}({self.uid})被注入了太多脱氧核糖核酸..."
            f"\n在{self.req_user_card}的猛烈攻势下，"
            f"{self.user_card}的{self.jj_name}彻底萎缩消失了♡"
            f"\n取而代之的是一个深度{self.depth}cm的{self.hole_name}♡"
            f"\n{self.user_card}已经完全雌堕, 变成了女孩子♡"
        )


def xnn_enter() -> str:
    """进入 xnn 状态时的完整提示（含 debuff 信息）。"""
    return (
        "\n你醒啦, 你已经变成xnn了！"
        "\n你当前的对决胜率减少50%，对决失败扣除增加50%"
        "\n你可以通过打胶或对决挣脱，亦或者...成为群友的rbq？"
    )


# TODO 退出的文案不太好，有待优化


def xnn_self_exit() -> str:
    """自己挣脱 xnn 状态提示。"""
    return "\n恭喜你成功挣脱了xnn状态喵！"


def xnn_opp_enter() -> str:
    """对方进入 xnn 状态提示。"""
    return "\n对方已经变成xnn了喵！"


def xnn_opp_exit() -> str:
    """对方挣脱 xnn 状态提示。"""
    return "\n对方已挣脱xnn状态喵！"


# TODO 和wrong_world_negative风格一致
def wrong_world_positive() -> str:
    """正值玩家使用负值指令时的提示。"""
    return "你还不是女孩子哦~"


def wrong_world_negative(jj_name: str = "牛子") -> str:
    """负值玩家使用正值指令时的提示。"""
    return f"你没有{jj_name}喵，请使用「开扣/挖矿」指令喵"


def wrong_world_use_zha(jj_name: str) -> str:
    """负值玩家尝试使用日/透时的提示。"""
    return f"你没有{jj_name}喵，请使用「榨群友」指令"


def pk_self_target() -> str:
    """PK @自己时的提示。"""
    return "你不能pk自己喵"


def pk_positive_only() -> str:
    """击剑仅限正值玩家提示。"""
    return "女生请使用「磨豆腐/磨」或「pk/对决」喵"


def pk_negative_only() -> str:
    """磨豆腐仅限负值玩家提示。"""
    return "男生请使用「击剑」或「pk/对决」喵"


# TODO 对于对方不符合Pk性别的文案呢，可以说对方没有jj/hole，不能pk


def suo_target_negative(*, pronoun: str, jj_name: str) -> str:
    """嗦目标处于负值世界时的提示。"""
    return f"{pronoun}是女生，没有{jj_name}可以嗦喵"


# TODO 男生也要说没有hole可以舔喵。此外把所有男孩子女孩子改为男生女生


def tian_target_not_negative(*, pronoun: str) -> str:
    """舔目标不在负值世界时的提示。"""
    return f"{pronoun}是男生，不能舔喵~"


def pk_same_camp_fail() -> str:
    """PK 同阵营检查失败：正负值不能跨世界 PK。"""
    return "你们不在同一个世界喵！"


def target_not_found(*, action: str) -> str:
    """透/榨未找到可用目标时的提示。"""
    if action == "榨":
        return "找不到可以榨的目标喵~"
    return "找不到可以下手的目标喵~"


def self_target_owner(*, action: str) -> str:
    """群主命令目标为自己时的提示。"""
    if action == "榨":
        return "你榨你自己?"
    return "你透你自己?"


def no_admin_target(*, action: str) -> str:
    """管理命令找不到可选管理时的提示。"""
    if action == "榨":
        return "喵喵喵 找不到可榨的群管理!"
    return "喵喵喵 找不到群管理!"


# endregion
