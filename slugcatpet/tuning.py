"""物理、环境、核心行为、规划共用的常量，tick=1/40s。"""

from __future__ import annotations

# 心情仲裁打分噪声
MOOD_NOISE_AMP = 0.20

# 趴下休息：体力驱动的强制疲劳
EXHAUST_ENTER_ENERGY = 0.1
EXHAUST_EXIT_ENERGY = 0.50
LIE_SETTLE_TICKS = 40
SLEEP_ANCHOR_EASE = 0.45  # 睡着时身体贴向睡姿锚点的速度

# 玩耗体力的游戏所需的最低体力
PLAY_ENERGY_GATE = 0.40

# 性格换算的全局系数
PERS_ACT_SPREAD = 1.0
PERS_GATE_SPREAD = 0.20
PERS_GATE_FLOOR = 0.20

# 做完一件事后先站一会再挑下一件
IDLE_BREATHER = 50

# 饱食度
FOOD_INIT = 2
FOOD_KILL_PENALTY = 4
EN_EAT_RESTORE = 0.10

# 业力与冬眠
KARMA_INIT = 8
KARMA_MAX = 9
HIBERNATE_TICKS = 6000  # 冬眠睡这么久（150 s）
REVIVE_TICKS = 400

# 困意：醒着慢慢涨，睡着慢慢降；冬眠睡满清零，打盹只降一截
SLEEPY_INIT = 0.3
SLEEPY_RATE = 1.0 / 60000.0  # 醒着每 tick 涨这么多
SLEEPY_VIG_MULT = 1.5  # 剧烈活动时涨得快
SLEEP_RELIEF_RATE = 1.0 / 8000.0  # 睡着每 tick 降这么多
SLEEP_WANT_LO = 0.55  # 困意从这里开始想睡
SLEEP_WANT_HI = 0.95  # 到这里很想睡；到 1 撑不住，就地睡
NAP_DROP = 0.45  # 食物不够冬眠时只打盹，困意降这么多就醒（不扣食物、不加业力）
NAP_FLOOR = 0.25

# 意图
INTENT_TEMP = 0.10
HANG_UTIL = 0.35  # 接着闲待
HANG_HOLD_MIN = 800  # 选了闲待后待这么久再重选（tick）
HANG_HOLD_MAX = 2400
PLAY_UTIL = 0.40  # 玩：× 好动程度，体力低、困了都降
HUNGRY_PLAY_DAMP = 0.25  # 饿着又没吃的时玩的意愿最多降这么多
REST_WANT_HI = 0.45  # 体力低于这里开始想歇
REST_WANT_LO = 0.15  # 到这里很想歇
REST_TICKS = 600  # 歇一会趴这么久
REST_DONE_ENERGY = 0.6
EAT_OPP_UTIL = 0.30  # 顺手吃
EAT_BED_UTIL = 1.1  # 睡前要吃够
EAT_BED_LO = 0.5
EAT_BED_HI = 0.85
EAT_URGENT = 0.6  # 睡前要吃够到这里就打断手头的事
WARM_UTIL = 1.2  # 冷：× 冷的程度

# 爬架
PERCH_UTIL = 0.3  # 去爬架
PERCH_COST_LIMIT = 1200  # 只考虑这么多 tick 内走得到的位置
PERCH_CROWD_R = 30.0  # 离别的猫或它预约的位置这么近的不去
PERCH_NEARBY = 0.5  # 换地方时留在同一根杆上的概率
PERCH_DWELL_MIN = 600  # 到点后待这么久，吊着、爬着的减半
PERCH_DWELL_MAX = 2000
PERCH_BORED = 0.8  # 这一趟每多待一处，换地方的意愿乘这么多

# 撞击伤害；晕、死的速度阈值按猫种，见 SlugStats.fall_*_speed
FALL_STUN_MIN = 40  # 晕 tick，按速度在两档之间插值
FALL_STUN_MAX = 140
DRAG_IMPACT_MAX_SCALE = 6.0  # 拖拽时补回被限速的部分，最多放大这么多
# 被光标抓着甩：持续高速同向转圈就晕
SPIN_STUN_DEG_PER_S = 900.0
SPIN_STUN_TICKS = 120
SPIN_STUN_DURATION = 200

# 好感
TEMPER_SWING_SPEED = 10.0
TEMPER_SWING_RATE = -0.0008
TEMPER_STUN = -0.10
TEMPER_KILL_CANCEL_HUMAN = -0.10
TEMPER_KILL_REVIVED = -0.50
TEMPER_FEED = 0.20
TEMPER_DECAY = 1.0 / 180000.0
TEMPER_SNATCH = -0.06  # 手里东西被光标抢走
SNATCH_ANGER_TEMPER = -0.35  # 被抢时好感低于此就生气

# 手持
HUNGER_URGENT_FRAC = 0.5  # 饱食低于上限的这一比例算真饿：拿到就吃
SNACK_DELAY_MIN = 600  # 有点饿时拿着的东西过多久再吃（tick）
SNACK_DELAY_MAX = 2400
ARM_TEMPER = -0.25  # 好感低于此会捡块石头揣着
ARM_TEMPER_HYST = 0.10  # 好感回升过 ARM_TEMPER + 此值才放下
SPEAR_TEMPER = -0.55  # 好感低于此才拿矛当武器，且比石头优先；回升过此值 + ARM_TEMPER_HYST 放下
SPEAR_PREF = 0.35  # 拿矛优先：挑武器时矛的距离乘此值
DRAG_THROW_TEMPER = -0.25  # 被拎起时好感低于此可能把石头朝光标扔

# 寒冷、暴风雪、暖灯供暖、转世
COLD_BLIZZARD_DEFAULT_OFF = True
COLD_BLIZZARD_RAMP = 2400
COLD_BLIZZARD_HOLD = 2400
COLD_BLIZZARD_TOTAL = 2 * COLD_BLIZZARD_RAMP + COLD_BLIZZARD_HOLD
COLD_EXPOSURE = 1.0
COLD_GAIN_CLAMP_HI = 0.0055
COLD_LAMP_WARMTH = 0.0005
COLD_LAMP_RANGE = 350.0
COLD_LAMP_SCALE = 0.6
COLD_CRAMP_GAIN_GATE = 0.0003
COLD_DEATH_STUN = 50
COLD_WARMTH_INNER = 70.0
COLD_NATURAL_DECAY = 0.001
REINCARNATE_TICKS = 600

# 自主趋暖与冻醒
COLD_SEEK_ENTER = 0.30
COLD_SEEK_EXIT = 0.10
COLD_NOSLEEP = 0.20
COLD_ARRIVE_FRAC = 0.8

# 雪与霜冻氛围
SNOW_ENABLED = True
SNOW_MAX_FLAKES = 50
SNOW_VIGNETTE_MAX = 15

# 雨（默认关）
RAIN_AMOUNT = 0.4  # 默认雨量，0.5 以上露天会被推、砸晕
RAIN_SHELTER_POLL_MS = 250  # 下雨时取挡雨窗口的间隔
WINDOW_BAR_POLL_MS = 120  # 刷新窗口虚拟杆的间隔（窗口一动就要跟着变）
RAIN_FPS = 30  # 雨层的出帧率
SNOW_FPS = 24  # 雪层的出帧率（雪要整屏重绘，比物理 tick 的 40Hz 慢一档省很多 CPU）
RAIN_VOLUME = 0.6  # 默认雨声音量
RAIN_ITEM_KICK_MAX = 3.0  # 物品单次被雨推的速度上限

# 水环境（默认关）
WATER_FULL_DEPTH = 0.55
WATER_EASE_TICKS = 400
WATER_STILL_EPS = 0.15
WATER_SPACING = 20.0
WATER_FLOW = 0.08
WATER_BODY_RGBA = (46, 120, 150, 92)
WATER_SURFACE_RGBA = (150, 214, 232, 175)
WATER_THREAT_SAFE_DEPTH = 60.0

# 游泳/憋气/淹死（y↓）
SWIM_ENTER = 0.22
SWIM_EXIT = 0.10  # 出水阈值，低于入水阈值形成滞回
SWIM_SUB_FILTER = 0.35  # 游泳时浸没度低通系数
SWIM_DEEP_DEPTH = 30.0
SWIM_DEEP_DIVE_DEPTH = 10.0
SWIM_DEEP_FULL = 80.0
SWIM_DEEP_HIP_SUB = 0.6
SWIM_BOOST_MIN_AIR = 0.5
SWIM_BOOST_DIST = 60.0
SWIM_SURFACE_HEAD_ABOVE = 15.0
SWIM_LUNG_SUBMERGE = 0.9
SWIM_DROWN_SUB_HIP = 0.5
SWIM_DROWN_STEP = 1.0 / 120.0
SWIM_LUNG_RECOVER = 60.0
SWIM_LUNG_RECOVER_EXH = 240.0
SWIM_ARRIVE_R = 34.0
SWIM_ARRIVE_X = 6.0  # 横向死区，免得在目标正下方来回抖
SWIM_FETCH_SEEK_R = 220.0
SWIM_FETCH_REACH = 22.0
SWIM_VEL_MAX = 45.0
SWIM_SURFACE_REST_FAC = 0.5
SWIM_STOP_DAMP = 0.90  # 无横游意图时的水平阻尼
SWIM_TURN_DOT = 0.35
# 累了或缺氧：浮到水面歇着（滞回）
SWIM_REST_ENERGY_IN = 0.20
SWIM_REST_ENERGY_OUT = 0.45
SWIM_REST_ABOVE = 15.0  # 歇着时头露出水面的高度
SWIM_REST_ENERGY_REC_FAC = 3.0  # 歇着时体力恢复倍率（× EN_REC_IDLE）
SWIM_REST_RECOVER_MULT = 0.4
# 水里错开：下潜从下面过，或从水面小跳过去
SWIM_PASS_TICKS = 28
SWIM_PASS_COOLDOWN = 26
SWIM_PASS_DIVE_MIN = 48.0  # 下潜深度（水面以下）
SWIM_PASS_DIVE_MAX = 92.0
SWIM_PASS_SINK_GAIN = 0.10
SWIM_PASS_SINK_ACCEL_CAP = 1.1
SWIM_PASS_DIVE_KICK = 1.8
SWIM_PASS_DIVE_CAP = 3.2
SWIM_PASS_EVADE_VX = 1.6
SWIM_LEAP_HEAD = 7.5  # 上跳冲量
SWIM_LEAP_FEET = 7.0
SWIM_LEAP_VX = 1.3
SWIM_LEAP_EVADE_VX = 3.2
SWIM_LEAP_FALL_CAP = 2.5
# 漂到目标后停一会再选下一个点
SWIM_IDLE_HOLD_MIN = 120
SWIM_IDLE_HOLD_MAX = 520
# 漂游潜深随 swim_zeal 插值
SWIM_DRIFT_DEPTH_MIN = 15.0
SWIM_DRIFT_DEPTH_MAX = 70.0
SWIM_DRIFT_DEEP_MAX = 260.0
SWIM_BOOST_DIST_ZEAL = 25.0

# 自动爆跳：起跳后第几 tick 点火，弧线模拟和爆破行为共用
PYRO_BOOST_AIR_TICKS = 6

# 溺水吐泡
BUBBLE_MAX = 40
BUBBLE_DRAW_SCALE = 0.45
BUBBLE_RGBA = (0, 1, 0)
BUBBLE_OPACITY = 0.25
BUBBLE_INHERIT_VEL = 0.025
BUBBLE_SPAWN_KICK = 0.5

# 待机兜底：东张西望
LOOK_UPDATE_PROB = 0.1
LOOK_NOTHING_PROB = 0.0025
LOOK_INTEREST_DECAY_UPDATES = 8  # 评估这么多次后开始看腻
LOOK_MIN_INTEREST = 0.20
LOOK_DIST_NEAR = 400.0
LOOK_CURSOR_BASE = 1.00
LOOK_ITEM_BASE = 0.80
# 待机兜底：踱步
PACE_PROB = 0.0016
# 待机走位：按 sociability 决定靠近、远离或随机
SOCIAL_WANDER_LO = 0.4
SOCIAL_WANDER_HI = 0.6
SOCIAL_WANDER_SAMPLES = 11
SOCIAL_WANDER_SIGMA_FRAC = 0.15
SOCIAL_WANDER_MOVE_W = 0.6
SOCIAL_WANDER_CROSS_W = 0.8
SOCIAL_WANDER_STAY_GAIN = 0.05
SOCIAL_WANDER_STAY_SPAN_FRAC = 0.06
# 待机对视：两只发呆的猫靠近时偶尔对视
STARE_DIST_MAX = 220.0
STARE_DIST_NEAR = 70.0
STARE_DECAY_MULT = 0.62  # 邻近度指数，压低中距离的对视
STARE_BASE_PROB = 0.0018  # 最远处每 tick 概率
STARE_NEAR_PROB = 0.020  # 最近处每 tick 概率
STARE_LOCK_MIN = 55
STARE_LOCK_MAX = 150
STARE_COOLDOWN_MIN = 300
STARE_COOLDOWN_MAX = 850
STARE_ENGAGE_DIST = 22.0
STARE_ENGAGE_MULT = 0.3

# 站杆顶 / 横杆上的平衡
BAL_MAX = 120.0
BAL_COUNTER_WRAP = 300.0
BAL_SWAY_X = 0.08
BAL_SWAY_Y = 0.02

# 取物
GRAB_REACH = 18.0
REACH_GATE_K = 2.0

# 运动规划：几何覆盖、粗略线性代价、执行器失败与重规划
PLAN_WALK_SPEED = 4.2
PLAN_CLIMB_SPEED = 1.6
PLAN_STARTUP_TICKS = 20.0
PLAN_STAND_REACH_H = 17.0 + GRAB_REACH
PLAN_FLOOR_TOL = 12.0
PLAN_WALK_X_PAD = 30.0
PLAN_EN_RATE_LIGHT = 1.0 / 4800.0
PLAN_EN_RATE_VIGOROUS = 1.0 / 1200.0
PLAN_PROGRESS_MIN = 20.0
PLAN_REPLAN_BUDGET = 8
PLAN_COOLDOWN_TICKS = 1200
PLAN_FAILS_PER_SCHEME = 2
PLAN_SCHEMES_MAX = 2
PLAN_STEP_TIMEOUT_MIN = 240.0
PLAN_STEP_TIMEOUT_K = 3.0
PLAN_ARRIVE_EPS = 14.0
PLAN_ARRIVE_HOLD = 30
PLAN_JUMP_HOLD_GEARS = (0, 3, 6)
PLAN_JUMP_TAKEOFF_EPS = 6.0

# 光标驻留：在高度带内几乎不动时累计 tick，舔光标和光标劫持共用
CURSOR_DWELL_BAND_LO = 0.50  # 高度带上沿（占工作区高比例）
CURSOR_DWELL_BAND_HI = 0.75  # 高度带下沿
CURSOR_DWELL_TOL = 6.0  # 每 tick 位移小于此（px）算没动
CURSOR_DWELL_TICKS = 200  # 光标在带内停这么久算驻留
CURSOR_SPEED_RELEASE = 12.0  # 光标平滑速度超过此（px/tick）算甩开

# 听歌摇摆：多数机器不暴露音频电平（本机实测 E_NOINTERFACE），读不到真实节拍，
# 所以按固定拍子走，观感上像在跟着晃。幅度再乘性格 activity。
MUSIC_SWAY_ON = True
MUSIC_SWAY_BPM = 96.0  # 固定拍子
MUSIC_SWAY_DEG = 3.5  # 躯干倾角（度）。别调大：静态歪着看着像驼背，不像在晃
MUSIC_SWAY_SHIFT_X = 2.6  # 重心左右移（px）——摇摆主要靠这个
MUSIC_SWAY_SHIFT_Y = 1.4  # 上下弹（px），每拍一次
MUSIC_SWAY_HEAD_X = 1.8  # 头跟着摆的横移（px）
MUSIC_SWAY_HEAD_Y = 1.2  # 点头的上下幅度（px）
MUSIC_SWAY_ON_TICKS = (320, 480)  # 摇 8~12 秒（40 tick/s）
MUSIC_SWAY_OFF_TICKS = (120, 200)  # 歇 3~5 秒
MUSIC_SWAY_EASE = 0.045  # 淡入淡出：每 tick 向目标靠近的比例
MUSIC_SWAY_ACT_BASE = 0.4  # 性格活跃度 → 幅度：base + gain × activity
MUSIC_SWAY_ACT_GAIN = 1.2  # activity 0.4 → 0.88 倍；0.95 → 1.54 倍

# 光标劫持被左键打断：抢光标时鼠标是真被 ClipCursor 锁住的，打游戏时尤其要命，
# 所以只要左键一按就立刻还回去。冷却是为了不变成"点一下松一下"的拉锯。
CURSOR_BREAK_LBUTTON = True
CURSOR_BREAK_COOLDOWN = 200  # 打断后这么久不再抢光标（tick，200 = 5 秒）

# 被摸（享受）：光标在猫身上上下来回搓，搓够了就眯眼晃起来；摸久了会腻，抖一下躲开。
# 只在猫站着发呆或趴着时受理，不进物理、不打断别的行为。
PET_ON = True
PET_PAD = 6.0  # 命中猫身的外扩（逻辑 px），跟穿透判定用同一个
PET_STROKE_MIN = 7.0  # 一个方向上至少滑这么远（px）才算划了一下，路过的抖动不算
PET_TURN_GAP = 20  # 光标离开猫身这么久（tick）没回来，计数清零
PET_STROKES_NEED = 3  # 上下来回搓这么多次开始享受（约 1 秒）
PET_EASE = 0.06  # 享受强度淡入淡出：每 tick 向目标靠近的比例
PET_BPM = 52.0  # 享受摇晃的节奏，比听歌（96）慢一半，慢悠悠的
PET_SHIFT_X = 3.4  # 重心左右移（px）——享受主要靠这个
PET_SHIFT_Y = 1.0  # 上下弹（px）
PET_TILT_DEG = 2.0  # 躯干倾角（度）。别调大：静态歪着看着像驼背，不像在晃
PET_HEAD_X = 1.4  # 头跟着摆的横移（px）
PET_HEAD_LIFT = 2.2  # 抬头（px，向上）。享受时会微微仰头
PET_BLINK = 4  # 享受时维持的闭眼帧计数（>0 走 face_blink，也就是眯着眼）
PET_BORE_TICKS = 480  # 享受累计这么久就腻（12 秒）
PET_BORE_DECAY = 2  # 不摸的时候余韵每 tick 退这么多，摸摸停停也能累计到腻
PET_TEMPER_EVERY = 60  # 享受时每隔这么久涨一次好感（tick）
PET_TEMPER_GAIN = 0.03  # 每次涨的好感（舔一次光标是 0.10，比那个慢）
PET_TEMPER_CAP = 0.18  # 一轮享受最多涨这么多，别让人一直搓着刷好感
PET_BORE_TEMPER = -0.04  # 摸腻了掉的好感
PET_SHOO_KICK = 2.6  # 腻了甩你一下：上半身的横向冲量（px/tick）
PET_COOL_TICKS = 600  # 腻了之后的冷却（15 秒），这段时间再摸没反应——等于躲开你
