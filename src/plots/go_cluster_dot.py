"""GO cluster summary dot plot — pure renderer (dialog + bundle 공유).

render_go_cluster_dot(fig, df, params) 는 GONetworkDialog._do_dotplot 과 재현 번들이 공유한다.
입력 df 는 '클러스터당 대표 term' 표(rep_df): 각 행이 유효 클러스터의 대표 GO term이며
컬럼에 cluster_id, description, fdr, gene_ratio, fold_enrichment, gene_count, ontology,
direction, _cluster_size(클러스터 멤버 수)를 포함한다. 대표 term 선정·클러스터 크기 계산은
다이얼로그가 수행하고, 여기서는 정렬·top N·scatter·colorbar·범례만 담당한다. Qt 비의존.
"""
import numpy as np
import pandas as pd


def render_go_cluster_dot(fig, df, params):
    """rep_df 로부터 cluster dot plot 을 fig 에 그린다. 그린 df(정렬·top N 적용) 반환.

    params: x_axis('-log10(FDR)'|'Gene Ratio'|'Fold Enrichment'),
            color_by('FDR'|'Ontology'|'Direction'),
            size_by('Cluster size'|'Gene count'),
            sort_by('FDR'|'Cluster Size'|'Term Name'), top_n,
            dot_size_min, dot_size_scale, cmap, z_min, z_max, z_auto,
            colorbar_loc, colorbar_shrink, show_size_legend,
            x_min, x_max, y_min, y_max, title
    """
    import matplotlib
    import matplotlib.colors as mcolors
    from matplotlib import cm
    from matplotlib.patches import Patch

    C_CLUSTER, C_FDR, C_RATIO, C_FE = 'cluster_id', 'fdr', 'gene_ratio', 'fold_enrichment'
    C_COUNT, C_DESC, C_ONT, C_DIR = 'gene_count', 'description', 'ontology', 'direction'

    ax = fig.add_subplot(111)
    df = df.copy() if df is not None else pd.DataFrame()
    if df.empty:
        ax.text(0.5, 0.5, 'No clustered data available', ha='center', va='center',
                fontsize=13, transform=ax.transAxes)
        ax.axis('off')
        return None
    if '_cluster_size' not in df.columns:
        df['_cluster_size'] = 1

    # ── 정렬 ──
    sort_by = params.get('sort_by', 'FDR')
    if sort_by == 'FDR' and C_FDR in df.columns:
        df = df.sort_values(C_FDR, ascending=False)
    elif sort_by == 'Cluster Size':
        df = df.sort_values('_cluster_size', ascending=True)
    elif sort_by == 'Term Name' and C_DESC in df.columns:
        df = df.sort_values(C_DESC, ascending=False)

    # ── Top N (무엇을 남길지: FDR=가장 유의 / Fold Enrichment=가장 강한 enrichment) ──
    top_n = int(params.get('top_n', 20))
    top_n_by = params.get('top_n_by', 'FDR')
    if len(df) > top_n:
        if top_n_by == 'Fold Enrichment' and C_FE in df.columns:
            keep = pd.to_numeric(df[C_FE], errors='coerce').fillna(
                float('-inf')).nlargest(top_n).index
        elif C_FDR in df.columns:
            keep = df.nsmallest(top_n, C_FDR).index
        else:
            keep = df.index[:top_n]
        df = df.loc[df.index.isin(keep)]
    n_terms = len(df)

    # ── Y 라벨 ("C001: term" — 다중-term 클러스터만 접두, singleton 은 term 명만) ──
    cluster_ids = df[C_CLUSTER].tolist() if C_CLUSTER in df.columns else list(range(n_terms))

    def _cid_prefix(cid):
        return f"C{cid}: " if str(cid).isdigit() else ""
    if C_DESC in df.columns:
        y_labels = [f"{_cid_prefix(cid)}{str(v)[:60]}"
                    for cid, v in zip(cluster_ids, df[C_DESC])]
    else:
        y_labels = [f"C{cid}" if str(cid).isdigit() else str(cid) for cid in cluster_ids]

    # ── X 값 ──
    x_axis = params.get('x_axis', 'Fold Enrichment')
    if x_axis == '-log10(FDR)' and C_FDR in df.columns:
        x_vals = [-np.log10(max(float(v), 1e-300)) for v in df[C_FDR]]
        x_label = '-log10(FDR)'
    elif x_axis == 'Gene Ratio' and C_RATIO in df.columns:
        x_vals = []
        for v in df[C_RATIO]:
            try:
                if '/' in str(v):
                    a, b = str(v).split('/'); x_vals.append(float(a) / float(b))
                else:
                    x_vals.append(float(v))
            except Exception:
                x_vals.append(0.0)
        x_label = 'Gene Ratio'
    elif x_axis == 'Fold Enrichment' and C_FE in df.columns:
        x_vals = [float(v) if pd.notna(v) else 0.0 for v in df[C_FE]]
        x_label = 'Fold Enrichment'
    elif C_FDR in df.columns:
        x_vals = [-np.log10(max(float(v), 1e-300)) for v in df[C_FDR]]
        x_label = '-log10(FDR)'
    else:
        x_vals = list(range(n_terms)); x_label = 'Index'

    # ── 색 ──
    color_by = params.get('color_by', 'Fold Enrichment')
    legend_handles = []
    scatter_cmap = scatter_norm = None
    color_label = 'FDR'
    if color_by in ('Fold Enrichment', 'Fold Enrichment (median)') and (
            C_FE in df.columns or '_fe_median' in df.columns):
        # 효과 크기(강도)로 색칠 — 유의성 필터를 이미 거친 데이터에선 FDR보다 정보 효율이 높다.
        fe_col = ('_fe_median' if color_by == 'Fold Enrichment (median)'
                  and '_fe_median' in df.columns else C_FE)
        fe_vals = pd.to_numeric(df[fe_col], errors='coerce').fillna(0.0).tolist() \
            if fe_col in df.columns else []
        if fe_vals:
            if params.get('z_auto', True):
                vmin = min(fe_vals)
                vmax = max(fe_vals)
            else:
                vmin = float(params.get('z_min', 0.0))
                vmax = float(params.get('z_max', 1.0))
            if vmax <= vmin:
                vmax = vmin + 1.0
            scatter_norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
            cmap_name = params.get('cmap', 'YlOrRd_r')
            # 높은 fold enrichment = 진한 색이 되도록 역방향(_r) 팔레트는 정방향으로 바꾼다.
            if cmap_name.endswith('_r'):
                cmap_name = cmap_name[:-2]
            scatter_cmap = cmap_name
            dot_colors = fe_vals
            color_label = ('Fold Enrichment (cluster median)'
                           if fe_col == '_fe_median' else 'Fold Enrichment')
        else:
            dot_colors = '#3498db'
    elif color_by == 'FDR' and C_FDR in df.columns:
        fdr_vals = [float(v) for v in df[C_FDR]]
        if params.get('z_auto', True):
            vmin = max(min(fdr_vals), 1e-300) if fdr_vals else 1e-300
            vmax = max(max(fdr_vals, default=1.0), vmin * 10)
        else:
            vmin = max(float(params.get('z_min', 1e-10)), 1e-300)
            vmax = float(params.get('z_max', 0.05))
            if vmax <= vmin:
                vmax = vmin * 10
        scatter_norm = mcolors.LogNorm(vmin=vmin, vmax=vmax)
        scatter_cmap = params.get('cmap', 'viridis_r')
        dot_colors = fdr_vals
        # 클러스터 FDR = 대표(클러스터 내 최소 FDR) term 값임을 명시 (집계값 아님).
        color_label = 'FDR (representative term)'
    elif color_by == 'Ontology' and C_ONT in df.columns:
        onts = df[C_ONT].tolist()
        uniq = list(dict.fromkeys(onts))
        cmap_ont = cm.tab10
        ont_map = {o: cmap_ont(i / max(len(uniq), 1)) for i, o in enumerate(uniq)}
        dot_colors = [ont_map.get(str(o), '#aaa') for o in onts]
        legend_handles = [Patch(color=ont_map[o], label=o) for o in uniq]
    elif color_by == 'Direction' and C_DIR in df.columns:
        dir_c = {'UP': '#e74c3c', 'DOWN': '#3498db', 'TOTAL': '#95a5a6'}
        dot_colors = [dir_c.get(str(d), '#95a5a6') for d in df[C_DIR]]
        seen = list(dict.fromkeys(df[C_DIR].tolist()))
        legend_handles = [Patch(color=dir_c.get(str(d), '#aaa'), label=str(d)) for d in seen]
    else:
        dot_colors = '#3498db'

    # ── 크기 (size_by: 클러스터 멤버 수 or 대표 term 유전자 수) ──
    size_by = params.get('size_by', 'Cluster size')
    dot_min = float(params.get('dot_size_min', 40.0))
    dot_scale = float(params.get('dot_size_scale', 20.0))
    if size_by == 'Gene count' and C_COUNT in df.columns:
        size_src = pd.to_numeric(df[C_COUNT], errors='coerce').fillna(1)
        size_legend_title = 'Genes'
    else:
        size_src = df['_cluster_size']
        size_legend_title = 'Members'
        size_by = 'Cluster size'
    dot_sizes = [max(dot_min, float(s) * dot_scale) for s in size_src]

    y_pos = list(range(n_terms))
    sc = ax.scatter(x_vals, y_pos, s=dot_sizes, c=dot_colors,
                    cmap=scatter_cmap, norm=scatter_norm, alpha=0.85,
                    edgecolors='black', linewidths=0.8, zorder=3)

    if scatter_cmap is not None and scatter_norm is not None:
        cbar = fig.colorbar(sc, ax=ax, location=params.get('colorbar_loc', 'right'),
                            shrink=float(params.get('colorbar_shrink', 0.6)), pad=0.02)
        cbar.set_label(color_label)

    # ── 크기 범례 ──
    if params.get('show_size_legend', True):
        max_v = int(size_src.max()) if len(size_src) else 1
        if max_v <= 4:
            counts = list(range(1, max_v + 1))
        else:
            counts = sorted(set([1] + [int(round(v)) for v in np.linspace(max_v / 3, max_v, 3)]))
        size_handles = [ax.scatter([], [], s=max(dot_min, cnt * dot_scale), c='#aaaaaa',
                                   alpha=0.7, edgecolors='black', linewidths=0.8, label=f'{cnt}')
                        for cnt in counts]
    else:
        size_handles = []

    if legend_handles:
        color_leg = ax.legend(handles=legend_handles, loc='lower right',
                              title=color_by, framealpha=0.9)
        ax.add_artist(color_leg)
    if size_handles:
        ax.legend(handles=size_handles, title=size_legend_title, loc='upper right',
                  framealpha=0.9, handletextpad=1.2, labelspacing=1.0)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(y_labels)
    ax.set_xlabel(x_label)
    size_txt = 'gene count' if size_by == 'Gene count' else 'cluster member count'
    ax.set_title(params.get('title') or
                 f"GO Cluster Summary Dot Plot\nTop {n_terms} clusters  ·  dot size = {size_txt}",
                 fontweight='bold')
    ax.grid(axis='x', alpha=0.3, linestyle='--')
    ax.axvline(x=0, color='gray', linewidth=0.6)

    x_min, x_max = params.get('x_min'), params.get('x_max')
    if x_min is not None and x_max is not None:
        ax.set_xlim(float(x_min), float(x_max))
    y_min, y_max = params.get('y_min'), params.get('y_max')
    if y_min is not None and y_max is not None:
        ax.set_ylim(float(y_min) - 0.5, float(y_max) + 0.5)

    fig.tight_layout()
    return df
