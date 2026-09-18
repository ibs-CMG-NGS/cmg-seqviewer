"""Quadrant 산점도 hover 툴팁 관리자.

render_quadrant()가 반환하는 scatter_data를 받아, 마우스 근처의 점을 찾아
symbol/log2FC/padj/concordance를 보여주는 annotation을 관리한다.
매번 figure.clear() 후 새 ax로 다시 그리는 다이얼로그(QuadrantPlotDialog,
MultiOmicsWorkbenchDialog)에서 공유 — 리드로우할 때마다 bind()만 다시 호출하면 된다.
"""
import numpy as np


class QuadrantHoverTooltip:
    def __init__(self, canvas):
        self.canvas = canvas
        self._ax = None
        self._annot = None
        self._scatter_data = []
        self._cid = None

    def bind(self, ax, scatter_data):
        """리드로우 직후 호출 — 새 ax/scatter_data로 hover 툴팁을 다시 붙인다."""
        self._ax = ax
        self._scatter_data = scatter_data or []

        self._annot = ax.annotate(
            "",
            xy=(0, 0), xytext=(12, 12), textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.4", fc="lightyellow", ec="gray", alpha=0.92),
            arrowprops=dict(arrowstyle="->", color="gray", lw=0.8),
            fontsize=8, zorder=10,
        )
        self._annot.set_visible(False)

        if self._cid is not None:
            self.canvas.mpl_disconnect(self._cid)
        self._cid = self.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)

    def _on_mouse_move(self, event):
        if event.inaxes is None or self._ax is None:
            if self._annot and self._annot.get_visible():
                self._annot.set_visible(False)
                self.canvas.draw_idle()
            return

        xlim = self._ax.get_xlim()
        ylim = self._ax.get_ylim()
        x_range = xlim[1] - xlim[0]
        y_range = ylim[1] - ylim[0]

        best_dist = float('inf')
        best_info = None

        ex, ey = event.xdata, event.ydata
        for data in self._scatter_data:
            if len(data['x']) == 0:
                continue
            dx = (data['x'] - ex) / (x_range or 1)
            dy = (data['y'] - ey) / (y_range or 1)
            dists = np.sqrt(dx ** 2 + dy ** 2)
            idx = int(np.argmin(dists))
            if dists[idx] < best_dist:
                best_dist = dists[idx]
                best_info = (
                    data['x'][idx],
                    data['y'][idx],
                    data['symbol'][idx],
                    data['concordance'][idx],
                    data['padj'][idx],
                )

        real_threshold = 0.025
        if best_dist < real_threshold and best_info is not None:
            x, y, sym, cat, padj = best_info
            padj_str = f"{padj:.2e}" if not np.isnan(padj) else "N/A"
            text = (
                f"{sym}\n"
                f"RNA log2FC: {y:.3f}\n"
                f"ATAC log2FC: {x:.3f}\n"
                f"RNA padj: {padj_str}\n"
                f"{cat}"
            )
            self._annot.xy = (x, y)
            self._annot.set_text(text)
            xoff = -90 if (x > (xlim[0] + xlim[1]) / 2) else 12
            yoff = -60 if (y > (ylim[0] + ylim[1]) / 2) else 12
            self._annot.xyann = (xoff, yoff)
            self._annot.set_visible(True)
            self.canvas.draw_idle()
        else:
            if self._annot and self._annot.get_visible():
                self._annot.set_visible(False)
                self.canvas.draw_idle()
