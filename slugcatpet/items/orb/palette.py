"""珍珠配色与贴图模板。

色值不是估的：把雨世界 wiki 上官方珍珠贴图（11×11 格的小球）逐颗下载下来，
读每个像素取出现最多的那个颜色，得到的就是本色。暗部不用灰色，而是本色压暗。

珍珠本体的模板（11×11 格，A=黑描边 C=本色 B=压暗的内缘环）：

    ...AAAAA...
    ..ABCCCBA..
    .ACCCCCCCA.
    ABCCCCCCCBA
    ACCCCCCCBCA
    ACCCCCCCBCA
    ACCCCCCCBCA
    ABCCCCCBCBA
    .ACCBBBCCA.
    ..ABCCCBA..
    ...AAAAA...

三层，没有高光、没有渐变、没有漩涡。游戏的"闪闪发光"靠偶尔闪一下的光，见 model.py。
"""

from __future__ import annotations

# 原作珍珠直径就是 11 格（桌面宠物同样用 20px 一格，所以是原尺寸）
GRID_W = 11

# 有几颗"暗"珍珠暗到几乎全黑（如天空群岛的暗蓝 13,45,66），
# 在亮桌面上会和描边糊成一团，统一把最亮通道抬到这个数，颜色关系不变
_MIN_MAX = 90

GRID = (
    "...AAAAA...",
    "..ABCCCBA..",
    ".ACCCCCCCA.",
    "ABCCCCCCCBA",
    "ACCCCCCCBCA",
    "ACCCCCCCBCA",
    "ACCCCCCCBCA",
    "ABCCCCCBCBA",
    ".ACCBBBCCA.",
    "..ABCCCBA..",
    "...AAAAA...",
)

# （名字, 地区/出处, 本色 RGB）
PEARLS: tuple[tuple[str, str, tuple[int, int, int]], ...] = (
    ("白珍珠", "通用", (179, 179, 179)),
    ("粉白珍珠", "通用", (255, 153, 229)),
    ("广播珍珠", "非矛大师流程", (232, 198, 210)),
    ("浅蓝色珍珠", "郊区", (147, 168, 233)),
    ("浅粉色珍珠", "郊区", (255, 201, 233)),
    ("亮蓝色珍珠", "工业区", (34, 91, 255)),
    ("深翠绿色珍珠", "垃圾堆", (32, 198, 143)),
    ("沉黄色珍珠", "垃圾堆", (233, 244, 82)),
    ("亮绿色珍珠", "排水系统", (38, 190, 60)),
    ("深洋红色珍珠", "阴影城堡", (132, 20, 81)),
    ("深紫色珍珠", "管道堆场", (195, 13, 245)),
    ("金色珍珠", "烟囱天棚", (242, 204, 25)),
    ("白绿色珍珠", "高墙", (125, 164, 125)),
    ("赞美诗珍珠", "腐化之地", (176, 47, 251)),
    ("赞美诗珍珠（褪色）", "无声构造", (189, 73, 255)),
    ("暗蓝色珍珠", "天空群岛", (13, 45, 66)),
    ("暗绿色珍珠", "天空群岛", (13, 66, 45)),
    ("暗紫色珍珠", "天空群岛", (45, 13, 66)),
    ("橄榄绿色珍珠", "天空群岛", (45, 66, 13)),
    ("暗洋红色珍珠", "天空群岛 / 地下", (66, 13, 45)),
    ("深粉色珍珠", "农场阵列", (255, 38, 103)),
    ("亮红色珍珠", "农场阵列", (255, 60, 60)),
    ("明水鸭色珍珠", "地下", (60, 147, 147)),
    ("亮紫色珍珠", "海岸线", (148, 53, 237)),
    ("亮洋红色珍珠", "海岸线", (255, 27, 180)),
    ("白黄色珍珠", "海岸线", (233, 244, 82)),
    ("浅黄色珍珠", "沉没巨构", (246, 238, 83)),
    ("深绿色珍珠", "大都会", (38, 125, 42)),
    ("黄铜色珍珠", "大都会", (194, 102, 0)),
    ("浅紫色珍珠", "外层空间", (157, 118, 212)),
    ("海蓝色珍珠", "猎手腹内", (153, 255, 229)),
    ("暗红色珍珠", "矛大师腹内", (126, 2, 10)),
    ("灰绿色珍珠", "溪流腹内", (166, 227, 174)),
)

WHITE = 0  # 白珍珠：原作里绝大多数珍珠都是白的
GOLD = PEARLS.index(next(p for p in PEARLS if p[0] == "金色珍珠"))

# 暗部 = 本色压暗；原作各颗实测 0.42~0.54，取 0.47
SHADE = 0.47


def _lift(c: tuple[int, int, int]) -> tuple[int, int, int]:
    m = max(c)
    if m >= _MIN_MAX:
        return c
    k = _MIN_MAX / m
    return tuple(min(255, round(v * k)) for v in c)


def body_rgb(i: int) -> tuple[int, int, int]:
    """第 i 种珍珠的本色。"""
    return _lift(PEARLS[i][2])


def shade_rgb(i: int) -> tuple[int, int, int]:
    """第 i 种珍珠的暗部（本色压暗）。"""
    return tuple(round(v * SHADE) for v in body_rgb(i))


def _runs(ch: str) -> tuple[tuple[int, int, int], ...]:
    """模板里某一层的横向连续段（x, y, 长度），单位是格。"""
    out = []
    for y, row in enumerate(GRID):
        x = 0
        while x < GRID_W:
            if row[x] == ch:
                s = x
                while x < GRID_W and row[x] == ch:
                    x += 1
                out.append((s, y, x - s))
            else:
                x += 1
    return tuple(out)


RUNS_OUTLINE = _runs("A")
RUNS_SHADE = _runs("B")
RUNS_BODY = _runs("C")

N_COLORS = len(PEARLS)
