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
                 fallback=FALLBACK_DESIGN, fit="fill", stretch_limit=1.10):
        super().__init__(parent)
        self.content = content
        self.max_scale = max_scale
        self.user_scale = 1.0          # multiplier from --ui-scale
        self.fit = fit                 # fill / stretch / aspect
        self.stretch_limit = max(1.0, float(stretch_limit))
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
            # Pin the embedded widget to its design size. Without this the
            # proxy re-lays the panel out against the *scaled* viewport and the
            # content collapses (seen as a panel that grows but never fills).
            self.content.setFixedSize(w, h)
            self._design = (w, h)
        return self._design

    def current_scales(self):
        """(sx, sy) for the current viewport.

        fill    -> each axis fills the viewport, distortion capped at
                   stretch_limit; on a 16:9 window that is ~3-4%, invisible.
        stretch -> same, no cap: always fills, knobs turn elliptical when the
                   window aspect ratio is far from the panel's.
        aspect  -> one scale for both axes: no distortion, dark bars.
        """
        vp = self.viewport().size()
        dw, dh = self.design_size()
        if vp.width() <= 0 or vp.height() <= 0:
            return 1.0, 1.0
        fx = vp.width() / dw
        fy = vp.height() / dh
        if self.fit == "aspect":
            sx = sy = min(fx, fy)
        else:
            sx, sy = fx, fy
            if self.fit != "stretch":
                cap = self.stretch_limit
                if sy > sx * cap:            # window much taller than the panel
                    sy = sx * cap
                elif sx > sy * cap:          # window much wider than the panel
                    sx = sy * cap
        sx *= self.user_scale
        sy *= self.user_scale
        clamp = lambda s: max(0.2, min(s, self.max_scale))
        return clamp(sx), clamp(sy)

    def current_scale(self):
        return min(self.current_scales())

    def refit(self):
        sx, sy = self.current_scales()
        self.resetTransform()
        self.scale(sx, sy)

    def set_fit(self, mode):
        self.fit = mode if mode in ("fill", "stretch", "aspect") else "fill"
        self.refit()

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
