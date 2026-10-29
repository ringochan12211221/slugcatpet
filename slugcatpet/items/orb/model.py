"""珍珠的物理：和石头同构（单个质点 + 墙地碰撞），不参与物体间碰撞。

尺寸照原作：原作珍珠本体是 11 格直径的小球，桌宠同样 20px 一格，所以 rad = 5.5 就是原尺寸。
手感比原来的光萤沉：落得干脆、落地几乎不弹；水里会慢慢沉下去。
但还是留了一点悬浮（原作里珍珠也有浮着的时候），只是幅度小得多。
"""

from __future__ import annotations

import math
import random

from ...core.chunkphys import aabb_wall_collide, apply_water
from ...core.units import clampf
from ..state import ItemState

RAD = 5.5  # 直径 11 = 原作珍珠的大小
MASS = 0.12
GRAVITY = 0.50  # y↓，比石头轻一点，但落得干脆
AIR_FRICTION = 0.990
BOUNCE = 0.30  # 珍珠不怎么弹
SURFACE_FRICTION = 0.50
BUOYANCY = 0.95  # 比水重，会慢慢沉
WATER_FRICTION = 0.94

REST_VEL_EPS = 0.35
# 注意：phase 每 tick +1.0，下面几个角速度都要乘上去才对；
# 直接 sin(phase) 会是 6~10Hz 的抽搐。0.05 左右 ≈ 2~3 秒一个来回。
BOB_SPEED = 0.055  # 悬浮摆动的角速度（rad/tick），约 2.9 秒一个来回
BOB_AMP = 0.9  # 上下浮动幅度（px）——珍珠比原来的光萤沉，浮得很轻
DRIFT_SPEED = 0.012  # 静止时的横向漂移角速度（乘 6 后约 2.2 秒一个来回）
DRIFT_AMP = 4.0  # 横向漂移幅度（px）
GLOW_SPEED = 0.05  # 呼吸明暗的角速度，约 3.1 秒一个来回

# 偶尔闪一下的光：这才是原作"闪闪发光的球体"里那个闪，贴图本身没有高光
SPARK_TICKS = 7
SPARK_WAIT_LO = 320  # 8 秒
SPARK_WAIT_HI = 1600  # 40 秒

EXIT_FLING_SPEED = 8.0

# 两种形态：玩具型（默认，就是个会飘的小东西）/ 跟随型（绕着光标转）
TOY, FOLLOW = "toy", "follow"

ORBIT_R = 30.0  # 跟随型绕光标转的半径
ORBIT_SPEED = 0.018  # 绕行角速度（rad/tick）；切向速度约 0.5px/tick，不算"有动静"
FOLLOW_PULL = 0.055  # 追向光标的加速度系数
FOLLOW_DAMP = 0.80  # 阻尼：越大越飘
FOLLOW_MAX_V = 26.0


class Orb:
    """一颗光萤。"""

    collision_layer = 2
    creature = False
    dead = False
    edible = False
    throwable = True
    playful = True  # 猫会去玩它（见 behaviors/orb_play）
    pierces = False
    stops_weapons = False
    carcass = False
    needle_quarters = 0
    food_points = 0

    __slots__ = (
        "x",
        "y",
        "vx",
        "vy",
        "last_x",
        "last_y",
        "rad",
        "mass",
        "gravity",
        "air_friction",
        "bounce",
        "surface_friction",
        "buoyancy",
        "water_friction",
        "water_y",
        "room_gravity",
        "state",
        "rotation_deg",
        "last_rotation",
        "spin",
        "vibrate",
        "pal_i",
        "spark",
        "spark_wait",
        "_rng",
        "fling",
        "thrown_by_cat",
        "spare_cursor",
        "dissolve",
        "seed",
        "phase",
        "glow",
        "rest_x",
        "mode",
        "goal",
        "collide_with_objects",
        "_id",
        "_contact_floor",
        "_contact_ceil",
        "_contact_x",
        "_impact_cb",
        "unfetchable",
        "fetch_fails",
        "held_by_hand",
        "behind",
    )

    def __init__(self, x: float, y: float, seed: int = 0, pal_i: int = 0):
        self.x = self.last_x = float(x)
        self.y = self.last_y = float(y)
        self.rest_x = float(x)
        self.vx = 0.0
        self.vy = 0.0
        self.rad = RAD
        self.mass = MASS
        self.gravity = GRAVITY
        self.air_friction = AIR_FRICTION
        self.bounce = BOUNCE
        self.surface_friction = SURFACE_FRICTION
        self.buoyancy = BUOYANCY
        self.water_friction = WATER_FRICTION
        self.water_y = None
        self.room_gravity = 1.0
        self.state = ItemState.FREE
        self.rotation_deg = 0.0
        self.last_rotation = 0.0
        self.spin = 0.0
        self.vibrate = 0
        self.pal_i = int(pal_i)  # 配色索引，见 palette.py
        self._rng = random.Random(0x9E37 ^ (int(seed) * 2654435761 & 0xFFFFFFFF))
        self.spark = 0  # >0 表示正在闪，倒数
        self.spark_wait = self._rng.randint(SPARK_WAIT_LO, SPARK_WAIT_HI)
        self.fling = False
        self.thrown_by_cat = False
        self.spare_cursor = False
        self.dissolve = -1
        self.seed = int(seed)
        self._id = int(seed)
        # 每颗错开相位，一群光萤不会同步呼吸
        self.phase = (int(seed) % 1000) * 0.618 * math.tau
        self.glow = 1.0
        self.mode = TOY  # 默认玩具型
        self.goal = None  # 跟随型要追的光标位置，由 OrbKind.tick 每 tick 写入
        self.collide_with_objects = False
        self._contact_floor = False
        self._contact_ceil = False
        self._contact_x = 0
        self._impact_cb = None
        self.unfetchable = True  # 不吃它，取果行为不会来叼
        self.fetch_fails = 0
        self.held_by_hand = None
        self.behind = False

    @property
    def pos(self):
        return (self.x, self.y)

    # ---- 视觉用的浮动量（不进物理，只让画出来在飘）----
    def bob_offset(self) -> tuple[float, float]:
        moving = math.hypot(self.vx, self.vy) > REST_VEL_EPS
        if moving or self.state != ItemState.FREE:
            return (0.0, 0.0)
        t = self.phase * 1.0 + self.seed * 0.37  # 每颗错开，一群光萤不同步
        return (
            math.sin(t * DRIFT_SPEED * 6.0) * DRIFT_AMP * 0.25,
            math.sin(t * BOB_SPEED) * BOB_AMP,
        )

    def glow_at(self) -> float:
        """0.75–1.0 的呼吸亮度。"""
        return 0.875 + 0.125 * math.sin(self.phase * GLOW_SPEED + self.seed * 0.11)

    def collision_chunks(self):
        self.collide_with_objects = False
        return ()

    def set_rotation_to_grabber(self, gx: float, gy: float) -> None:
        self.last_rotation = self.rotation_deg

    def set_held_direction(self, dx: float, dy: float) -> None:
        self.last_rotation = self.rotation_deg

    def on_thrown(self, throw) -> None:
        self.spin = 0.0
        self.fling = False
        self.thrown_by_cat = True
        self.spare_cursor = getattr(throw, "spare_cursor", True)  # 不砸光标

    def in_flight(self) -> bool:
        return self.fling or self.thrown_by_cat

    def parried(self, dx, dy) -> None:
        self.fling = False
        self.thrown_by_cat = False
        self.vx, self.vy = dx * 18.0, dy * 18.0

    def clash(self, mx, my, dx, dy, speed, rng) -> None:
        self.x += (mx - self.x) * 0.5
        self.y += (my - self.y) * 0.5
        self.vx, self.vy = dx * speed * 0.5, dy * speed * 0.5
        self.vibrate = 20
        self.fling = False
        self.thrown_by_cat = False

    def at_rest_on_ground(self, HL: float) -> bool:
        return self.y + self.rad >= HL - 0.5 and abs(self.vx) < REST_VEL_EPS and abs(self.vy) < REST_VEL_EPS

    def step(self, WL: float, HL: float) -> None:
        self.phase += 1.0
        self._tick_spark()
        if self.state in (ItemState.MOUSE, ItemState.CARRIED):
            self._contact_floor = False
            return
        self.last_x, self.last_y = self.x, self.y
        self.last_rotation = self.rotation_deg
        if self.state == ItemState.GONE:
            return

        if self.mode == FOLLOW and self.goal is not None:
            self._follow(WL, HL)
            return

        self.vy += self.gravity * self.room_gravity
        apply_water(
            self, self.water_y, self.buoyancy, self.water_friction, self.room_gravity, self.air_friction
        )
        self.x += self.vx
        self.y += self.vy
        self._collide(WL, HL)

        if self._contact_floor:
            # 落地后横向速度衰减得快些，很快就停住开始浮
            self.vx *= 0.92

        if self.vibrate > 0:
            self.vibrate -= 1

        if (self.fling or self.thrown_by_cat) and (
            self.at_rest_on_ground(HL) or math.hypot(self.vx, self.vy) < EXIT_FLING_SPEED
        ):
            self.fling = False
            self.thrown_by_cat = False

        # 别飘出屏幕：出界夹回由窗口统一处理，这里只夹住速度别越积越大
        self.vx = clampf(self.vx, -40.0, 40.0)
        self.vy = clampf(self.vy, -40.0, 40.0)

    def _collide(self, WL: float, HL: float) -> None:
        aabb_wall_collide(self, WL, HL, impact=self._impact_cb)

    def _tick_spark(self) -> None:
        """偶尔闪一下：原作珍珠的"闪闪发光"就是这个，不是贴图上的高光。"""
        if self.spark > 0:
            self.spark -= 1
            return
        if self.state != ItemState.FREE:
            return
        self.spark_wait -= 1
        if self.spark_wait <= 0:
            self.spark = SPARK_TICKS
            self.spark_wait = self._rng.randint(SPARK_WAIT_LO, SPARK_WAIT_HI)

    def spark_progress(self) -> float:
        """正在闪的话返回 0（刚亮起）→ 1（已消失）；没在闪返回 -1。"""
        if self.spark <= 0:
            return -1.0
        return 1.0 - self.spark / SPARK_TICKS

    def _follow(self, WL: float, HL: float) -> None:
        """跟随型：绕着光标慢慢转，不落地也不受重力。"""
        tx, ty = self.goal
        ang = self.phase * ORBIT_SPEED + self.seed * 0.7
        tx += math.cos(ang) * ORBIT_R
        ty += math.sin(ang) * ORBIT_R
        self.vx = (self.vx + (tx - self.x) * FOLLOW_PULL) * FOLLOW_DAMP
        self.vy = (self.vy + (ty - self.y) * FOLLOW_PULL) * FOLLOW_DAMP
        self.vx = clampf(self.vx, -FOLLOW_MAX_V, FOLLOW_MAX_V)
        self.vy = clampf(self.vy, -FOLLOW_MAX_V, FOLLOW_MAX_V)
        self.x = clampf(self.x + self.vx, self.rad, WL - self.rad)
        self.y = clampf(self.y + self.vy, self.rad, HL - self.rad)
        self._contact_floor = self._contact_ceil = False
        self._contact_x = 0
        self.fling = False
        self.thrown_by_cat = False
        if self.vibrate > 0:
            self.vibrate -= 1

    def deflect(self, rng) -> None:
        v = math.hypot(self.vx, self.vy)
        a = rng.uniform(0.0, math.tau)
        mag = rng.uniform(0.2, 0.5) * v
        self.vx = -0.4 * self.vx + math.cos(a) * mag
        self.vy = -0.5 * self.vy + math.sin(a) * mag
        self.vibrate = 20
