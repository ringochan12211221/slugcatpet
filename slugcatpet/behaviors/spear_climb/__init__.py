"""插矛搭脚点：想登高但近处没有落脚点时，朝侧墙插一根矛，再沿着它爬上去。

矛（含身上长出的骨针）扎进墙后自带杆接口，会自动成为杆网里的一根横杆，
所以这里只负责「弄到矛 → 走到能出手的位置 → 朝墙上方扔 → 等它扎住」，
扎住之后交给现有的上横杆行为爬上去。
"""

from __future__ import annotations

import math

from ...brain.hands import WEAPON, can_wield
from ...brain.skills.hpole import GRIP_DIST
from ...brain.skills.throw import Pitch, WeaponPickup, wieldable_items
from ...brain.state import LIGHT, T_ACTIVITY, State
from ...items.base import CLIMBABLE, THROWABLE
from ...items.spear.model import WALL
from ...items.state import ItemState
from ...planning.jump_reach import JumpReach
from ...planning.reach import DONE, GIVEUP
from ..base import Behavior, mood_candidate, mood_params

AIM_MIN_TICKS = 10  # 瞄准至少这么久才扔
AIM_TIMEOUT = 200  # 一直够不着就换一侧墙
SETUP_TIMEOUT = 1200  # 整个行为的看门狗
WATCH_TIMEOUT = 90  # 扔出去后等它扎住的帧数
MAX_TRIES = 2  # 换侧墙 / 重跳的次数
NEAR = 12.0  # 离走位目标这么近算站好了
UP_JUMP = 30.0  # 没舌头的猫：扎在头顶这么高，原地起跳刚好够得着
UP_TONGUE = 60.0  # 有舌头的猫：扎高点，甩舌头把自己收上去
BEAM_PAD = 4.0  # 起跳目标别贴着横杆两端
SLOPE = 1.15  # 横扔仰角上限（约 41°）对应的 水平距离 / 高度
DIST_MIN = 60.0  # 站得离墙至少这么远，才扔得出仰角
LEDGE_LO, LEDGE_HI = 25.0, 150.0  # 头顶这个高度区间里有横杆就不必插
LEDGE_DX = 200.0  # 且水平离得这么近


class _BeamGoal:
    """矛扎墙后露出的那一截：给跳跃控制器当够取目标。"""

    __slots__ = ("obj", "x", "y")

    def __init__(self, obj, x, y):
        self.obj = obj
        self.x = x
        self.y = y

    def pos(self):
        return (self.x, self.y)


def _sticks(o):
    """能扎进墙的武器（矛、骨针；石头只能砸晕，扎不住）。"""
    return getattr(o, "pierces", False)


def _has_ledge(fsm):
    """头顶上方够得着的高度里已经有横杆了，就不用自己插一根。"""
    c0 = fsm.body.chunk0
    for p in fsm.items(CLIMBABLE):
        if p.kind != "horizontal":
            continue
        above = c0.y - p.ay
        if not (LEDGE_LO <= above <= LEDGE_HI):
            continue
        if abs((min(p.ax, p.bx) + max(p.ax, p.bx)) * 0.5 - c0.x) <= LEDGE_DX:
            return True
    return False


class SpearPlanter:
    """弄到矛 → 站位 → 朝墙插 → 等它扎住；update() 返回 running / done / giveup。"""

    def __init__(self, fsm):
        self.fsm = fsm
        self.win = fsm.win
        self.body = fsm.body
        self.gfx = fsm.gfx
        self.grow = fsm.win.skill("grow_weapon")
        self.mount = fsm.win.skill("hpole_mount")
        # 有舌头甩得远就扎高些；没舌头的只能靠跳，扎在起跳够得着的高度
        self.up = UP_TONGUE if self.mount is not None else UP_JUMP
        self.phase = "arm"
        self.t = 0
        self.timer = 0
        self.tries = 0
        self.side = 1  # +1 右墙，-1 左墙
        self.weapon = None
        self.pickup = None
        self.pitch = None
        self.target = None
        self.thrown = None
        self.hop = None

    # 武器

    def _usable(self, o):
        # hunting=True 只为绕开「好感够低才肯拿扎人的东西」这条：插矛是当工具用，不是动粗。
        # 但「没力气的猫（圣徒 spear_toss）扎不进墙」这条照旧 —— 原作里圣徒就是没这个力气。
        return _sticks(o) and can_wield(self.body, o, hunting=True)

    def _held(self):
        return next((o for o in self.body.held_items() if self._usable(o)), None)

    def _arm(self, w):
        self.weapon = w
        self.pitch = Pitch(self.fsm, w, spare_cursor=True)
        self.phase = "aim"
        self.t = 0

    # 推进

    def update(self):
        self.timer += 1
        if self.timer > SETUP_TIMEOUT:
            return "giveup"
        return getattr(self, "_phase_" + self.phase)()

    def _phase_arm(self):
        w = self._held()
        if w is not None:
            self._arm(w)
            return "running"
        if self.grow is not None and not self.body.swimming:
            self.phase = "grow"
            self.t = 0
            return "running"
        self.pickup = WeaponPickup(
            self.fsm, lambda s, d: d, "SpearClimb", hunting=True, accept=self._usable
        )
        if not self.pickup.select():
            return "giveup"
        self.phase = "fetch"
        return "running"

    def _phase_grow(self):
        r = self.grow.update()
        if r == "got":
            self._arm(self.grow.weapon)
        elif r == "fail":
            return "giveup"
        return "running"

    def _phase_fetch(self):
        pk = self.pickup
        if not pk.available():
            return "giveup"
        r = pk.update()
        if r == "got":
            self._arm(pk.target)
        elif r == "failed":
            return "giveup"
        return "running"

    # 站位与瞄准

    def _wall_x(self):
        return self.fsm.WL if self.side > 0 else 0.0

    def _stand_x(self):
        """站到离墙这么远：仰角才够把矛送到头顶上方。"""
        b = self.body
        x = self._wall_x() - self.side * max(DIST_MIN, self.up * SLOPE)
        lo = b.walk_min if b.walk_min is not None else 0.0
        hi = b.walk_max if b.walk_max is not None else self.fsm.WL
        return min(hi, max(lo, x))

    def _phase_aim(self):
        b, pitch = self.body, self.pitch
        if pitch.side() is None:
            self.phase = "arm"
            return "running"
        pt = (self._wall_x(), b.chunk0.y - self.up)
        self.target = pt
        self.gfx.look_at = pt
        self.t += 1
        pitch.face(pt)
        if self.t > AIM_TIMEOUT:
            return self._aim_stuck()
        # 先走到离墙够近的地方再出手：远了只是 33% 概率扎住，近了是必扎
        want = self._stand_x()
        if abs(b.chunk0.x - want) > NEAR:
            b.walk_to(want)
            return "running"
        b.stop_walk()
        if not pitch.can_hit(pt):
            return self._aim_stuck()
        b.facing = pitch.throw_dir
        if pitch.aim(pt) and self.t >= AIM_MIN_TICKS:
            pitch.release()
            self.phase = "throw"
        return "running"

    def _aim_stuck(self):
        """站在出手位上还是够不着（或走不过去）：换一侧墙再试。"""
        self.tries += 1
        if self.tries >= MAX_TRIES:
            return "giveup"
        self.side = -self.side
        self.t = 0
        return "running"

    def _phase_throw(self):
        if self.pitch.update(self.target) == "thrown":
            self.thrown = self.pitch.thrown
            self.phase = "watch"
            self.t = 0
        return "running"

    def _phase_watch(self):
        self.t += 1
        w = self.thrown
        if w is not None:
            self.gfx.look_at = (w.x, w.y)
            if w.mode == WALL:
                if self.mount is not None:
                    self._mount(w)  # 有舌头：甩上去，不用跳
                    return "done"
                self.phase = "hop"
                self.t = 0
                return "running"
            if w.state == ItemState.GONE:
                w = self.thrown = None
        if self.t > WATCH_TIMEOUT or w is None:
            self.tries += 1
            if self.tries >= MAX_TRIES:
                return "giveup"
            self.phase = "arm"  # 掉地上了，捡起来再扔
            self.t = 0
            self.thrown = None
        return "running"

    # 爬上去

    def _beam_goal(self, w):
        """矛那一截横杆上、离猫最近的够取点。"""
        b = self.body
        lo, hi = min(w.ax, w.bx) + BEAM_PAD, max(w.ax, w.bx) - BEAM_PAD
        return _BeamGoal(w, min(max(b.chunk0.x, lo), hi), w.ay)

    def _at_beam(self, w):
        """身体（头）离那一截横杆够近，可以直接抓住。"""
        b = self.body
        lo, hi = min(w.ax, w.bx), max(w.ax, w.bx)
        ax = min(max(b.chunk0.x, lo + 2.0), hi - 2.0)
        return math.hypot(b.chunk0.x - ax, b.chunk0.y - w.ay) <= GRIP_DIST

    def _phase_hop(self):
        """没舌头的猫：走到矛下面起跳，够到了就抓住交给上横杆。"""
        w = self.thrown
        if w is None or w.mode != WALL or w not in self.fsm.items(CLIMBABLE):
            return self._retry()
        if self._at_beam(w):
            self._mount(w)
            return "done"
        if self.hop is None:
            goal = self._beam_goal(w)
            if JumpReach(self.win).can_touch(goal) is None:
                return self._retry()  # 扎太高了，跳不上去
            self.hop = JumpReach(self.win).make_controller(goal)
        r = self.hop.update()
        if r in (DONE, GIVEUP):
            self.hop = None
            return self._retry()
        return "running"

    def _retry(self):
        """这一下没成：换一侧墙 / 换个高度再来，次数用完就收工。"""
        self.hop = None
        self.tries += 1
        if self.tries >= MAX_TRIES:
            return "giveup"
        self.phase = "arm"
        self.t = 0
        self.thrown = None
        return "running"

    def _mount(self, w):
        """抓住这根矛：占住它，交给上横杆行为爬上去。"""
        fsm = self.fsm
        if "HPole" not in fsm._states:
            return
        fsm.social.claim(fsm.win, "hpole", w)
        fsm._transition("HPole")

    def release(self):
        """收尾：没扔出去的武器留着，抬着的手放下。"""
        b, g = self.body, self.gfx
        if self.hop is not None:
            self.hop.cancel()
            self.hop = None
        b.stop_walk()
        b.arm_aim["l"] = b.arm_aim["r"] = None
        g.hand_aim["l"] = g.hand_aim["r"] = None
        if self.pickup is not None and self.pickup.target is not None:
            self.fsm.social.release(self.win, "stone")
        self.pickup = None
        self.pitch = None


class SpearClimb(State):
    name = "SpearClimb"
    mood = "spear_climb"
    tier = T_ACTIVITY
    energy = LIGHT
    planter = None

    def hands_needed(self):
        return "one" if self.planter is None or self.planter.weapon is None else "any"

    def enter(self):
        fsm = self.fsm
        fsm.gfx.hand_aim["l"] = fsm.gfx.hand_aim["r"] = None
        self.planter = SpearPlanter(fsm)

    def tick(self, cursor, disturbed):
        fsm = self.fsm
        if self.planter is None:
            fsm.settle()
            return
        r = self.planter.update()
        if r == "running":
            return
        if r == "done":
            self.planter = None  # 已经交棒给上横杆了，别再收尾
            return
        self._release()
        fsm.settle()

    def brk(self):
        self._release()

    def kill_break(self):
        self._release()

    def stun_break(self):
        self._release()

    def _release(self):
        p = self.planter
        if p is not None:
            p.release()
            if p.weapon is not None:
                self.fsm.hands.adopt(p.weapon, WEAPON)
        self.planter = None


class SpearClimbBehavior(Behavior):
    key = "spear_climb"
    mood = "spear_climb"
    title = {"zh": "插矛搭脚点", "en": "Plant a spear"}
    doc = (
        "想登高可近处又没有落脚点时，捡起矛（或从身上拔一根骨针）朝侧墙扔过去，"
        "矛扎进墙露出一截就成了根横杆，再顺着它爬上去。插之前会先看头顶够得着的高度里"
        "有没有现成的横杆，有就不费这个事。"
    )
    requires = (THROWABLE, CLIMBABLE)
    params = mood_params(0.85, 0.72, 0.30, 0.30, 0.0035, 0.00045)

    def mount(self, fsm):
        # 没舌头的猫上不去横杆 —— 插矛就是把这件事补上的手段，所以不按舌头来挡。
        # 有没有力气扎进墙（圣徒 spear_toss）由 can() 里的 can_wield 判断。
        p = self.p
        b = fsm.body
        st = fsm.add_state(SpearClimb)
        fsm.register_mood_entry("spear_climb", "SpearClimb")
        gate = fsm.traits.play_gate

        def can(ctx):
            if ctx.energy < gate or ctx.submerged or b.swimming or b.on_pole:
                return False
            if fsm.grab.active or fsm.ask("exhausted"):
                return False
            if fsm.win.skill("grow_weapon") is None and not any(
                _sticks(o) for o in wieldable_items(fsm, hunting=True)
            ):
                return False
            return not _has_ledge(fsm)

        mood_candidate(fsm, "spear_climb", p, gate=can, before="idle")

        def on_stun():
            if st.planter is not None:
                st.planter.release()
                st.planter = None

        fsm.on_stun(on_stun)
