"""帧显示列表：tick 里记录绘制调用与精确范围，paintEvent 回放。"""

from __future__ import annotations

from numbers import Real

from PySide6.QtCore import QLineF, QPoint, QPointF, QRect, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygon,
    QPolygonF,
    QRegion,
    QTransform,
)

_AA = 2.0  # 抗锯齿 / 取整外扩（设备 px）
_EVERYTHING = QRectF(-1e7, -1e7, 2e7, 2e7)
_RECT_CAP = 16  # 每帧交给 Qt 的矩形条数上限，超了就合并
_GAPS = (64, 160, 400, 1000)  # 合并时逐轮放宽的横向间隙（设备 px）

_EVERY_RECT = _EVERYTHING.toAlignedRect()


def _num(a):
    return isinstance(a, Real)


def _aligned(d):
    return d.adjusted(-_AA, -_AA, _AA, _AA).toAlignedRect()


def union_rect(rects) -> QRect:
    """一堆矩形的包围盒（设备坐标）。"""
    out = QRect()
    for r in rects:
        if r is None or r.isEmpty():
            continue
        out = out.united(r if isinstance(r, QRect) else _aligned(r))
    return out


def merge_rects(rects, cap=_RECT_CAP):
    """把一堆矩形并成尽量少的几个，只合并靠得近的，别把分散的猫并成一个大包围盒。

    按左边排序后贪心：后一个的左边界落在前一个右边界 + gap 之内就并掉。
    间隙逐轮放宽，直到条数不超过 cap。
    """
    rs = [r if isinstance(r, QRect) else _aligned(r) for r in rects]
    rs = [r for r in rs if r.isValid() and not r.isEmpty()]
    if len(rs) <= cap:
        return rs
    for gap in _GAPS:
        rs.sort(key=lambda r: r.left())
        out = []
        for r in rs:
            if out and r.left() <= out[-1].right() + gap:
                out[-1] = out[-1].united(r)
            else:
                out.append(r)
        rs = out
        if len(rs) <= cap:
            break
    return rs


def _pix_size(img):
    dpr = img.devicePixelRatio() or 1.0
    return img.width() / dpr, img.height() / dpr


def _image_rect(args):
    a0 = args[0]
    if isinstance(a0, (QRect, QRectF)):
        return QRectF(a0)
    k = next((i for i, a in enumerate(args) if isinstance(a, (QPixmap, QImage))), None)
    if k is None:
        return None
    img, rest = args[k], args[k + 1 :]
    src = rest[0] if rest and isinstance(rest[0], (QRect, QRectF)) else None
    if src is None and len(rest) >= 4 and all(_num(v) for v in rest[:4]):
        src = QRectF(*rest[:4])
    w, h = (src.width(), src.height()) if src is not None and src.width() > 0 else _pix_size(img)
    if isinstance(a0, (QPoint, QPointF)):
        return QRectF(a0.x(), a0.y(), w, h)
    head = args[:k]
    if len(head) == 4 and all(_num(v) for v in head):
        return QRectF(*head)
    if len(head) == 2 and all(_num(v) for v in head):
        return QRectF(head[0], head[1], w, h)
    return None


def _rect_arg(args):
    a0 = args[0]
    if isinstance(a0, (QRect, QRectF)):
        return QRectF(a0)
    if len(args) >= 4 and all(_num(v) for v in args[:4]):
        return QRectF(*args[:4])
    return None


def _ellipse_rect(args):
    a0 = args[0]
    if isinstance(a0, (QPoint, QPointF)) and len(args) >= 3:
        rx, ry = args[1], args[2]
        return QRectF(a0.x() - rx, a0.y() - ry, 2 * rx, 2 * ry)
    return _rect_arg(args)


def _line_rect(args):
    a0 = args[0]
    if isinstance(a0, QLineF) or hasattr(a0, "p1"):
        p1, p2 = a0.p1(), a0.p2()
    elif len(args) >= 2 and isinstance(a0, (QPoint, QPointF)):
        p1, p2 = a0, args[1]
    elif len(args) >= 4 and all(_num(v) for v in args[:4]):
        p1, p2 = QPointF(args[0], args[1]), QPointF(args[2], args[3])
    else:
        return None
    return QRectF(QPointF(p1), QPointF(p2)).normalized()


def _poly_rect(args):
    a0 = args[0]
    if hasattr(a0, "boundingRect"):
        return QRectF(a0.boundingRect())
    return None


_NOPEN = Qt.PenStyle.NoPen
_MUT = (QPen, QBrush, QColor, QFont, QPolygonF, QPolygon, QPainterPath, QTransform, QRegion)


def _freeze(a):
    """可变值类型拷一份（隐式共享，O(1)），防止绘制代码事后改动已记录的参数。"""
    return tuple(type(v)(v) if isinstance(v, _MUT) else v for v in a)


class FrameRecorder(QPainter):
    _dummy = None

    def __init__(self, font=None):
        if FrameRecorder._dummy is None:
            FrameRecorder._dummy = QImage(1, 1, QImage.Format.Format_ARGB32_Premultiplied)
        super().__init__(FrameRecorder._dummy)
        if font is not None:
            QPainter.setFont(self, font)  # 与窗口 painter 初始字体一致，不入列表
        self.ops = []
        self._rs = []  # 每条绘制的范围（设备坐标，未含 AA 外扩），刷屏时按需合并
        self._sb = None  # 静态内容的范围，不算进每帧的刷新范围
        self._static = 0
        self._everything = False

    def static_begin(self):
        """之后画的是静态内容。"""
        self._static += 1

    def static_end(self):
        self._static -= 1

    def _add(self, r, stroke=True):
        if r is None:
            self._everything = True
            return
        d = self.transform().mapRect(r)
        if stroke:
            pen = self.pen()
            if pen.style() != _NOPEN:
                pad = max(pen.widthF(), 1.0) * 0.5 * max(1.0, self.transform().m11())
                d = d.adjusted(-pad, -pad, pad, pad)
        if self._static:
            self._sb = d if self._sb is None else self._sb.united(d)
        else:
            self._rs.append(d)

    def static_rect(self) -> QRect:
        if self._sb is None:
            return QRect()
        return _aligned(self._sb)

    def device_rect(self) -> QRect:
        """包围盒。只用于「有没有画东西」之类判断，刷屏请用 device_rects。"""
        if self._everything:
            return _EVERY_RECT
        return union_rect(self._rs)

    def device_rects(self):
        """本帧要刷的矩形列表（设备坐标，含 AA 外扩），已合并到 _RECT_CAP 条以内。"""
        if self._everything:
            return [_EVERY_RECT]
        return merge_rects(self._rs)

    # 热路径：blit() 的 drawPixmap(QPointF, QPixmap)
    def drawPixmap(self, *a, _m=QPainter.drawPixmap):
        if len(a) == 2 and type(a[1]) is QPixmap:
            pt, pm = a
            dpr = pm.devicePixelRatio()
            r = QRectF(pt.x(), pt.y(), pm.width() / dpr, pm.height() / dpr)
        else:
            r = _image_rect(a)
            a = _freeze(a)
        self._add(r, False)
        self.ops.append((_m, a))

    def sprite(self, x, y, rot, sx, sy, pt, pm):
        """blit 快路径：直接算出世界变换，录成一条操作，等价于 save/平移/旋转/缩放/drawPixmap/restore。"""
        t = self.transform()
        t.translate(x, y)
        if rot:
            t.rotate(rot)
        t.scale(sx, sy)
        dpr = pm.devicePixelRatio()
        d = t.mapRect(QRectF(pt.x(), pt.y(), pm.width() / dpr, pm.height() / dpr))
        if self._static:
            self._sb = d if self._sb is None else self._sb.united(d)
        else:
            self._rs.append(d)
        self.ops.append((_sprite, (t, pt, pm)))


def _sprite(p, t, pt, pm):
    p.save()
    p.setWorldTransform(t)
    p.drawPixmap(pt, pm)
    p.restore()


def _plain(name):
    m = getattr(QPainter, name)

    def f(self, *a):
        self.ops.append((m, a))
        m(self, *a)

    f.__name__ = name
    return f


def _copying(name):
    m = getattr(QPainter, name)

    def f(self, *a):
        a = _freeze(a)
        self.ops.append((m, a))
        m(self, *a)

    f.__name__ = name
    return f


def _draw(name, extract, stroke=True):
    m = getattr(QPainter, name)

    def f(self, *a):
        self._add(extract(a) if extract else None, stroke)
        self.ops.append((m, _freeze(a)))

    f.__name__ = name
    return f


# 参数都是不可变标量/枚举/QPointF 的状态调用：不拷贝
for _n in (
    "save",
    "restore",
    "translate",
    "rotate",
    "scale",
    "shear",
    "setOpacity",
    "setRenderHint",
    "setRenderHints",
    "setCompositionMode",
    "setClipRect",
    "setClipping",
    "resetTransform",
    "setBrushOrigin",
    "setBackgroundMode",
    "setLayoutDirection",
    "setViewport",
    "setWindow",
    "setViewTransformEnabled",
    "setWorldMatrixEnabled",
):
    setattr(FrameRecorder, _n, _plain(_n))
# 可能传入可变 Qt 值对象的状态调用：拷贝
for _n in (
    "setPen",
    "setBrush",
    "setFont",
    "setTransform",
    "setWorldTransform",
    "setClipPath",
    "setClipRegion",
    "setBackground",
):
    setattr(FrameRecorder, _n, _copying(_n))

for _n, _ex, _st in (
    ("drawImage", _image_rect, False),
    ("drawEllipse", _ellipse_rect, True),
    ("drawLine", _line_rect, True),
    ("drawPolygon", _poly_rect, True),
    ("drawPolyline", _poly_rect, True),
    ("drawConvexPolygon", _poly_rect, True),
    ("drawRect", _rect_arg, True),
    ("drawRoundedRect", _rect_arg, True),
    ("fillRect", _rect_arg, False),
):
    setattr(FrameRecorder, _n, _draw(_n, _ex, _st))


def _drawPath(self, path):
    self._add(path.controlPointRect())
    self.ops.append((QPainter.drawPath, (QPainterPath(path),)))


def _fillPath(self, path, brush):
    self._add(path.controlPointRect(), stroke=False)
    self.ops.append((QPainter.fillPath, _freeze((path, brush))))


def _strokePath(self, path, pen):
    w = pen.widthF()
    self._add(path.controlPointRect().adjusted(-w, -w, w, w), stroke=False)
    self.ops.append((QPainter.strokePath, _freeze((path, pen))))


def _drawText(self, *a):
    self._add(_rect_arg(a) if isinstance(a[0], (QRect, QRectF)) else None)
    self.ops.append((QPainter.drawText, _freeze(a)))


FrameRecorder.drawPath = _drawPath
FrameRecorder.fillPath = _fillPath
FrameRecorder.strokePath = _strokePath
FrameRecorder.drawText = _drawText

# 其余绘制方法算不准范围：记为整窗
for _n in (
    "drawArc",
    "drawChord",
    "drawPie",
    "drawPoint",
    "drawPoints",
    "drawLines",
    "drawRects",
    "drawTiledPixmap",
    "drawStaticText",
    "drawGlyphRun",
    "drawPicture",
    "drawPixmapFragments",
    "eraseRect",
):
    setattr(FrameRecorder, _n, _draw(_n, None))


def replay(p: QPainter, ops) -> None:
    for m, a in ops:
        m(p, *a)
