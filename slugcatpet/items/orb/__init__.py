"""光萤：会飘会发光的小球，猫会跑过去扑它玩；可以拿起来扔，扔出去不打光标。

画面不依赖游戏素材，用 QPainter 现画（径向渐变光晕 + 高光核心）。
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QRadialGradient

from ..base import CARRYABLE, THROWABLE, ItemKind
from ..state import ItemState
from .model import FOLLOW, TOY, Orb

# 外观
GLOW_COLOR = (140, 240, 200)  # 青绿萤光
CORE_COLOR = (245, 255, 252)
GLOW_SCALE = 2.9  # 光晕半径 = rad × 此值
GLOW_ALPHA = 92
CORE_ALPHA = 235
SPEC_RATIO = 0.34  # 左上高光相对半径
SPEC_ALPHA = 200
FOLLOW_GLOW = 1.3  # 跟随型亮一档，好认

# 放置
CAP = 6
HIT_PAD = 10.0  # 光标点到它的判定余量（双击 / 右键切换形态）

# 被猫扑到
POUNCE_MIN_SPEED = 5.0


def draw_glow_orb(p: QPainter, x: float, y: float, rad: float, glow: float, alpha: float = 1.0) -> None:
    """画一颗光萤：外圈光晕 + 实心核心 + 左上一点高光。"""
    if alpha <= 0.0:
        return
    p.save()
    p.setPen(Qt.PenStyle.NoPen)

    gr = max(1.0, rad * GLOW_SCALE)
    grad = QRadialGradient(QPointF(x, y), gr)
    c0 = QColor(*GLOW_COLOR)
    c0.setAlpha(int(GLOW_ALPHA * glow * alpha))
    c1 = QColor(*GLOW_COLOR)
    c1.setAlpha(int(GLOW_ALPHA * 0.45 * glow * alpha))
    c2 = QColor(*GLOW_COLOR)
    c2.setAlpha(0)
    grad.setColorAt(0.0, c0)
    grad.setColorAt(0.45, c1)
    grad.setColorAt(1.0, c2)
    p.setBrush(QBrush(grad))
    p.drawEllipse(QPointF(x, y), gr, gr)

    core = QColor(*CORE_COLOR)
    core.setAlpha(int(CORE_ALPHA * alpha))
    p.setBrush(QBrush(core))
    p.drawEllipse(QPointF(x, y), rad, rad)

    if rad > 2.5:
        sp = QColor(255, 255, 255)
        sp.setAlpha(int(SPEC_ALPHA * alpha))
        p.setBrush(QBrush(sp))
        sr = rad * SPEC_RATIO
        p.drawEllipse(QPointF(x - rad * 0.30, y - rad * 0.32), sr, sr)
    p.restore()


class OrbKind(ItemKind):
    key = "orb"
    store = "orbs"
    cap = CAP
    affords = frozenset({THROWABLE, CARRYABLE})
    collides = False
    grab_pad = 9.0
    grab_rank = 1
    dead_state = ItemState.GONE
    layer = "front"

    def make(self, win, lx, ly, seed):
        return Orb(lx, ly, seed=seed)

    def drop(self, win, o):
        for pet in win.pets:
            pet.body.release(o)
        o.state = ItemState.GONE

    def on_grab(self, o):
        o.fling = False
        o.thrown_by_cat = False

    def on_release(self, win, o):
        if o.state == ItemState.MOUSE:
            o.state = ItemState.FREE
            o.fling = True
        o.thrown_by_cat = False

    def tick(self, win):
        # 跟随型每 tick 记下光标在哪；玩具型用不上，留着随时能切过去
        cur = win.cursor_logical()
        for o in win.orbs:
            o.goal = cur
        super().tick(win)

    def draw(self, win, p):
        ts = win._ts
        for o in win.orbs:
            if o.state == ItemState.GONE:
                continue
            bx, by = o.bob_offset()
            x = o.last_x + (o.x - o.last_x) * ts + bx
            y = o.last_y + (o.y - o.last_y) * ts + by
            a = self.dissolve_alpha(o, ts)
            if o.vibrate > 0:
                x += (o.vibrate % 3) - 1.0
            g = o.glow_at() * (FOLLOW_GLOW if o.mode == FOLLOW else 1.0)
            draw_glow_orb(p, x, y, o.rad, g, a)

    def draw_hint(self, win, p, cx, cy):
        p.save()
        p.setOpacity(0.55)
        draw_glow_orb(p, cx, cy, Orb(0, 0).rad, 1.0, 1.0)
        p.restore()

    def paint_icon(self, p, r, atlas):
        cx, cy = r.center().x(), r.center().y()
        rad = min(r.width(), r.height()) * 0.26
        draw_glow_orb(p, cx, cy, rad, 1.0, 1.0)
        p.setPen(QPen(QColor(*GLOW_COLOR, 200), max(1.2, rad * 0.22)))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), rad * 1.75, rad * 1.75)


KIND = OrbKind()


def set_mode(o, mode):
    """切换玩具型 / 跟随型。切回玩具型时原地松手，让它自己飘下去。"""
    if o.mode == mode:
        return
    o.mode = mode
    if mode == TOY:
        o.goal = None
        o.vx *= 0.3
        o.vy = min(o.vy, 0.0)


def orb_at(win, pos):
    """光标下的一颗光萤；没有返回 None。"""
    best, bd = None, None
    for o in win.orbs:
        if o.state == ItemState.GONE:
            continue
        d = math.hypot(pos[0] - o.x, pos[1] - o.y) - o.rad
        if d <= HIT_PAD and (bd is None or d < bd):
            best, bd = o, d
    return best
