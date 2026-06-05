# Phase 1 — Code-Level Implementation Plan
### 중앙 테마 + 정확한 Export + 팔레트

**Parent**: [FIGURE_QUALITY_REPRODUCIBILITY_PLAN.md](FIGURE_QUALITY_REPRODUCIBILITY_PLAN.md)
**Status**: 📋 Planned (code-level design; not yet implemented)
**Scope**: P1만. P2(FigureSpec/프리셋/round-trip)는 별도.

---

## 0. 목표와 산출물

P1 완료 시:
- 모든 플롯이 **하나의 저널 테마**로 일관(폰트/선/tick/spine).
- 저장물이 **mm 단위 정확한 크기 + DPI + 편집 가능한 벡터(PDF/SVG)** 를 만족.
- 색은 **colorblind-safe 팔레트** 기본.
- 13개 다이얼로그의 `_save_figure` 중복이 **단일 export 유틸**로 수렴(점진).

**신규 파일 3개 + 파일럿 적용 2개:**
| 파일 | 종류 | 내용 |
|---|---|---|
| `src/utils/figure_theme.py` | 신규 | rcParams 테마 프리셋 + `theme_context()` + 팔레트 |
| `src/utils/figure_export.py` | 신규 | `save_figure()` (mm 사이징/DPI/벡터 fonttype) |
| `src/gui/widgets/figure_style_panel.py` | 신규 | 공용 스타일/내보내기 컨트롤 위젯 |
| `src/gui/gene_expression_bar_dialog.py` | 수정(파일럿) | 테마 컨텍스트 + 신규 export 적용 |
| `src/gui/go_bar_chart_dialog.py` | 수정(파일럿) | 동일 |

> `src/gui/widgets/`는 신규 디렉토리 → `__init__.py` 추가 필요.

---

## 1. `src/utils/figure_theme.py`

현재 전역 matplotlib 설정 지점이 없고(각 다이얼로그가 `matplotlib.use('QtAgg')`), 테마를 **전역 변경하면 누수**되므로 `rc_context` 기반 컨텍스트로 제공한다.

```python
"""중앙 figure 테마 (rcParams 프리셋) + colorblind-safe 팔레트."""
from contextlib import contextmanager
import matplotlib as mpl

# Okabe-Ito (colorblind-safe)
OKABE_ITO = ['#000000', '#E69F00', '#56B4E9', '#009E73',
             '#F0E442', '#0072B2', '#D55E00', '#CC79A7']
PALETTES = {'okabe_ito': OKABE_ITO, 'tab10': None}  # None → mpl 기본 유지

# 모든 테마 공통 기반
_BASE = {
    'figure.dpi': 100,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    # 편집 가능한 벡터 텍스트 (저장 시점에 살아 있어야 함 → export에서도 보강)
    'pdf.fonttype': 42,
    'ps.fonttype': 42,
    'svg.fonttype': 'none',
    # 논문 톤
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
    # 폰트 크기 체계
    'font.size': 9,
    'axes.titlesize': 11,
    'axes.labelsize': 10,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 8,
}

THEMES = {
    'Journal (sans)':  {**_BASE, 'font.family': ['Arial', 'Helvetica', 'DejaVu Sans']},
    'Journal (serif)': {**_BASE, 'font.family': ['Times New Roman', 'DejaVu Serif']},
    'Presentation':    {**_BASE, 'font.size': 12, 'axes.titlesize': 15,
                        'axes.labelsize': 13, 'xtick.labelsize': 11,
                        'ytick.labelsize': 11, 'legend.fontsize': 11,
                        'axes.linewidth': 1.2,
                        'font.family': ['Arial', 'Helvetica', 'DejaVu Sans']},
}
DEFAULT_THEME = 'Journal (sans)'

def list_themes() -> list[str]:
    return list(THEMES)

def theme_params(name: str, overrides: dict | None = None) -> dict:
    params = dict(THEMES.get(name, THEMES[DEFAULT_THEME]))
    if overrides:
        params.update(overrides)
    return params

@contextmanager
def theme_context(name: str = DEFAULT_THEME, overrides: dict | None = None,
                  palette: str | None = 'okabe_ito'):
    """다이얼로그의 그리기 블록을 감싸 전역 누수 없이 테마 적용."""
    params = theme_params(name, overrides)
    cyc = PALETTES.get(palette)
    if cyc:
        params['axes.prop_cycle'] = mpl.cycler(color=cyc)
    with mpl.rc_context(params):
        yield
```

**주의**
- `font.family`에 시스템 의존(Arial). 없으면 자동으로 다음 후보(DejaVu Sans, 항상 존재)로 폴백 → 깨지지 않음. (Arial 번들은 라이선스 이슈 → §6 참조)
- `theme_context`는 **그리기 시점**에 감싸야 한다. `Figure`/`Axes` 생성과 모든 `plot/bar/scatter/set_*` 호출이 컨텍스트 안에 있어야 rcParams가 반영됨.

---

## 2. `src/utils/figure_export.py`

다이얼로그별 `_save_figure`(예: `go_bar_chart_dialog.py`, `gene_expression_bar_dialog.py`)의 중복을 대체.

```python
"""중앙 figure export — mm 단위 사이징, DPI, 편집 가능한 벡터."""
from pathlib import Path
import matplotlib as mpl

MM_PER_INCH = 25.4
JOURNAL_WIDTH_MM = {'single': 85.0, 'one-half': 114.0, 'double': 170.0}
VECTOR = {'pdf', 'svg', 'eps'}
RASTER = {'png', 'tiff', 'tif', 'jpg', 'jpeg'}

def save_figure(fig, path: str | Path, fmt: str | None = None,
                dpi: int = 300, size_mm: tuple[float, float] | None = None,
                transparent: bool = False) -> Path:
    path = Path(path)
    fmt = (fmt or path.suffix.lstrip('.') or 'png').lower()
    if not path.suffix:
        path = path.with_suffix('.' + fmt)

    supported = fig.canvas.get_supported_filetypes()
    if fmt not in supported:
        raise ValueError(f"Unsupported format '{fmt}'. "
                         f"Supported: {', '.join(sorted(supported))}")

    if size_mm:
        fig.set_size_inches(size_mm[0] / MM_PER_INCH, size_mm[1] / MM_PER_INCH)

    # 편집 가능한 벡터 텍스트를 저장 시점에 보장(테마 밖에서 호출돼도 안전)
    save_rc = {'pdf.fonttype': 42, 'ps.fonttype': 42, 'svg.fonttype': 'none'}
    kwargs = dict(bbox_inches='tight', transparent=transparent)
    if fmt in RASTER:
        kwargs['dpi'] = dpi
    with mpl.rc_context(save_rc):
        fig.savefig(path, format=fmt, **kwargs)
    return path
```

**주의**
- 벡터 fonttype은 테마(§1)에도 있지만, export가 테마 컨텍스트 **밖**에서 호출될 수 있어 여기서 한 번 더 보장.
- `set_size_inches`는 figure를 영구 변경 → 저장 후 화면 표시 크기가 바뀔 수 있음. 필요시 저장 전 크기를 백업·복원하거나, 저장 전용 figure에 그리는 방식 고려(파일럿에서는 단순 변경 허용).
- EPS는 투명도 미지원 → `transparent=True` + eps 조합 경고/무시 처리.

---

## 3. `src/gui/widgets/figure_style_panel.py`

기존 다이얼로그 좌측 패널에 끼울 수 있는 **공용 컨트롤**. 파일럿에서는 "테마 + 크기(mm)/DPI/포맷"만 우선 노출(축/폰트 세부는 후속).

```python
from PyQt6.QtWidgets import (QWidget, QFormLayout, QComboBox, QDoubleSpinBox,
                             QSpinBox, QHBoxLayout, QLabel)
from PyQt6.QtCore import pyqtSignal
from utils import figure_theme

class FigureStylePanel(QWidget):
    """테마/사이징/내보내기 공용 컨트롤. 값 변경 시 changed 방출."""
    changed = pyqtSignal()  # 테마 등 '다시 그려야' 하는 변경

    def __init__(self, parent=None):
        super().__init__(parent)
        form = QFormLayout(self)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(figure_theme.list_themes())
        self.theme_combo.currentTextChanged.connect(lambda _: self.changed.emit())
        form.addRow("Theme:", self.theme_combo)

        # journal 폭 프리셋 + mm 직접 입력
        self.width_mm = QDoubleSpinBox(); self.width_mm.setRange(30, 400); self.width_mm.setValue(85)
        self.height_mm = QDoubleSpinBox(); self.height_mm.setRange(30, 400); self.height_mm.setValue(70)
        size_row = QHBoxLayout()
        for w in (QLabel("W"), self.width_mm, QLabel("H"), self.height_mm):
            size_row.addWidget(w)
        form.addRow("Size (mm):", size_row)

        self.dpi_combo = QComboBox(); self.dpi_combo.addItems(["300", "600", "150"])
        form.addRow("DPI (raster):", self.dpi_combo)
        self.fmt_combo = QComboBox(); self.fmt_combo.addItems(["pdf", "svg", "png", "tiff", "eps"])
        form.addRow("Format:", self.fmt_combo)

    def theme_name(self) -> str: return self.theme_combo.currentText()
    def size_mm(self) -> tuple[float, float]:
        return (self.width_mm.value(), self.height_mm.value())
    def export_opts(self) -> dict:
        return {"fmt": self.fmt_combo.currentText(), "dpi": int(self.dpi_combo.currentText()),
                "size_mm": self.size_mm()}
```

`src/gui/widgets/__init__.py` (빈 파일) 추가.

---

## 4. 파일럿 다이얼로그 통합 (2개)

### 4-1. `gene_expression_bar_dialog.py`
1. **import**: `from utils import figure_theme, figure_export`.
2. **테마 상태**: `__init__`에서 `self._style = FigureStylePanel()` 를 좌측 패널에 추가, `self._style.changed.connect(self._update_plot)`.
3. **그리기 컨텍스트**: `_update_plot()`의 본문 전체를
   ```python
   with figure_theme.theme_context(self._style.theme_name()):
       ... (기존 figure.clear() ~ canvas.draw())
   ```
   로 감싼다. (현재 색 지정은 `group_colors`가 명시색이라 팔레트와 충돌 안 함; 명시색 우선.)
4. **export 교체**: 기존 `_save_figure`의 본문을
   ```python
   opts = self._style.export_opts()
   path, _ = QFileDialog.getSaveFileName(self, "Save Figure",
       f"gene_expression_bar_{self.dataset.name}.{opts['fmt']}", _filters())
   if not path: return
   try:
       figure_export.save_figure(self.figure, path, **opts)
       QMessageBox.information(...)
   except ValueError as e: QMessageBox.warning(...)
   ```
   기존 `width_spin/height_spin`(inch)·`_on_figure_size_changed`는 **유지하되**, 저장 크기는 `size_mm` 우선(혹은 inch 컨트롤 제거하고 mm로 일원화 — 파일럿에서 결정).

### 4-2. `go_bar_chart_dialog.py`
동일 패턴. 기존 `_save_figure`(L333~)와 `width_spin/height_spin`(inch) 대체.

> **점진 원칙**: 두 파일럿만 먼저. 검증 후 나머지 11개(volcano/heatmap/pca/MA/quadrant/integrated_volcano/concordance/go_dot/go_comparison_dot/go_network/multi_group_heatmap)로 확산.

---

## 5. 설정 영속화 (QSettings)

앱은 이미 `QSettings("RNASeqDataView", "MainWindow")`([main_window.py:68](../../src/gui/main_window.py#L68)) 사용. P1 기본값을 같은 store에 저장:

| 키 | 값 | 기본 |
|---|---|---|
| `figure/theme` | 테마명 | `Journal (sans)` |
| `figure/dpi` | int | 300 |
| `figure/format` | str | `pdf` |
| `figure/size_preset` | single/one-half/double/custom | single |

`FigureStylePanel`이 생성 시 QSettings에서 읽고, 변경 시 저장(선택). 파일럿에서는 우선 메모리 기본값만, 영속화는 옵션.

---

## 6. 폰트 / PyInstaller 주의

- **Arial 번들 금지**(라이선스). 대신 `font.family=['Arial','Helvetica','DejaVu Sans']` 순서 → 사용자 시스템에 Arial 있으면 사용, 없으면 DejaVu Sans(matplotlib 내장, 항상 존재).
- **편집 가능한 벡터**: 텍스트를 outline 안 하므로(`svg.fonttype='none'`, `pdf.fonttype=42`) 다운스트림 편집기에 해당 폰트가 있어야 동일하게 보임. 없으면 대체 폰트로 렌더(내용은 유지·편집 가능).
- PyInstaller spec(`rna-seq-viewer.spec`, `cmg-seqviewer-macos.spec`)에 **추가 hiddenimports 불필요**(matplotlib만 사용). 폰트 번들을 택하면 `datas`에 TTF 추가 + `font_manager.fontManager.addfont()` 호출 필요.

---

## 7. 검증 (headless 우선)

1. **테마 적용 단위테스트**
   ```python
   import matplotlib as mpl
   from utils.figure_theme import theme_context
   with theme_context('Journal (sans)'):
       assert mpl.rcParams['axes.spines.top'] is False
       assert mpl.rcParams['svg.fonttype'] == 'none'
   ```
2. **export 회귀(headless)**: `QT_QPA_PLATFORM=offscreen`로 파일럿 다이얼로그 생성 → `save_figure(fig, tmp.pdf/svg/png, size_mm=(85,70))`:
   - 파일 생성 확인.
   - **SVG 편집가능성**: 저장된 SVG에 `<text` 요소가 존재(=경로로 outline 안 됨) + `font-family` 속성 확인.
   - **PNG 크기**: 85mm×300dpi ≈ 1004px 폭(±오차) 확인.
3. **수동(최종)**: 내보낸 PDF/SVG를 Illustrator/Inkscape에서 열어 **텍스트 선택·편집 가능** + 크기 정확 확인.

---

## 8. 작업 체크리스트 (순서/노력)

| # | 작업 | 파일 | 노력 |
|---|---|---|---|
| 1 | `figure_theme.py` 작성 | 신규 | S |
| 2 | `figure_export.py` 작성 | 신규 | S |
| 3 | `widgets/__init__.py` + `figure_style_panel.py` | 신규 | M |
| 4 | gene_expression_bar 파일럿 통합 | 수정 | M |
| 5 | go_bar_chart 파일럿 통합 | 수정 | S |
| 6 | headless 검증 스크립트(테마/export) | test | S |
| 7 | (옵션) QSettings 영속화 | 수정 | S |
| 8 | 수동 벡터 편집 확인 → 나머지 11개 확산 계획 | — | — |

권장 순서: **1 → 2 → 6(부분) → 3 → 4 → 5 → 6(완) → 7**. 즉 테마/export를 먼저 만들고 헤드리스로 검증한 뒤 UI 위젯·파일럿을 붙인다.

## 9. 리스크 / 결정 필요
- **inch vs mm 컨트롤 일원화**: 기존 inch SpinBox를 제거하고 mm로 통일할지, 둘 다 둘지(파일럿에서 결정).
- **저장 시 figure 크기 영구 변경**: 화면 표시 크기 변동 허용 여부(허용 권장, 단순).
- **테마 누수**: 반드시 `rc_context`만 사용, 전역 `rcParams` 직접 수정 금지.
- **명시색 vs 팔레트**: group_colors 등 명시색은 팔레트보다 우선(현 동작 유지).
