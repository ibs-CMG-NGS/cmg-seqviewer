# CMG-SeqViewer — Publication-Quality Figure & Reproducibility Plan

**Status**: 📋 Planned (not started)
**Author**: design note
**Scope**: figure 품질(논문/발표용) 세밀 제어 + 그리는 과정의 재현성·재사용성
**목적**: 지금 당장 구현하지 않더라도, 이 문서만 보면 언제든 착수할 수 있는 포괄적 설계도

---

## Context (왜 필요한가)

cmg-seqviewer의 핵심 기능이 거의 완성됐고, 다음 단계는 **figure 품질(논문/발표용)** 과 **그리는 과정의 재현성·재사용성**이다. 논문/발표 준비 시 같은 figure를 조건만 바꿔 여러 번 다시 그리는 비용이 크다. Prism/OriginPro/GraphPad 급의 세밀 제어를 *전부* 복제하는 것은 다년 작업이므로, **체감 가치의 80%를 주는 20%** 에 집중한다.

### 핵심 설계 원칙 (모든 Phase의 전제)
> **Figure = 직렬화 가능한 `FigureSpec`(데이터 참조 + 스타일) + 순수 렌더러(spec → matplotlib Figure)**

Prism/Origin 내부도 "프로젝트 = 데이터 + 스타일 상태"다. spec을 도입하면 디테일 설정·테마·재현성·재사용이 한 뿌리에서 파생된다. 이 결정이 가장 중요하다.

### 현재 코드의 토대 (재사용 자산)
| 자산 | 위치 | 역할 |
|---|---|---|
| `ProjectIO` 프로젝트 spec | `src/utils/project_io.py` (`_build_spec`, `plot_type`/`plot_params` 직렬화 ~L146–178) | figure spec 재현성의 출발점 |
| Plot Settings Dock | `src/gui/main_window.py` (`plot_settings_dock` L244, `_update_plot_settings_dock` L2350, `_pin_plot_to_tab` L2295) | 스타일 패널이 이미 다이얼로그와 분리됨 |
| 다이얼로그별 export | 예: `src/gui/go_bar_chart_dialog.py::_save_figure` (PNG/PDF/SVG/TIFF, 300dpi) | 중앙 export로 통합 대상 |
| 유의성/주석·그룹색 | `src/gui/gene_expression_bar_dialog.py` (`_p_to_stars`, group_colors) | 주석 레이어로 일반화 대상 |
| 13개 plot 다이얼로그 | `src/gui/*_dialog.py` (volcano/heatmap/pca/MA/quadrant/integrated_volcano/concordance/go_*/gene_expression_bar 등) | 공용 테마·export·spec 적용 대상 |

### 솔직한 제약 (먼저 합의)
- matplotlib은 **요소 드래그 WYSIWYG, axis break** 등이 매우 어렵다 → 약속하지 않는다. 강점은 "선언적 spec + 자동 재생성".
- **리팩토링 비용**: 13개 다이얼로그가 컨트롤·export를 중복 구현 → 공용화가 선결. 다이얼로그가 늘수록 중복이 폭발하므로 지금이 적기.
- Prism 완전 복제는 비목표. 테마 + 정확한 벡터 export + 유의성 + 멀티패널 + spec 재현성에 집중.

---

## 우선순위 요약 (난이도 / 효과)

| Phase | 주제 | 난이도 | 효과 | 권장 우선순위 |
|---|---|---|---|---|
| **P1** | 중앙 테마 + 정확한 export(단위/DPI/편집가능 벡터) + 팔레트 | 낮음 | 매우 큼 | **즉시** |
| **P2** | `FigureSpec` 직렬화 + 스타일 프리셋(저장/적용/전체적용) + export에 spec 임베드(round-trip) | 중간 | 큼 | 높음 |
| **P3** | 유의성/주석 레이어 일반화 + 멀티패널 합성(A/B/C) + 배치 export | 중간 | 큼 | 중간 |
| **P4** | export-to-script + provenance 메타데이터 + 템플릿 갤러리 | 중상 | 중(신뢰·재현 가치) | 선택 |

각 Phase는 독립적으로 가치가 있어 **순서대로 멈춰도 됨**(P1만 해도 전체 figure 품질이 올라감).

---

## Phase 1 — 중앙 테마 + 정확한 Export (즉시, 가성비 최고)

**목표:** 모든 플롯이 한 번에 논문 톤으로 일관되고, 저장물이 저널 규격(크기/DPI/편집가능 벡터)을 만족.

### 필요한 작업
1. **중앙 테마 모듈** `src/utils/figure_theme.py` (신규)
   - matplotlib `rcParams` 기반 "저널 테마" 1개 이상 정의: 폰트(Arial/Helvetica), 글자 크기 체계(title/axis/tick/legend), 선 굵기, **tick 방향=out·길이**, **top/right spine 제거**, 기본 DPI, 기본 팔레트.
   - `apply_theme(name)` 컨텍스트로 적용. `plt.style.use` 또는 `mpl.rc_context` 사용.
   - colorblind-safe 팔레트(Okabe-Ito, viridis) 내장 + 사용자 팔레트 등록 훅.
2. **중앙 export 유틸** `src/utils/figure_export.py` (신규)
   - 13개 다이얼로그의 `_save_figure` 중복을 대체하는 단일 함수: `save_figure(fig, path, fmt, dpi, size_mm)`.
   - **실제 단위 사이징**: 폭/높이 mm 입력(저널 1단 ~85mm, 2단 ~170mm) → inch 변환 후 `fig.set_size_inches`.
   - **편집 가능한 벡터**: 저장 시 `rcParams['pdf.fonttype']=42`, `rcParams['svg.fonttype']='none'` (폰트 outline 금지, 텍스트 편집 가능). EPS 옵션도.
   - 래스터는 dpi 300/600 선택, `bbox_inches='tight'`.
3. **공용 컨트롤 위젯** `src/gui/widgets/figure_style_panel.py` (신규)
   - 테마 선택, 폰트/크기, 축 라벨/범위/tick, figure 크기(mm), DPI/포맷을 한 곳에서 편집하는 재사용 위젯. 기존 다이얼로그 좌측 패널에 끼워 넣음(점진 적용).

### 필요한 스크립트/모듈 요약
- `figure_theme.py` (rcParams 프리셋), `figure_export.py` (단위/DPI/벡터 export), `widgets/figure_style_panel.py` (공용 컨트롤).

### 주의할 점
- 폰트: 배포(PyInstaller) 환경에 Arial이 없을 수 있음 → fallback(DejaVu Sans) + 번들 폰트 등록 검토. 벡터에 텍스트로 남기려면 뷰어/편집기에 해당 폰트가 있어야 깨지지 않음.
- 기존 다이얼로그는 **한 번에 다 바꾸지 말고** 1–2개(예: gene_expression_bar, go_bar_chart)부터 공용 위젯·export로 교체해 검증 후 확산.
- 테마 적용은 전역 `rcParams`를 건드리므로 **다이얼로그 단위 `rc_context`** 로 격리해 다른 플롯에 누수 방지.

---

## Phase 2 — FigureSpec 직렬화 + 스타일 프리셋 + Round-trip (재현성 핵심)

**목표:** "figure를 여러 번 그리는" 비용 제거. figure = 재현 가능한 spec, 스타일은 데이터와 분리해 재사용.

### 필요한 작업
1. **`FigureSpec` 정의** `src/models/figure_spec.py` (신규, dataclass)
   - 필드: `plot_type`, `data_ref`(dataset id + filter/comparison params 참조), `style`(테마+오버라이드), `annotations`, `size_mm`, `dpi`, `app_version`, `created_at`.
   - `to_dict()/from_dict()` — 기존 `ProjectIO`의 `plot_params`를 이 spec으로 **승격/호환**(`project_io.py` 직렬화에 `style` 블록 추가).
2. **렌더러 분리**: 각 plot_type에 대해 `render(spec, df) -> Figure` 순수 함수. 다이얼로그는 spec을 편집하고 렌더러를 호출만.
   - 점진 전략: 신규 `gene_expression_bar`부터 spec 기반으로 리팩토링 → 패턴 확립 후 확산.
3. **데이터 참조 디커플링**: spec은 데이터 스냅샷이 아니라 **dataset+filter ID 참조**. 다음 실험은 데이터셋만 교체 → 같은 figure 재생성(=템플릿).
4. **스타일 프리셋** `src/utils/style_presets.py` + 저장 위치(`QStandardPaths.AppDataLocation`/기존 `data_path_config` 규약과 통일)
   - 명명된 프리셋 저장/로드("LabDefault","NatureFig"), 임의 플롯에 적용, **Apply style to all**(열린/핀된 모든 플롯에 일괄 적용).
5. **Export에 spec 임베드 (round-trip 편집)**
   - SVG `<metadata>` 또는 PDF `/Keywords`에 `FigureSpec` JSON 삽입. 앱의 "Open Figure"가 이를 읽어 **편집 가능한 플롯으로 복원**.
   - 지난 OLE(더블클릭 편집) 논의의 **현실적·크로스플랫폼 대안**.

### 필요한 스크립트/모듈 요약
- `models/figure_spec.py`, `utils/style_presets.py`, plot_type별 `render()` 함수(렌더러), `project_io.py` 확장(style 블록), figure import(spec 복원) 로더.

### 주의할 점
- **버전 호환**: spec에 `format_version` 두고 마이그레이션 경로 확보(`project_io`의 `format_version` 패턴 재사용).
- 데이터 참조가 깨질 때(원본 데이터셋 없음) graceful fallback: spec에 **요약 통계 캐시** 또는 마지막 렌더 PNG를 함께 저장해 최소한 보기는 가능.
- 프리셋/스타일 적용이 plot_type마다 의미가 다를 수 있음(heatmap colormap vs bar color) → style 스키마를 **공통 + plot_type별 확장**으로 설계.
- round-trip 임베드 시 파일 크기·민감정보(데이터 경로) 노출 주의 → 임베드 on/off 옵션.

---

## Phase 3 — 유의성/주석 레이어 + 멀티패널 + 배치 Export

**목표:** 논문 figure의 "마지막 10%"(유의성 표기, Figure 1A/B/C, 리비전 일괄 재출력).

### 필요한 작업
1. **주석 레이어 일반화** `src/utils/figure_annotations.py` (신규)
   - bracket + 별표 + `n=` + p-value 를 재사용 primitive로. `gene_expression_bar_dialog.py`의 `_p_to_stars`·별표 배치 로직을 추출·확장(쌍별 bracket, 다중비교 보정 옵션: BH/Bonferroni).
2. **멀티패널 합성** `src/gui/figure_layout_dialog.py` (신규)
   - 여러 핀된 plot 탭을 grid로 배치 → 패널 라벨(A/B/C) 자동 → 단일 figure로 export. matplotlib `GridSpec`/subfigures 활용.
3. **배치 export** `src/utils/figure_batch.py` (신규)
   - figure set을 한 번 정의 → 지정 크기/포맷/DPI로 전부 재생성. **논문 리비전 시 전체 figure 1클릭 재출력.** 기존 `ProjectIO`의 핀된 plot 목록을 입력으로.

### 필요한 스크립트/모듈 요약
- `utils/figure_annotations.py`, `gui/figure_layout_dialog.py`, `utils/figure_batch.py`.

### 주의할 점
- 멀티패널은 패널마다 폰트/크기 스케일이 어긋나기 쉬움 → P1 테마가 mm 단위로 잡혀 있어야 일관. (P1 선행 권장)
- 통계 주석은 **검정 가정**(독립성·정규성·등분산)이 데이터에 맞는지 사용자 책임 → UI에 검정명·n 표기 의무화, 잘못된 자동 별표 방지.
- 배치 export는 데이터 참조(P2)가 있어야 의미가 큼 → P2 선행 권장.

---

## Phase 4 — Export-to-Script + Provenance + 템플릿 갤러리 (선택/고급)

**목표:** 재현성의 최상위(앱 밖 재현, 감사 추적), 신규 사용자 온보딩.

### 필요한 작업
1. **Export as Python script**: FigureSpec → 독립 실행 matplotlib 스크립트 생성. 리뷰어 신뢰·앱 외 재현. (렌더러가 순수 함수면 자연스럽게 가능)
2. **Provenance 메타데이터**: 모든 export에 앱 버전·데이터셋·필터·날짜 스탬프(PDF/SVG 메타 또는 사이드카 JSON). `Analysis_Info` 시트 관행과 일치.
3. **템플릿 갤러리**: 자주 쓰는 figure(volcano/heatmap/bar) 스타일 템플릿 모음 + 미리보기 → 새 분석에 즉시 적용.

### 주의할 점
- script export는 앱 내부 헬퍼 의존을 끊고 **순수 matplotlib**로 떨어뜨려야 가치(이식성). 렌더러 설계 시 이를 염두.
- 메타데이터에 절대경로/내부정보 노출 주의(P2와 동일).

---

## 의존 관계 / 권장 진행 순서
```
P1 (테마·export·팔레트)  ──┬──> P2 (spec·프리셋·round-trip)
                           │
                           └──> P3 멀티패널은 P1 필요, 배치export는 P2 필요
P4는 P2(렌더러 순수화) 위에서 가장 매끄럽다.
```
- **최소 가치 컷**: P1만 — 모든 figure가 즉시 저널 톤 + 정확한 벡터 export.
- **재현성 컷**: P1+P2 — figure 재생성/템플릿/round-trip 편집.
- **풀 셋**: P1–P3 — 논문 figure 거의 완결. P4는 여유 시.

## 교차 주의사항(전 Phase 공통)
- **점진적 리팩토링**: 신규/단순 다이얼로그 1–2개에 먼저 적용 → 패턴 검증 후 확산. 13개 한 번에 금지.
- **rcParams 격리**: 항상 `rc_context`로 다이얼로그 단위 적용, 전역 누수 방지.
- **폰트 배포**: PyInstaller 번들에 폰트 포함 여부·fallback 결정.
- **버전/마이그레이션**: spec·프리셋·project에 `format_version`.
- **matplotlib 한계 수용**: 드래그 편집/axis break 비목표.

## 검증 방법 (구현 시)
- **P1**: 한 다이얼로그(예 gene_expression_bar)에 테마+mm export 적용 → PDF/SVG를 Illustrator/Inkscape에서 열어 **텍스트가 편집 가능**하고 크기가 정확한지 확인. 헤드리스(`QT_QPA_PLATFORM=offscreen`)로 savefig 회귀 테스트.
- **P2**: 플롯 만들고 `.seqproj` 저장→재오픈 시 **스타일까지 동일 복원**. SVG 임베드 spec을 "Open Figure"로 복원해 동일 플롯 재현. pytest로 `FigureSpec.to_dict/from_dict` 라운드트립.
- **P3**: 동일 데이터로 유의성 별표가 검정 결과와 일치(scipy 교차검증). 멀티패널 export가 패널 라벨·크기 일관. 배치 export가 N개 figure를 일관 재생성.
- **P4**: 생성된 스크립트를 앱 밖 python에서 실행→동일 figure. 메타데이터 판독.

## 영향받는/신규 파일 (요약)
- 신규: `utils/figure_theme.py`, `utils/figure_export.py`, `models/figure_spec.py`, `utils/style_presets.py`, `utils/figure_annotations.py`, `gui/figure_layout_dialog.py`, `utils/figure_batch.py`, `gui/widgets/figure_style_panel.py`
- 수정(점진): `src/gui/*_dialog.py` 13종(공용 패널·export·렌더러 적용), `src/utils/project_io.py`(style 블록), `src/gui/main_window.py`(메뉴: Figure Layout, Batch Export, Open Figure; Plot Settings Dock 연계)
