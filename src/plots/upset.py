"""UpSet plot — pure renderer (dialog + bundle 공유).

render_upset(fig, df, params) 는 UpsetPlotDialog._do_plot 과 재현 번들 스크립트가 공유한다.
입력 df 는 long-format 멤버십 테이블: 컬럼 dataset(라벨), item(peak_id/gene). 데이터셋별
집합을 재구성해 upsetplot 으로 그린다. upsetplot 의존(없으면 안내 메시지).

upsetplot 은 pandas>=3.0(Copy-on-Write)·numpy>=2.0 환경에서 깨지므로 두 개의 호환 패치를
동봉하고 render 시점에 적용한다(idempotent). Qt 비의존.
"""
import numpy as np
import pandas as pd


def _patched_plot_matrix(self, ax):
    """upsetplot.UpSet.plot_matrix의 pandas 3.0 Copy-on-Write 호환 패치.

    원본은 `styles[col].fillna(value, inplace=True)` (chained assignment)를 사용하는데,
    pandas>=3.0의 강제 CoW 하에서는 이 inplace 호출이 no-op이 되어 facecolor 등이 NaN으로
    남고 scatter가 'Invalid RGBA argument: nan'으로 실패한다. fillna만 비-inplace 대입으로 교체.
    """
    ax = self._reorient(ax)
    data = self.intersections
    n_cats = data.index.nlevels

    inclusion = data.index.to_frame().values

    styles = [
        [
            self.subset_styles[i]
            if inclusion[i, j]
            else {"facecolor": self._other_dots_color, "linewidth": 0}
            for j in range(n_cats)
        ]
        for i in range(len(data))
    ]
    styles = sum(styles, [])
    style_columns = {
        "facecolor": "facecolors",
        "edgecolor": "edgecolors",
        "linewidth": "linewidths",
        "linestyle": "linestyles",
        "hatch": "hatch",
    }
    styles = (
        pd.DataFrame(styles)
        .reindex(columns=style_columns.keys())
        .astype(
            {
                "facecolor": "O",
                "edgecolor": "O",
                "linewidth": float,
                "linestyle": "O",
                "hatch": "O",
            }
        )
    )
    styles["linewidth"] = styles["linewidth"].fillna(1)
    styles["facecolor"] = styles["facecolor"].fillna(self._facecolor)
    styles["edgecolor"] = styles["edgecolor"].fillna(styles["facecolor"])
    styles["linestyle"] = styles["linestyle"].fillna("solid")
    del styles["hatch"]

    x = np.repeat(np.arange(len(data)), n_cats)
    y = np.tile(np.arange(n_cats), len(data))

    if self._element_size is not None:
        s = (self._element_size * 0.35) ** 2
    else:
        s = 200
    ax.scatter(
        *self._swapaxes(x, y),
        s=s,
        zorder=10,
        **styles.rename(columns=style_columns),
    )

    if self._with_lines:
        idx = np.flatnonzero(inclusion)
        line_data = (
            pd.Series(y[idx], index=x[idx])
            .groupby(level=0)
            .aggregate(["min", "max"])
        )
        colors = pd.Series(
            [
                style.get("edgecolor", style.get("facecolor", self._facecolor))
                for style in self.subset_styles
            ],
            name="color",
        )
        line_data = line_data.join(colors)
        ax.vlines(
            line_data.index.values,
            line_data["min"],
            line_data["max"],
            lw=2,
            colors=line_data["color"],
            zorder=5,
        )

    tick_axis = ax.yaxis
    tick_axis.set_ticks(np.arange(n_cats))
    tick_axis.set_ticklabels(
        data.index.names, rotation=0 if self._horizontal else -90
    )
    ax.xaxis.set_visible(False)
    ax.tick_params(axis="both", which="both", length=0)
    if not self._horizontal:
        ax.yaxis.set_ticks_position("top")
    ax.set_frame_on(False)
    ax.set_xlim(-0.5, x[-1] + 0.5, auto=False)
    ax.grid(False)


def _patched_label_sizes(self, ax, rects, where):
    """upsetplot.UpSet._label_sizes의 numpy>=2.0 호환 패치.

    원본은 `0.01 * abs(np.diff(ax.get_xlim()))` (길이 1 ndarray)를 margin으로 쓰는데,
    numpy>=2.0에서 matplotlib Text 좌표 변환이 1-요소 배열을 스칼라로 변환하지 못해
    오류가 난다. margin만 float 스칼라로 변환.
    """
    from upsetplot import util as _upsetplot_util

    if not self._show_counts and not self._show_percentages:
        return
    if self._show_counts is True:
        count_fmt = "{:.0f}"
    else:
        count_fmt = self._show_counts
        if "{" not in count_fmt:
            count_fmt = _upsetplot_util.to_new_pos_format(count_fmt)

    pct_fmt = "{:.1%}" if self._show_percentages is True else self._show_percentages

    if count_fmt and pct_fmt:
        if where == "top":
            fmt = f"{count_fmt}\n({pct_fmt})"
        else:
            fmt = f"{count_fmt} ({pct_fmt})"

        def make_args(val):
            return val, val / self.total
    elif count_fmt:
        fmt = count_fmt

        def make_args(val):
            return (val,)
    else:
        fmt = pct_fmt

        def make_args(val):
            return (val / self.total,)

    if where == "right":
        margin = float(0.01 * abs(np.diff(ax.get_xlim()))[0])
        for rect in rects:
            width = rect.get_width() + rect.get_x()
            ax.text(
                width + margin,
                rect.get_y() + rect.get_height() * 0.5,
                fmt.format(*make_args(width)),
                ha="left",
                va="center",
            )
    elif where == "left":
        margin = float(0.01 * abs(np.diff(ax.get_xlim()))[0])
        for rect in rects:
            width = rect.get_width() + rect.get_x()
            ax.text(
                width + margin,
                rect.get_y() + rect.get_height() * 0.5,
                fmt.format(*make_args(width)),
                ha="right",
                va="center",
            )
    elif where == "top":
        margin = float(0.01 * abs(np.diff(ax.get_ylim()))[0])
        for rect in rects:
            height = rect.get_height() + rect.get_y()
            ax.text(
                rect.get_x() + rect.get_width() * 0.5,
                height + margin,
                fmt.format(*make_args(height)),
                ha="center",
                va="bottom",
            )
    else:
        raise NotImplementedError("unhandled where: %r" % where)


def _apply_upset_patches():
    """upsetplot.UpSet 클래스에 호환 패치를 적용(idempotent)."""
    from upsetplot import UpSet
    UpSet.plot_matrix = _patched_plot_matrix
    UpSet._label_sizes = _patched_label_sizes


def render_upset(fig, df, params):
    """UpSet plot을 fig에 그린다. from_contents 결과 프레임 반환. 그릴 수 없으면 None.

    params: top_n(15), order(list), title
    """
    try:
        from upsetplot import UpSet, from_contents
    except ImportError:
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, "upsetplot is required to render this figure.\n"
                          "Install it with:  pip install upsetplot",
                ha='center', va='center', transform=ax.transAxes, color='#888888')
        return None

    _apply_upset_patches()

    df = df.copy() if df is not None else pd.DataFrame()
    if df.empty or 'dataset' not in df.columns or 'item' not in df.columns:
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, "No overlap data to plot.", ha='center', va='center',
                transform=ax.transAxes, color='#888888')
        return None

    order = params.get('order') or list(pd.unique(df['dataset']))
    non_empty = {}
    for lbl in order:
        items = set(df[df['dataset'] == lbl]['item'].dropna().unique())
        if items:
            non_empty[lbl] = items
    if len(non_empty) < 2:
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, "표시할 항목이 충분하지 않습니다.\n필터 조건을 조정하세요.",
                ha='center', va='center', fontsize=12, transform=ax.transAxes)
        return None

    data = from_contents(non_empty)
    upset = UpSet(
        data,
        subset_size='count',
        sort_by='cardinality',
        max_subset_rank=int(params.get('top_n', 15)),
        show_counts=True,
    )
    upset.plot(fig=fig)
    fig.suptitle(params.get('title', 'DA Peak Overlap Across Comparisons'),
                 fontsize=13, fontweight='bold')
    return data
