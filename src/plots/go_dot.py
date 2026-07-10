"""GO/KEGG enrichment dot plot — pure renderer (dialog + bundle 공유).

render_go_dot(fig, df, params) 는 GODotPlotDialog._do_plot 과 재현 번들 스크립트가 공유한다.
Qt/다이얼로그/StandardColumns 에 의존하지 않도록 표준 컬럼명을 문자열 리터럴로 쓴다.
colorbar를 그리므로 Figure를 받는다. 다이얼로그의 픽셀 단위 여백 미세보정은 렌더러가 필요하므로
여기서는 렌더러-독립 margins 만 적용하고, 그 보정은 다이얼로그가 이후 수행한다.
"""
import numpy as np
import pandas as pd


def _gene_ratio(df):
    if 'gene_ratio' in df.columns:
        def parse(v):
            try:
                if pd.isna(v):
                    return 0.0
                if isinstance(v, (int, float)):
                    return float(v)
                p = str(v).split('/')
                if len(p) == 2:
                    d = float(p[1])
                    return float(p[0]) / d if d > 0 else 0.0
                return 0.0
            except Exception:
                return 0.0
        return df['gene_ratio'].apply(parse)
    if 'gene_count' in df.columns:
        m = df['gene_count'].max()
        if m > 0:
            return df['gene_count'] / m
    return pd.Series(0.5, index=df.index)


def render_go_dot(fig, df, params):
    """GO/KEGG dot plot을 fig에 그린다. (plotted_df, sizes) 반환. 데이터 없으면 None.

    params: top_n, x_axis('Gene Ratio'|'Fold Enrichment'), size_mode('Gene Count'|'Gene Ratio'|
            'Fold Enrichment'), palette, color_min, color_max, xlabel_text
    """
    # 크기 정규화 표(함수 내부 — 번들 inline 자기완결)
    _SIZE_NORM = {
        "Gene Count":      (100.0, [(10, "10 genes"), (30, "30 genes"), (80, "≥80 genes")]),
        "Gene Ratio":      (0.40,  [(0.03, "0.03"),   (0.12, "0.12"),  (0.35, "≥0.35")]),
        "Fold Enrichment": (20.0,  [(2.0,  "2×"),     (5.0,  "5×"),    (15.0, "≥15×")]),
    }
    _S_MIN, _S_MAX = 50, 500

    df = df.copy() if df is not None else pd.DataFrame()
    ax = fig.add_subplot(111)
    if len(df) == 0:
        ax.text(0.5, 0.5, 'No data to display\nAdjust filters',
                ha='center', va='center', fontsize=14, transform=ax.transAxes)
        return None

    required = ['description']
    if 'fdr' in df.columns:
        required.append('fdr')
    if 'gene_count' in df.columns:
        required.append('gene_count')
    df = df.dropna(subset=required)
    if len(df) == 0:
        ax.text(0.5, 0.5, 'No valid data to display\n(NaN values removed)',
                ha='center', va='center', fontsize=14, transform=ax.transAxes)
        return None

    df['_gene_ratio'] = _gene_ratio(df)

    x_axis_type = params.get('x_axis', 'Gene Ratio')
    if x_axis_type == "Fold Enrichment" and 'fold_enrichment' in df.columns:
        df['_x_val'] = pd.to_numeric(df['fold_enrichment'], errors='coerce').fillna(0)
    else:
        df['_x_val'] = df['_gene_ratio']

    df = df.sort_values('_x_val', ascending=False).head(int(params.get('top_n', 20)))
    df = df.sort_values('_x_val', ascending=True)

    x_data = df['_x_val']
    y_labels = [str(l)[:60] + '...' if len(str(l)) > 60 else str(l)
                for l in (df['description'].to_list() if 'description' in df.columns
                          else [f"Term {i+1}" for i in range(len(df))])]
    y_data = np.arange(len(y_labels))

    if 'fdr' in df.columns:
        colors = df['fdr']
        cmap = params.get('palette', 'YlOrRd_r')
        color_label = "FDR"
        vmin = params.get('color_min', 0.0)
        vmax = params.get('color_max', 0.05)
    else:
        colors, cmap, color_label, vmin, vmax = 'steelblue', None, None, None, None

    size_mode = params.get('size_mode', 'Gene Count')
    if size_mode == "Gene Count" and 'gene_count' in df.columns:
        raw = pd.to_numeric(df['gene_count'], errors='coerce').fillna(0)
    elif size_mode == "Gene Ratio":
        raw = pd.to_numeric(df['_gene_ratio'], errors='coerce').fillna(0)
    elif size_mode == "Fold Enrichment" and 'fold_enrichment' in df.columns:
        raw = pd.to_numeric(df['fold_enrichment'], errors='coerce').fillna(0)
    else:
        raw = None

    if raw is not None and size_mode in _SIZE_NORM:
        norm_max, size_rep = _SIZE_NORM[size_mode]
        sizes = _S_MIN + np.clip(raw / norm_max, 0, 1) * (_S_MAX - _S_MIN)
    else:
        norm_max, size_rep = None, None
        sizes = pd.Series(100, index=df.index)

    scatter = ax.scatter(x_data, y_data, c=colors, s=sizes, cmap=cmap, alpha=0.7,
                         edgecolors='black', linewidth=0.5, vmin=vmin, vmax=vmax)

    # 렌더러-독립 여백 (다이얼로그는 이후 픽셀 단위로 미세보정)
    max_s = float(sizes.max() if hasattr(sizes, 'max') else sizes)
    max_r_pt = np.sqrt(max_s) / 2
    fig_w_pt = fig.get_size_inches()[0] * fig.dpi
    fig_h_pt = fig.get_size_inches()[1] * fig.dpi
    ax.margins(x=max_r_pt / (fig_w_pt * 0.55) + 0.05,
               y=max_r_pt / (fig_h_pt * 0.80) + 0.05)

    n = len(df)
    yfs = 9 if n <= 10 else 8 if n <= 20 else 7 if n <= 30 else 6
    ax.set_yticks(y_data)
    ax.set_yticklabels(y_labels, fontsize=yfs)
    ax.set_xlabel(params.get('xlabel_text') or x_axis_type, fontsize=11, fontweight='bold')
    ax.set_ylabel("GO/KEGG Terms", fontsize=11, fontweight='bold')
    ax.set_title("GO/KEGG Enrichment Dot Plot", fontsize=13, fontweight='bold')
    ax.grid(axis='x', alpha=0.3, linestyle='--')

    if cmap is not None and color_label is not None:
        cbar = fig.colorbar(scatter, ax=ax, shrink=0.5, pad=0.02, anchor=(0, 1.0))
        cbar.set_label(color_label, fontsize=10)

    if size_rep is not None and norm_max is not None:
        from matplotlib.lines import Line2D
        lfs = 8

        def _ms(val):
            s = _S_MIN + np.clip(val / norm_max, 0, 1) * (_S_MAX - _S_MIN)
            return 2.0 * np.sqrt(s / np.pi)

        max_diam = max(_ms(v) for v, _ in size_rep)
        elements = [Line2D([0], [0], marker='o', color='none', markerfacecolor='#808080',
                           markeredgecolor='#333333', markeredgewidth=0.8,
                           markersize=_ms(v), label=lbl) for v, lbl in size_rep]
        leg = ax.legend(handles=elements, title=size_mode, loc='upper left', fontsize=lfs,
                        title_fontsize=lfs, labelspacing=max_diam / lfs + 0.5,
                        handlelength=0, handletextpad=1.2, borderpad=0.9, framealpha=0.95,
                        edgecolor='#bbbbbb', fancybox=False, bbox_to_anchor=(1.02, 0.20))
        leg.get_title().set_fontweight('bold')

    try:
        fig.tight_layout(rect=(0, 0, 0.85, 1))
    except Exception:
        left = min(0.50, 0.30 + max((len(str(l)) for l in y_labels), default=0) * 0.004)
        fig.subplots_adjust(left=left, right=0.85)

    return df, sizes
