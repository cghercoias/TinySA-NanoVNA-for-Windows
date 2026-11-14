"""Uniformly scale the instrument panel to whatever window it lands in.

The panel is laid out in fixed logical pixels (~1560x820): every control is
hand-painted with hardcoded geometry, and the stylesheet uses fixed point
sizes. Two things follow from that:

  * on a window narrower than the design the right-hand control column gets
    cut off;
  * maximising on a big display leaves a small panel floating in a large
    window, with text that looks tiny.

Rescaling the fonts alone does not work: the painted knobs, buttons and
connectors would keep their pixel geometry and clip their new labels. Instead
the panel is rendered inside a QGraphicsView and the view transform is
recomputed on every resize. Because the scale is applied by the painter, text
and vector graphics are rendered at the final size -- sharp, not upscaled
bitmaps -- and every child widget keeps its own layout logic untouched.

Usage (inside a QMainWindow):

    self.view = FitView(root, self)      # root = the panel's content widget
    self.setCentralWidget(self.view)
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsView

FALLBACK_DESIGN = (1560, 820)


class FitView(QGraphicsView):
    """Show `content` scaled to fill the viewport, keeping its aspect ratio."""

    def __init__(self, content, parent=None, max_scale=3.0, background="#1e2530",
                 fallback=FALLBACK_DESIGN):
        super().__init__(parent)
        self.content = content
        self.max_scale = max_scale
        self.user_scale = 1.0          # multiplier from --ui-scale
        self.fallback = fallback
        self._design = None

        self.setScene(QGraphicsScene(self))
        self._proxy = self.scene().addWidget(content)
        self._proxy.setPos(0, 0)

        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setRenderHints(QPainter.RenderHint.Antialiasing
                            | QPainter.RenderHint.TextAntialiasing
                            | QPainter.RenderHint.SmoothPixmapTransform)
        self.setBackgroundBrush(QColor(background))
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)

    # -- geometry ----------------------------------------------------------
    def design_size(self):
        """Preferred size of the panel in its own (unscaled) pixels."""
        if self._design is None:
            hint = self.content.sizeHint()
            mini = self.content.minimumSizeHint()
            w = max(hint.width(), mini.width())
            h = max(hint.height(), mini.height())
            if w < 200 or h < 200:                 # not laid out yet / unknown
                w, h = self.fallback
            self._design = (w, h)
        return self._design

    def current_scale(self):
        vp = self.viewport().size()
        dw, dh = self.design_size()
        if vp.width() <= 0 or vp.height() <= 0:
            return 1.0
        s = min(vp.width() / dw, vp.height() / dh) * self.user_scale
        return max(0.2, min(s, self.max_scale))

    def refit(self):
        s = self.current_scale()
        self.resetTransform()
        self.scale(s, s)

    def set_user_scale(self, factor):
        self.user_scale = max(0.2, float(factor))
        self.refit()

    # -- events ------------------------------------------------------------
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.refit()

    def showEvent(self, event):
        super().showEvent(event)
        # the content's real sizeHint is only known once it has been laid out
        self._design = None
        self.refit()
