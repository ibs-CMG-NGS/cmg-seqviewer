"""중앙 figure 테마 (rcParams 프리셋) + colorblind-safe 팔레트."""
from contextlib import contextmanager
import matplotlib as mpl

# Okabe-Ito (colorblind-safe, 8색)
OKABE_ITO = ['#000000', '#E69F00', '#56B4E9', '#009E73',
             '#F0E442', '#0072B2', '#D55E00', '#CC79A7']
PALETTES = {'okabe_ito': OKABE_ITO, 'tab10': None}  # None → mpl 기본 유지

_BASE = {
    'figure.dpi': 100,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'pdf.fonttype': 42,
    'ps.fonttype': 42,
    'svg.fonttype': 'none',
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.linewidth': 0.8,
    'axes.grid': False,
    'xtick.direction': 'out',
    'ytick.direction': 'out',
    'xtick.major.size': 3.0,
    'ytick.major.size': 3.0,
    'xtick.major.width': 0.8,
    'ytick.major.width': 0.8,
    'legend.frameon': False,
    'font.size': 9,
    'axes.titlesize': 11,
    'axes.labelsize': 10,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 8,
}

THEMES = {
    'Journal (sans)': {
        **_BASE,
        'font.family': ['Arial', 'DejaVu Sans'],
    },
    'Journal (serif)': {
        **_BASE,
        'font.family': ['Times New Roman', 'DejaVu Serif'],
    },
    'Presentation': {
        **_BASE,
        'font.size': 12,
        'axes.titlesize': 15,
        'axes.labelsize': 13,
        'xtick.labelsize': 11,
        'ytick.labelsize': 11,
        'legend.fontsize': 11,
        'axes.linewidth': 1.2,
        'font.family': ['Arial', 'DejaVu Sans'],
    },
}
DEFAULT_THEME = 'Journal (sans)'

# ──────────────────────────────────────────────────────────────
# Custom 테마 지원
# ──────────────────────────────────────────────────────────────

# 사용자가 조정 가능한 파라미터와 기본값 (rcParams 키와 1:1 대응)
CUSTOM_DEFAULTS = {
    'font_size':    9,
    'title_size':   11,
    'label_size':   10,
    'tick_size':    8,
    'legend_size':  8,
    'line_width':   0.8,
    'tick_length':  3.0,
    'spine_top':    False,   # False = top spine 숨김
    'spine_right':  False,   # False = right spine 숨김
    'grid':         False,
    'font_family':  'Arial, DejaVu Sans',
}


def _build_custom_rc(params: dict) -> dict:
    """사용자 커스텀 파라미터 딕셔너리 → matplotlib rcParams 딕셔너리."""
    p = {**CUSTOM_DEFAULTS, **params}
    family = [f.strip() for f in p['font_family'].split(',') if f.strip()]
    return {
        **_BASE,
        'font.size':          float(p['font_size']),
        'axes.titlesize':     float(p['title_size']),
        'axes.labelsize':     float(p['label_size']),
        'xtick.labelsize':    float(p['tick_size']),
        'ytick.labelsize':    float(p['tick_size']),
        'legend.fontsize':    float(p['legend_size']),
        'axes.linewidth':     float(p['line_width']),
        'xtick.major.size':   float(p['tick_length']),
        'ytick.major.size':   float(p['tick_length']),
        'axes.spines.top':    bool(p['spine_top']),
        'axes.spines.right':  bool(p['spine_right']),
        'axes.grid':          bool(p['grid']),
        'font.family':        family,
    }


# Custom 테마를 기본값으로 초기화 (앱 기동 시 QSettings 로드로 덮어씀)
THEMES['Custom'] = _build_custom_rc(CUSTOM_DEFAULTS)


def update_custom_theme(params: dict):
    """커스텀 파라미터로 메모리 내 THEMES['Custom']을 갱신."""
    THEMES['Custom'] = _build_custom_rc(params)


def save_custom_params(settings, params: dict):
    """QSettings에 커스텀 파라미터 저장."""
    settings.beginGroup('figure/custom')
    for key, val in params.items():
        settings.setValue(key, val)
    settings.endGroup()


def load_custom_params(settings) -> dict:
    """QSettings에서 커스텀 파라미터 로드. 없는 키는 기본값 사용."""
    result = dict(CUSTOM_DEFAULTS)
    settings.beginGroup('figure/custom')
    for key, default in CUSTOM_DEFAULTS.items():
        raw = settings.value(key)
        if raw is None:
            continue
        # QSettings는 모든 값을 str로 반환할 수 있음 — 타입 복원
        if isinstance(default, bool):
            result[key] = str(raw).lower() in ('true', '1', 'yes')
        elif isinstance(default, float):
            try:
                result[key] = float(raw)
            except (ValueError, TypeError):
                pass
        elif isinstance(default, int):
            try:
                result[key] = int(raw)
            except (ValueError, TypeError):
                pass
        else:
            result[key] = str(raw)
    settings.endGroup()
    return result


# ──────────────────────────────────────────────────────────────
# 공용 API
# ──────────────────────────────────────────────────────────────

def list_themes() -> list:
    return list(THEMES)


def theme_params(name: str, overrides: dict = None) -> dict:
    params = dict(THEMES.get(name, THEMES[DEFAULT_THEME]))
    if overrides:
        params.update(overrides)
    return params


@contextmanager
def theme_context(name: str = DEFAULT_THEME, overrides: dict = None,
                  palette: str = 'okabe_ito'):
    """다이얼로그 그리기 블록을 감싸 전역 누수 없이 테마 적용."""
    params = theme_params(name, overrides)
    cyc = PALETTES.get(palette)
    if cyc:
        params['axes.prop_cycle'] = mpl.cycler(color=cyc)
    with mpl.rc_context(params):
        yield
