"""植物再生：果子、黏菌被猫吃掉后，隔几秒在原地再长一个。

只认「被猫吃掉」：手动移除 / 清场走的是 kind.drop()，那里会 forget() 掉落脚点，不再生。
没有动画，到点直接用 win.spawn() 生成。
"""

from __future__ import annotations

from .state import ItemState

HOME_ATTR = "_plant_home"  # win 上挂的 {id(物体): 它最后停着的位置}
QUEUE_ATTR = "_plant_queue"  # win 上挂的 {物品 key: [[x, y, 剩余 tick], ...]}

RESTING = (ItemState.FREE, ItemState.HANGING, ItemState.STUCK)
RETRY_TICKS = 40  # 到上限腾不出位置时，隔这么久再试


def _bag(win, attr):
    d = getattr(win, attr, None)
    if d is None:
        d = {}
        setattr(win, attr, d)
    return d


def forget(win, obj):
    """手动移除：连落脚点一起忘掉，于是不再生。"""
    _bag(win, HOME_ATTR).pop(id(obj), None)


def _delay_ticks(win, secs) -> int:
    return max(1, int(round(float(secs) / getattr(win, "_PHYS_DT", 0.025))))


def step(win, kind):
    """每 tick：先补种到点的，再记落脚点、登记刚被吃掉的。"""
    queue = _bag(win, QUEUE_ATTR)
    if not getattr(win, "cfg_plant_regen", False):
        queue.pop(kind.key, None)
        return
    pending = queue.get(kind.key)
    if pending:
        left = []
        for item in pending:
            item[2] -= 1
            if item[2] > 0:
                left.append(item)
                continue
            if win.spawn(kind.key, item[0], item[1]) is None:
                item[2] = RETRY_TICKS
                left.append(item)
        if left:
            queue[kind.key] = left
        else:
            queue.pop(kind.key, None)
    homes = _bag(win, HOME_ATTR)
    delay = _delay_ticks(win, getattr(win, "cfg_plant_regen_secs", 8.0))
    for o in kind.objects(win):
        st = o.state
        if st in RESTING:
            homes[id(o)] = (o.x, o.y)
        elif st == ItemState.EATEN:
            pos = homes.pop(id(o), None)
            if pos is not None:
                queue.setdefault(kind.key, []).append([pos[0], pos[1], delay])
