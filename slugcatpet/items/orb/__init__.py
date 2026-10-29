"""珍珠：雨世界的数据珍珠，小小的、会偶尔闪一下光的球。

贴图照原作逐格现画（见 palette.py 里的 11×11 模板），不引用任何游戏素材：
黑描边 + 本色平涂 + 本色压暗的内缘环，没有高光、没有渐变、没有漩涡。
颜色每次生成时从官方彩色珍珠色表里随机抽一颗，白珍珠最常见（原作大多数珍珠是白的）。
"""

from __future__ import annotations

import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen

from ..base import CARRYABLE, THROWABLE, ItemKind
from ..state import ItemState
from .model import FOLLOW as FOLLOW, TOY, Orb  # FOLLOW 是转出去给窗口用的
from .palette import GOLD, N_COLORS, RUNS_BODY, RUNS_OUTLINE, RUNS_SHADE, WHITE, body_rgb, shade_rgb

# 放置
CAP = 6
HIT_PAD = 10.0  # 光标点到它的判定余量（双击 / 右键切换形态）

# 白珍珠最常见：原作里绝大多数珍珠都是白的，彩色珍珠才各自固定在一个地点
WHITE_W = 0.55

_rng = random.Random(0x5EED1)


def draw_pearl(p: QPainter, cx: float, cy: float, rad: float, pal_i: int, alpha: float = 1.0) -> None:
    """按原作的 11×11 格模板画一颗珍珠。"""
    if alpha <= 0.0:
        return
    cell = rad * 2.0 / 11.0
    x0, y0 = cx - rad, cy - rad
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    # 像素块关掉抗锯齿才对味，不然格子之间会糊出缝
    p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    if alpha < 1.0:
        p.setOpacity(alpha)
    for runs, col in (
        (RUNS_OUTLINE, (0, 0, 0)),
        (RUNS_SHADE, shade_rgb(pal_i)),
        (RUNS_BODY, body_rgb(pal_i)),
    ):
        p.setBrush(QBrush(QColor(*col)))
        for gx, gy, gw in runs:
            # 每格稍微胀一点点，避免相邻格子之间露出背景缝
            p.drawRect(QRectF(x0 + gx * cell, y0 + gy * cell, gw * cell + 0.5, cell + 0.5))
    p.restore()


def draw_sparkle(p: QPainter, cx: float, cy: float, rad: float, u: float) -> None:
    """闪一下的光：四道白色短光芒，点在珍珠左上边缘上。u = 0 刚亮起 → 1 已经没了。"""
    a = 1.0 - u
    if a <= 0.0:
        return
    lv = rad * (1.5 - 0.7 * u)
    lh = lv * 0.6
    sx, sy = cx - rad * 0.8, cy - rad * 0.8
    p.save()
    p.setPen(
        QPen(
            QColor(255, 255, 255, int(215 * a)),
            max(1.0, rad * 0.24),
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
        )
    )
    p.drawLine(QPointF(sx, sy - lv), QPointF(sx, sy + lv))
    p.drawLine(QPointF(sx - lh, sy), QPointF(sx + lh, sy))
    p.restore()


def _pick_color() -> int:
    """随机抽一颗珍珠的颜色；白的概率高得多。"""
    if _rng.random() < WHITE_W:
        return WHITE
    return _rng.randrange(1, N_COLORS)


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
        return Orb(lx, ly, seed=seed, pal_i=_pick_color())

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
            draw_pearl(p, x, y, o.rad, o.pal_i, a)
            sp = o.spark_progress()
            if sp >= 0.0:
                draw_sparkle(p, x, y, o.rad, sp)

    def draw_hint(self, win, p, cx, cy):
        p.save()
        p.setOpacity(0.55)
        draw_pearl(p, cx, cy, Orb(0, 0).rad, GOLD, 1.0)
        p.restore()

    def paint_icon(self, p, r, atlas):
        cx, cy = r.center().x(), r.center().y()
        rad = min(r.width(), r.height()) * 0.22
        draw_pearl(p, cx, cy, rad, GOLD, 1.0)


KIND = OrbKind()


def set_mode(o, mode):
    """切换玩具型 / 跟随型。切回玩具型时原地松手，让它自己掉下去。"""
    if o.mode == mode:
        return
    o.mode = mode
    if mode == TOY:
        o.goal = None
        o.vx *= 0.3
        o.vy = min(o.vy, 0.0)


def orb_at(win, pos):
    """光标下的一颗珍珠；没有返回 None。"""
    best, bd = None, None
    for o in win.orbs:
        if o.state == ItemState.GONE:
            continue
        d = math.hypot(pos[0] - o.x, pos[1] - o.y) - o.rad
        if d <= HIT_PAD and (bd is None or d < bd):
            best, bd = o, d
    return best
