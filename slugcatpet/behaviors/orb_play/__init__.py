"""玩光萤：闲着的时候凑过去拍一爪、或者叼起来颠两下扔出去；光萤跟着光标跑时猫会在后面追它。

三种玩法按光萤当下的形态和当时的情况选：
- 光萤是跟随型（跟着光标）→ 追过去扑一下
- 光萤是玩具型、猫有空手 → 走过去叼起来，玩一会儿再抛出去
- 光萤是玩具型、手上没空 → 走过去一巴掌拍飞
拍飞 / 扔出去之后会看一会儿，兴致还在就再玩一轮，最多三轮。
"""

from __future__ import annotations

import math

from ...brain.hands import TOY
from ...brain.skills.throw import GRAB_REACH
from ...brain.state import LIGHT, T_ACTIVITY, State
from ...items.base import THROWABLE
from ...items.orb.model import FOLLOW
from ...items.state import ItemState
from ..base import Behavior, mood_candidate, mood_params

BAT_REACH = 30.0  # 走到这么近就能拍到
BAT_VX = 6.5  # 拍出去的横向速度
BAT_VY = -5.0  # 顺手往上一挑
CHASE_NEAR = 46.0  # 追到这么近就扑
CHASE_P = 0.06  # 追上后每 tick 扑一下的概率
HOP_DX = 70.0  # 横向离这么近就原地蹦一下够它（光萤常飘在高处，够不着就跳着玩）
HOP_P = 0.03  # 每 tick 起跳的概率
MAX_HOPS = 3  # 蹦够这么多下就玩够了
HOLD_LO, HOLD_HI = 40, 110  # 叼着玩多久才扔
TOSS_SPEED = 5.0  # 抛出去的横向速度（光萤很轻，别扔太猛）
TOSS_UP = 4.5  # 抛出去的上挑
PICK_CARRY = 0.45  # 有空手时选择「叼起来扔」而不是「拍飞」的概率
WATCH_TICKS = 34  # 出手后看一会儿
MAX_ROUNDS = 3  # 最多玩几轮
APPROACH_TIMEOUT = 260  # 一直走不到就收工
CHASE_TIMEOUT = 320  # 追太久也收工
SETUP_TIMEOUT = 1100  # 整个行为的看门狗


def _playable(fsm, o) -> bool:
    """这颗光萤眼下能不能去玩。"""
    return (
        getattr(o, "playful", False)
        and o.state == ItemState.FREE
        and o.held_by_hand is None
        and fsm.social.free_for(fsm.win, o)
        and not fsm.hands.forbidden(o)
    )


def _any_playable(fsm) -> bool:
    return any(_playable(fsm, o) for o in fsm.items(THROWABLE))


class OrbPlayer:
    """一轮玩光萤的控制器；update() 返回 running / done / giveup。"""

    def __init__(self, fsm):
        self.fsm = fsm
        self.win = fsm.win
        self.body = fsm.body
        self.gfx = fsm.gfx
        self.rng = fsm.rng
        self.phase = "select"
        self.t = 0
        self.timer = 0
        self.rounds = 0
        self.hops = 0
        self.orb = None
        self.hold_at = 0

    # 推进

    def update(self):
        self.timer += 1
        if self.timer > SETUP_TIMEOUT:
            return "giveup"
        return getattr(self, "_phase_" + self.phase)()

    def _ok(self, o):
        return o is not None and o.state == ItemState.FREE and o.held_by_hand is None

    def _grab_dist(self, o, side):
        """上身或拿东西的手到光萤边缘的距离（光萤在地上，光看头到它的距离是够不着的）。"""
        c0 = self.body.chunk0
        d = math.hypot(c0.x - o.x, c0.y - o.y)
        hx, hy = self.body._carry_pos(side)
        return max(0.0, min(d, math.hypot(hx - o.x, hy - o.y)) - o.rad)

    def _phase_select(self):
        o = self._choose()
        if o is None:
            return "giveup"
        self.orb = o
        self.fsm.social.claim(self.win, "orb", o, "OrbPlay")
        if o.mode == FOLLOW:
            self.phase = "chase"
        elif self.body.free_hand() is not None and self.rng.random() < PICK_CARRY:
            self.phase = "fetch"
        else:
            self.phase = "approach"
        self.t = 0
        return "running"

    def _choose(self):
        """挑一颗来玩：跟随型优先（用户切成跟随型多半就是想看猫追它），其次就近。"""
        c0 = self.body.chunk0
        best, bkey = None, None
        for o in self.fsm.items(THROWABLE):
            if not _playable(self.fsm, o):
                continue
            key = (0 if o.mode == FOLLOW else 1, math.hypot(o.x - c0.x, o.y - c0.y))
            if bkey is None or key < bkey:
                best, bkey = o, key
        return best

    # 走过去拍一爪

    def _phase_approach(self):
        o, b = self.orb, self.body
        if not self._ok(o):
            return "giveup"
        self.gfx.look_at = (o.x, o.y)
        dx = o.x - b.chunk0.x
        if math.hypot(dx, o.y - b.chunk0.y) <= BAT_REACH:
            b.stop_walk()
            b.facing = 1 if dx >= 0 else -1
            b.reach_for(o, "r" if b.facing > 0 else "l")
            self._bat(o, b.facing)
            self.phase = "watch"
            self.t = 0
            return "running"
        b.walk_to(o.x - math.copysign(BAT_REACH * 0.6, dx if dx else 1.0))
        self.t += 1
        return "giveup" if self.t > APPROACH_TIMEOUT else "running"

    def _bat(self, o, facing):
        """一爪把它拍出去：偶尔往回勾一下，看着更顽皮。"""
        push = BAT_VX if self.rng.random() < 0.75 else -BAT_VX * 0.4
        o.vx = facing * push + self.rng.uniform(-1.5, 1.5)
        o.vy = BAT_VY + self.rng.uniform(-1.0, 1.0)
        o.vibrate = 12

    # 叼起来扔

    def _phase_fetch(self):
        o, b = self.orb, self.body
        if not self._ok(o):
            return "giveup"
        self.gfx.look_at = (o.x, o.y)
        side = b.free_hand()
        if side is None or not b.can_hold(o):
            self.phase = "approach"
            return "running"
        d = self._grab_dist(o, side)
        if d <= GRAB_REACH:
            b.stop_walk()
            b.facing = 1 if o.x >= b.chunk0.x else -1
            b.grab(o, b.free_hand("r" if b.facing > 0 else "l") or side)
            self.fsm.hands.adopt(o, TOY)
            self.hold_at = self.rng.randint(HOLD_LO, HOLD_HI)
            self.phase = "hold"
            self.t = 0
            return "running"
        b.walk_to(o.x)
        self.t += 1
        return "giveup" if self.t > APPROACH_TIMEOUT else "running"

    def _phase_hold(self):
        o, b = self.orb, self.body
        if b.hand_of(o) is None:
            return "giveup"
        b.stop_walk()
        self.gfx.look_at = (o.x, o.y)
        self.t += 1
        if self.t >= self.hold_at:
            side = b.hand_of(o)
            b.facing = 1 if self.rng.random() < 0.5 else -1
            b.throw(o, b.facing, TOSS_SPEED, up=TOSS_UP, spare_cursor=True)
            self.gfx.throw_object(side, o)
            self.phase = "watch"
            self.t = 0
        return "running"

    # 追着跟随型跑

    def _phase_chase(self):
        o, b = self.orb, self.body
        if not self._ok(o):
            return "giveup"
        self.gfx.look_at = (o.x, o.y)
        if o.mode != FOLLOW:
            self.phase = "approach"  # 追着追着变回玩具了，接着当玩具玩
            self.t = 0
            return "running"
        dx = o.x - b.chunk0.x
        d = math.hypot(dx, o.y - b.chunk0.y)
        if d <= CHASE_NEAR and b.on_floor() and self.rng.random() < CHASE_P:
            b.stop_walk()
            b.facing = 1 if dx >= 0 else -1
            b.reach_for(o, "r" if b.facing > 0 else "l")
            self._bat(o, b.facing)
            self.rounds += 1
            if self.rounds >= MAX_ROUNDS:
                return "done"
            self.t = 0
            return "running"
        # 光萤多半飘在够不着的高度：跑到它下面蹦一下够它
        if b.on_floor() and abs(dx) <= HOP_DX and self.rng.random() < HOP_P:
            b.facing = 1 if dx >= 0 else -1
            b.request_jump("stand")
            self.hops += 1
            if self.hops >= MAX_HOPS:
                return "done"
        b.walk_to(o.x)
        self.t += 1
        return "giveup" if self.t > CHASE_TIMEOUT else "running"

    # 看一会儿

    def _phase_watch(self):
        self.t += 1
        o = self.orb
        if o is not None:
            self.gfx.look_at = (o.x, o.y)
        if self.t < WATCH_TICKS:
            return "running"
        self.rounds += 1
        if self.rounds >= MAX_ROUNDS or not self._ok(o):
            return "done"
        self.phase = "select"
        self.t = 0
        return "running"

    def release(self):
        """收尾：还攥在手里就原地放下，手放下来。"""
        b, g = self.body, self.gfx
        b.stop_walk()
        b.arm_aim["l"] = b.arm_aim["r"] = None
        g.hand_aim["l"] = g.hand_aim["r"] = None
        o = self.orb
        if o is not None and b.hand_of(o) is not None:
            b.release(o)
        self.fsm.social.release(self.win, "orb")
        self.orb = None


class OrbPlay(State):
    name = "OrbPlay"
    mood = "orb_play"
    tier = T_ACTIVITY
    energy = LIGHT
    player = None

    def hands_needed(self):
        return "any"

    def enter(self):
        self.player = OrbPlayer(self.fsm)

    def tick(self, cursor, disturbed):
        fsm = self.fsm
        if self.player is None:
            fsm.settle()
            return
        r = self.player.update()
        if r == "running":
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
        if self.player is not None:
            self.player.release()
            self.player = None


class OrbPlayBehavior(Behavior):
    key = "orb_play"
    mood = "orb_play"
    title = {"zh": "玩光萤", "en": "Play with glow orbs"}
    doc = (
        "闲着的时候去玩光萤：凑过去一爪拍飞，或者叼起来颠两下再抛出去；"
        "光萤切成跟随型跟着光标跑时，猫会在后面追它扑它。玩两三轮就走开。"
    )
    requires = (THROWABLE,)
    # 新鲜度回升得快些（0.0009）：光萤是摆在那儿的玩具，闲着的时候该常去玩玩
    params = mood_params(1.00, 0.70, 0.28, 0.35, 0.0040, 0.00090)

    def mount(self, fsm):
        p = self.p
        b = fsm.body
        st = fsm.add_state(OrbPlay)
        fsm.register_mood_entry("orb_play", "OrbPlay")
        gate = fsm.traits.play_gate

        def can(ctx):
            if ctx.energy < gate or ctx.submerged or b.swimming or b.on_pole:
                return False
            if fsm.grab.active or fsm.ask("exhausted"):
                return False
            return _any_playable(fsm)

        mood_candidate(fsm, "orb_play", p, gate=can, before="idle")

        def on_stun():
            if st.player is not None:
                st.player.release()
                st.player = None

        fsm.on_stun(on_stun)
