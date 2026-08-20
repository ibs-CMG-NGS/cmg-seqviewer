"""GO/KEGG enrichment bar chart — pure renderer (dialog + bundle 공유).

render_go_bar(ax, df, params) 는 GOBarChartDialog._do_plot 과 재현 번들 스크립트가 공유한다.
Qt/StandardColumns 에 의존하지 않도록 표준 컬럼명을 문자열 리터럴로 쓴다.
"""
import numpy as np
import pandas as pd


def select_go_bar_rows(df, params):
    """bar chart에 그려질(=export 되어야 할) 행만 골라 정렬까지 적용해 반환.

    render_go_bar 와 GOBarChartDialog._export_data 가 이 함수를 공유한다 — 예전엔
    export 쪽이 이 로직(dropna/sort/top_n)을 별도로 복제해서, 둘 중 하나만 고치면
    그림과 export 가 어긋날 수 있었다. 데이터가 없으면 빈 DataFrame 반환(호출부가
    '데이터 없음' 처리는 각자 알아서 함).
    """
    df = df.copy() if df is not None else pd.DataFrame()
    if len(df) == 0:
        return df

    required = ['description']
    if 'fdr' in df.columns:
        required.append('fdr')
    if 'gene_count' in df.columns:
        required.append('gene_count')
    df = df.dropna(subset=required)
    if len(df) == 0:
        return df

    sort_by = params.get('sort_by', 'FDR (ascending)')
    if sort_by == "FDR (ascending)" and 'fdr' in df.columns:
        df = df.sort_values('fdr', ascending=True)
    elif sort_by == "Gene Count (descending)" and 'gene_count' in df.columns:
        df = df.sort_values('gene_count', ascending=False)
    elif sort_by == "Alphabetical" and 'description' in df.columns:
        df = df.sort_values('description', ascending=True)

    return df.head(int(params.get('top_n', 15)))


def render_go_bar(ax, df, params):
    """GO/KEGG bar chart를 ax에 그린다. 데이터 없으면 None 반환.

    params: top_n, x_axis('-log10(FDR)'|'Gene Ratio'|'Fold Enrichment'),
            sort_by('FDR (ascending)'|'Gene Count (descending)'|'Alphabetical'),
            bar_color(hex), horizontal(bool), xlabel_text
    """
    input_empty = df is None or len(df) == 0
    df = select_go_bar_rows(df, params)
    if len(df) == 0:
        msg = ('No data to display\nAdjust filters' if input_empty
               else 'No valid data to display\n(NaN values removed)')
        ax.text(0.5, 0.5, msg, ha='center', va='center', transform=ax.transAxes)
        return None

    x_axis_type = params.get('x_axis', '-log10(FDR)')
    if x_axis_type == "-log10(FDR)":
        x_data = (-np.log10(pd.to_numeric(df['fdr'], errors='coerce').replace(0, 1e-300))
                  if 'fdr' in df.columns else pd.Series(1, index=df.index))
    elif x_axis_type == "Gene Ratio":
        if 'gene_ratio' in df.columns:
            def _parse(r):
                try:
                    if pd.isna(r):
                        return 0.0
                    if isinstance(r, (int, float)):
                        return float(r)
                    p = str(r).split('/')
                    return float(p[0]) / float(p[1]) if len(p) == 2 and float(p[1]) > 0 else 0.0
                except Exception:
                    return 0.0
            x_data = df['gene_ratio'].apply(_parse)
        else:
            x_data = pd.Series(1, index=df.index)
    else:  # Fold Enrichment
        x_data = (pd.to_numeric(df['fold_enrichment'], errors='coerce').fillna(0)
                  if 'fold_enrichment' in df.columns else pd.Series(1, index=df.index))

    y_labels = [str(l)[:70] + '...' if len(str(l)) > 70 else str(l)
                for l in (df['description'].to_list() if 'description' in df.columns
                          else [f"Term {i+1}" for i in range(len(df))])]
    y_pos = np.arange(len(y_labels))
    bar_color = params.get('bar_color', '#4C72B0')
    horizontal = bool(params.get('horizontal', True))
    xlabel_text = params.get('xlabel_text') or x_axis_type
    ylabel_text = "GO/KEGG Terms"

    if horizontal:
        ax.barh(y_pos, x_data, color=bar_color, edgecolor='black', linewidth=0.5)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(y_labels)
        ax.set_xlabel(xlabel_text, fontweight='bold')
        ax.set_ylabel(ylabel_text, fontweight='bold')
        ax.invert_yaxis()
        ax.grid(axis='x', alpha=0.3, linestyle='--')
    else:
        ax.bar(y_pos, x_data, color=bar_color, edgecolor='black', linewidth=0.5)
        ax.set_xticks(y_pos)
        ax.set_xticklabels(y_labels, rotation=45, ha='right')
        ax.set_ylabel(xlabel_text, fontweight='bold')
        ax.set_xlabel(ylabel_text, fontweight='bold')
        ax.grid(axis='y', alpha=0.3, linestyle='--')

    ax.set_title("GO/KEGG Enrichment Bar Chart", fontweight='bold')
    return df
