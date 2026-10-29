"""窗口虚拟杆：把屏幕上的窗口边框变成猫能爬的杆。

杆是虚拟的：不进物品栏、不可移除、不占上限、不存档，也不画出来（窗口自己的边框就是它）。
只要它们出现在 win.items_affording(CLIMBABLE) 里，planning/climbmap.py 的杆网寻路
就会把窗口算进路线，于是**所有猫**都能顺着窗口侧边爬到顶上（不只是圣徒）。

几何：**只贴真实可见的边框**，不凭空延长。
- 左右侧 → 竖杆，只覆盖没被遮住的那一段（窗口顶到窗口底）；下沿离地 ≤ GROUND_TOL
  （最大化窗口压着任务栏的情况）才接到地面，猫走过去就能抓，不用跳
- 顶边、底边 → 悬空横杆；底边离地太近就不生成（和地面重复）
- 窗口重叠：按 Z 序（枚举顺序即 Z 序，越靠前越上层）逐层挖掉被盖住的段，只留最外缘
- 屏幕外的部分直接丢掉，不把边挪到屏幕边界上——免得凭空多出一根杆
"""

from __future__ import annotations

MIN_SEG = 60.0  # 短于这个的边框段不算（猫站不住）
GROUND_TOL = 64.0  # 竖杆下沿离地这么近就接到地面（走过去就能抓）
BOTTOM_CLEAR = 28.0  # 底边离地不足这么多就不生成（约一个任务栏高，压着任务栏的窗口也算）
MAX_WINDOWS = 24  # 最多处理这么多个窗口
MAX_BARS = 20
TOL = 0.5


class EdgePole:
    """一根窗口边生成的虚拟杆；接口和 items/pole 的 Pole 对齐（缺一个属性就会在规划里抛异常）。

    竖杆的端点顺序同 Pole：ax/ay 是着地那端，bx/by 是顶端（即 top_y）。
    """

    __slots__ = ("kind", "ax", "ay", "bx", "by", "state", "grounded", "has_been_climbed")

    def __init__(self, kind, ax, ay, bx, by, grounded):
        self.kind = "vertical" if kind == "vertical" else "horizontal"
        self.ax, self.ay = float(ax), float(ay)
        self.bx, self.by = float(bx), float(by)
        self.state = "free"
        self.grounded = bool(grounded)
        self.has_been_climbed = False

    @property
    def x(self) -> float:
        return self.bx

    @property
    def top_y(self) -> float:
        return self.by

    def key(self):
        return (self.kind, round(self.ax, 1), round(self.ay, 1), round(self.bx, 1), round(self.by, 1))


def _cut(ivs, a, b):
    """从区间表里挖掉 [a, b]。"""
    if b - a <= TOL:
        return ivs
    out = []
    for s, e in ivs:
        if b <= s + TOL or a >= e - TOL:
            out.append((s, e))
            continue
        if a > s + TOL:
            out.append((s, a))
        if b < e - TOL:
            out.append((b, e))
    return out


def _long_enough(ivs, min_len):
    return [(s, e) for s, e in ivs if e - s >= min_len]


def _clip(ivs, lo, hi):
    """裁到 [lo, hi] 里，只留够长的段（出屏的部分是真看不见，不是把边挪到边界上）。"""
    return _long_enough([(max(s, lo), min(e, hi)) for s, e in ivs], MIN_SEG)


def build(rects, WL, HL):
    """窗口矩形（已换算到逻辑坐标）→ 虚拟杆列表。rects 按 Z 序，越靠前越上层。"""
    out = []
    boxes = []
    for x0, y0, x1, y1 in rects[:MAX_WINDOWS]:
        left, right = min(x0, x1), max(x0, x1)
        top, bottom = min(y0, y1), max(y0, y1)
        if right - left < MIN_SEG or bottom - top < MIN_SEG:
            continue
        if right < TOL or left > WL - TOL or bottom < TOL or top > HL - TOL:
            continue  # 整个在屏幕外
        boxes.append((left, top, right, bottom))  # 保留真实坐标，裁剪只发生在段上

    for i, (left, top, right, bottom) in enumerate(boxes):
        # 上层的窗口会把这条边盖住
        top_seg = [(left, right)]
        bot_seg = [(left, right)]
        left_seg = [(top, bottom)]
        right_seg = [(top, bottom)]
        for j in range(i):
            bl, bt, br, bb = boxes[j]
            xs = (max(left, bl), min(right, br))
            ys = (max(top, bt), min(bottom, bb))
            if bt - TOL <= top <= bb + TOL:
                top_seg = _cut(top_seg, *xs)
            if bt - TOL <= bottom <= bb + TOL:
                bot_seg = _cut(bot_seg, *xs)
            if bl - TOL <= left <= br + TOL:
                left_seg = _cut(left_seg, *ys)
            if bl - TOL <= right <= br + TOL:
                right_seg = _cut(right_seg, *ys)

        # 出屏的部分不算：段裁掉，边的 x/y 仍用真实值
        top_seg = _clip(top_seg, 0.0, WL)
        bot_seg = _clip(bot_seg, 0.0, WL)
        left_seg = _clip(left_seg, 0.0, HL)
        right_seg = _clip(right_seg, 0.0, HL)

        for segs, x in ((left_seg, left), (right_seg, right)):
            if x < -TOL or x > WL + TOL:
                continue  # 这条侧边本身在屏幕外，没有可爬的边
            for s, e in segs:  # s=顶，e=底
                grounded = HL - e <= GROUND_TOL
                foot = HL if grounded else e
                if foot - s < MIN_SEG or HL - s < MIN_SEG:
                    continue
                out.append(EdgePole("vertical", x, foot, x, s, grounded))  # ay 着地端，by 顶端

        if -TOL <= top <= HL + TOL:
            for s, e in top_seg:
                out.append(EdgePole("horizontal", s, top, e, top, False))
        if -TOL <= bottom <= HL + TOL and HL - bottom >= BOTTOM_CLEAR:
            for s, e in bot_seg:
                out.append(EdgePole("horizontal", s, bottom, e, bottom, False))

    if len(out) > MAX_BARS:
        out.sort(key=lambda p: -(abs(p.bx - p.ax) + abs(p.by - p.ay)))
        del out[MAX_BARS:]
    return out


def signature(bars):
    return tuple(p.key() for p in bars)


def merge(old, new):
    """重建时复用几何没变的那根杆对象：别的窗口移动不会让正在爬的猫脱手。"""
    if not old:
        return list(new)
    pool = {}
    for p in old:
        pool.setdefault(p.key(), []).append(p)
    out = []
    for p in new:
        same = pool.get(p.key())
        out.append(same.pop(0) if same else p)
    return out
