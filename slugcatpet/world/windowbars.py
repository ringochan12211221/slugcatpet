"""窗口虚拟杆：把屏幕上的窗口边框变成猫能爬的杆。

杆是虚拟的：不进物品栏、不可移除、不占上限、不存档，也不画出来（窗口自己的边框就是它）。
只要它们出现在 win.items_affording(CLIMBABLE) 里，planning/climbmap.py 的杆网寻路
就会把窗口算进路线，于是**所有猫**都能顺着窗口侧边爬到顶上（不只是圣徒）。

几何：
- 左右侧 → 竖杆，从窗口顶一直落到地面（这样猫走过去就能抓到，不需要跳），grounded
- 顶边、底边 → 悬空横杆；底边离地太近就不生成（和地面重复）
- 窗口重叠：只保留没被更上层窗口盖住的那一段（最外缘）
"""

from __future__ import annotations

MIN_SEG = 60.0  # 短于这个的边框段不算（猫站不住）
BOTTOM_CLEAR = 40.0  # 底边离地不足这么多就不生成
MAX_WINDOWS = 24  # 最多处理这么多个窗口
MAX_BARS = 20
TOL = 0.5


class EdgePole:
    """一根窗口边生成的虚拟杆；字段和 items/pole 的 Pole 对齐，够 climbmap 用。"""

    __slots__ = ("kind", "ax", "ay", "bx", "by", "state", "grounded", "has_been_climbed")

    def __init__(self, kind, ax, ay, bx, by, grounded):
        self.kind = "vertical" if kind == "vertical" else "horizontal"
        self.ax, self.ay = float(ax), float(ay)
        self.bx, self.by = float(bx), float(by)
        self.state = "free"
        self.grounded = bool(grounded)
        self.has_been_climbed = False

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
        left, right = max(0.0, left), min(WL, right)
        top, bottom = max(0.0, top), min(HL, bottom)
        boxes.append((left, top, right, bottom))

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

        top_seg = _long_enough(top_seg, MIN_SEG)
        bot_seg = _long_enough(bot_seg, MIN_SEG)
        left_seg = _long_enough(left_seg, MIN_SEG)
        right_seg = _long_enough(right_seg, MIN_SEG)

        for segs, x in ((left_seg, left), (right_seg, right)):
            if not segs:
                continue
            y_top = min(s for s, _ in segs)
            if HL - y_top < MIN_SEG:
                continue
            # 从地面一路到窗口顶：猫走过去就能抓到
            out.append(EdgePole("vertical", x, y_top, x, HL, True))

        for segs, y in ((top_seg, top),):
            for s, e in segs:
                out.append(EdgePole("horizontal", s, y, e, y, False))
        if HL - bottom >= BOTTOM_CLEAR:
            for s, e in bot_seg:
                out.append(EdgePole("horizontal", s, bottom, e, bottom, False))

    if len(out) > MAX_BARS:
        out.sort(key=lambda p: -(abs(p.bx - p.ax) + abs(p.by - p.ay)))
        del out[MAX_BARS:]
    return out


def signature(bars):
    return tuple(p.key() for p in bars)
