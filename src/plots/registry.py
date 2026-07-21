"""플롯 렌더 레지스트리 — plot_type 하나로 어떤 플롯이든 다시 그릴 수 있게 한다.

각 항목: plot_type -> (모듈명, 렌더 함수명, target, from_dataset)
  target      : 'fig' = render(fig, df, params) / 'ax' = render(ax, df, params)
  from_dataset: True 면 그 플롯의 df 가 '데이터셋 테이블 그 자체'라 프로젝트 복원 시
                부모 데이터셋에서 다시 만들 수 있다. False 면 df 가 별도로 가공된
                표(멤버십·long-format·비교 결과 등)라 부모 데이터셋만으로는 복원 불가.

Pin to Tab(범용 스냅샷 탭)과 프로젝트 복원이 이 레지스트리를 공유한다.
"""

_REGISTRY = {
    # plot_type:              (module,                 function,                      target, from_dataset)
    'volcano':                ('volcano',              'render_volcano',              'ax',  True),
    'heatmap':                ('heatmap',              'render_heatmap',              'fig', True),
    'ma':                     ('ma',                   'render_ma',                   'ax',  True),
    'pca':                    ('pca',                  'render_pca',                  'fig', True),
    'go_dot':                 ('go_dot',               'render_go_dot',               'fig', True),
    'go_bar':                 ('go_bar',               'render_go_bar',               'ax',  True),
    'genomic_distribution':   ('genomic_distribution', 'render_genomic_distribution', 'fig', True),
    'gene_expression_bar':    ('gene_expression_bar',  'render_gene_expression_bar',  'ax',  True),
    'quadrant':               ('quadrant',             'render_quadrant',             'ax',  True),
    'integrated_volcano':     ('integrated_volcano',   'render_integrated_volcano',   'ax',  True),
    # 아래는 df 가 가공된 표 — 화면 pin 은 되지만 프로젝트 복원은 부모만으로 불가
    'go_comparison_dot':      ('go_comparison_dot',    'render_go_comparison_dot',    'fig', False),
    'go_cluster_dot':         ('go_cluster_dot',       'render_go_cluster_dot',       'fig', False),
    'meta_volcano':           ('meta_volcano',         'render_meta_volcano',         'ax',  False),
    'count_summary':          ('count_summary',        'render_count_summary',        'ax',  False),
    'annotation_comparison':  ('annotation_comparison', 'render_annotation_comparison', 'ax', False),
    'venn':                   ('venn',                 'render_venn',                 'ax',  False),
    'upset':                  ('upset',                'render_upset',                'fig', False),
}


def get_entry(plot_type):
    """(render_fn, target, from_dataset) 반환. 미등록이면 (None, None, False)."""
    entry = _REGISTRY.get((plot_type or '').lower())
    if not entry:
        return None, None, False
    mod_name, func_name, target, from_dataset = entry
    import importlib
    try:
        mod = importlib.import_module(f'plots.{mod_name}')
    except Exception:
        return None, None, False
    return getattr(mod, func_name, None), target, from_dataset


def is_supported(plot_type) -> bool:
    return (plot_type or '').lower() in _REGISTRY


def restorable_from_dataset(plot_type) -> bool:
    """프로젝트 복원 시 부모 데이터셋 테이블만으로 다시 그릴 수 있는 플롯인가."""
    entry = _REGISTRY.get((plot_type or '').lower())
    return bool(entry and entry[3])


def render_to_figure(fig, plot_type, df, params) -> bool:
    """등록된 렌더를 fig 에 그린다. 미등록/실패면 False."""
    fn, target, _ = get_entry(plot_type)
    if fn is None:
        return False
    if target == 'fig':
        fn(fig, df, params or {})
    else:
        ax = fig.add_subplot(111)
        fn(ax, df, params or {})
    return True


def supported_plot_types():
    return sorted(_REGISTRY)
