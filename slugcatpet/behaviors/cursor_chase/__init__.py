"""追光标：光标停住不动、离得不近不远时，按好感度缩放的概率跑过去看看。"""

from __future__ import annotations

from types import SimpleNamespace

from ...abilities.base import Param
from ...brain.fsm import _lerpmap
from ...brain.state import LIGHT, T_ACTIVITY
from ..base import Behavior

GIVEUP_SPEED_MULT = 3.0  # 光标速度超过 still_speed 的这么多倍就放弃


def _temper(temper, lo, hi):
    """好感 -1 → lo，+1 → hi，中间线性。"""
    return _lerpmap(temper, -1.0, 1.0, lo, hi)


class CursorChase(Behavior):
    key = "cursor_chase"
    title = {"zh": "追光标", "en": "Cursor chase"}
    doc = (
        "光标停住不动、离得不近不远时，按好感度缩放的概率跑过去：好感 -1 时很少搭理你，+1 时很勤快；"
        "追到就在光标下面待一会儿。只跑过去，不抢光标；困了、累了、被拎着都不追。"
    )
    params = {
        "check_every": Param(48, 4, 100000, "每隔几 tick 掷一次骰（40 tick = 1 秒）"),
        "chance": Param(0.35, 0.0, 1.0, "好感 0 时每次掷骰的命中率"),
        "temper_lo": Param(0.15, 0.0, 5.0, "好感 -1 时的概率倍率"),
        "temper_hi": Param(1.80, 0.0, 5.0, "好感 +1 时的概率倍率"),
        "sleepy_damp": Param(0.80, 0.0, 1.0, "困意压制：1 为困到头时完全不想追"),
        "still_ticks": Param(24, 0, 100000, "光标至少停这么久才考虑追"),
        "still_speed": Param(6.0, 0.0, 200.0, "光标每 tick 位移小于此算没动（px）"),
        "near_frac": Param(0.15, 0.0, 1.0, "比屏宽 × 此值还近就不追"),
        "far_frac": Param(0.60, 0.0, 1.0, "比屏宽 × 此值还远就懒得去"),
        "arrive_pad": Param(44.0, 0.0, 1000.0, "水平距离小于此算追到了（px）"),
        "linger": Param(60, 0, 100000, "追到后待这么久再收工（tick）"),
        "timeout": Param(160, 1, 100000, "最多追这么久（tick）"),
        "cooldown_lo": Param(800, 0, 1000000, "好感 0 时收工冷却下限（tick，800 = 20 秒）"),
        "cooldown_hi": Param(1600, 0, 1000000, "好感 0 时收工冷却上限（tick，1600 = 40 秒）"),
        "cooldown_temper_lo": Param(1.8, 0.0, 10.0, "好感 -1 时冷却倍率"),
        "cooldown_temper_hi": Param(0.6, 0.0, 10.0, "好感 +1 时冷却倍率"),
    }

    def mount(self, fsm):
        _mount(fsm, self.p)


def _mount(fsm, p):
    b = fsm.body
    ch = SimpleNamespace(cooldown=0, check=0, still=0, arrived=-1, timer=0)

    def enter():
        ch.timer = 0
        ch.arrived = -1
        fsm.gfx.hand_aim["l"] = None
        fsm.gfx.hand_aim["r"] = None

    def finish():
        brk()
        fsm.settle()

    def tick(cursor, disturbed):
        if cursor is None:
            finish()
            return
        ch.timer += 1
        if fsm._cursor_speed > p.still_speed * GIVEUP_SPEED_MULT:
            finish()  # 光标被甩开就不追了
            return
        fsm.gfx.look_at = cursor
        if ch.arrived >= 0:
            b.stop_walk()
            ch.arrived += 1
            if ch.arrived >= p.linger:
                finish()
            return
        if abs(cursor[0] - b.chunk0.x) <= p.arrive_pad:
            b.stop_walk()
            ch.arrived = 0
            return
        b.walk_to(cursor[0])
        if ch.timer >= p.timeout:
            finish()

    def brk():
        b.stop_walk()
        k = _temper(b.temper, p.cooldown_temper_lo, p.cooldown_temper_hi)
        lo = max(0, int(p.cooldown_lo * k))
        hi = max(lo, int(p.cooldown_hi * k))
        ch.cooldown = fsm.rng.randint(lo, hi)

    fsm.register_state(
        "CursorChase",
        enter=enter,
        tick=tick,
        brk=brk,
        kill_break=brk,
        stun_break=b.stop_walk,
        tier=T_ACTIVITY,
        energy=LIGHT,
    )
    fsm.on_stun(b.stop_walk)

    def free(cursor):
        return (
            cursor is not None
            and fsm.state == "IdleStand"
            and not fsm.grab.active
            and not fsm.ask("exhausted")
            and not fsm._zerog()
            and not b.swimming
            and ch.still >= p.still_ticks
            and p.near_frac * fsm.WL <= abs(b.chunk0.x - cursor[0]) <= p.far_frac * fsm.WL
        )

    def chance():
        c = p.chance * _temper(b.temper, p.temper_lo, p.temper_hi)
        return max(0.0, c * (1.0 - p.sleepy_damp * b.sleepiness))

    def rule(cursor):
        if ch.cooldown > 0:
            ch.cooldown -= 1
        if cursor is not None and fsm._cursor_speed <= p.still_speed:
            ch.still += 1
        else:
            ch.still = 0
        if ch.check > 0:
            ch.check -= 1
            return
        ch.check = int(p.check_every)
        if free(cursor) and fsm.rng.random() < chance():
            fsm._transition("CursorChase")

    fsm.register_rule(rule)
