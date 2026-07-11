# CMG-SeqViewer — Figure Bundle Export System (Reproducible Export)

**Status**: ✅ **Implemented** (2026-07-09)
**Author**: Implementation Log
**Scope**: Bundle export architecture + Volcano plot pilot + Regeneration scripts
**Reference**: [FIGURE_QUALITY_REPRODUCIBILITY_PLAN.md](FIGURE_QUALITY_REPRODUCIBILITY_PLAN.md) (Phase 4 - export-to-script + provenance)

---

## Overview

cmg-seqviewer에서 생성된 **플롯을 재현 가능한 번들로 내보내고, 다운스트림 figure-atlas에서 출판 품질로 가공하는 아키텍처**를 구현했습니다.

### 핵심 설계
```
cmg-seqviewer (분석 도구)
  ├─ 플롯 렌더링 (matplotlib)
  └─ 번들 export → {데이터 + 스크립트 + 메타데이터}
           ↓
figure-atlas (출판 도구) [미래]
  ├─ 번들 재현 (동일 환경에서 파이썬 스크립트 실행)
  ├─ 스타일 가공 (테마 적용, 크기 조정)
  ├─ README/검증 (재현성 확인)
  └─ 최종 출력
```

**이점**:
- ✅ **재현성**: 데이터 + 파라미터 + 코드가 한 번들에 함께 저장
- ✅ **분리**: cmg-seqviewer는 분석만, figure-atlas는 출판만 담당
- ✅ **이동성**: 번들을 압축해 전송 가능, 외부에서도 독립 재현 가능
- ✅ **감사 추적**: 메타데이터에 생성 환경/버전 기록

---

## 1. 구현된 아키텍처

### 1.1 번들 디렉토리 구조
```
volcano_plot_bundle/
├── inputs/
│   ├── data.csv                    # 원본 데이터 (모든 컬럼)
│   └── statistics.csv              # (선택) 통계 테이블
├── outputs/
│   ├── figure.png                  # 재현 스크립트 기본 출력
│   ├── figure.pdf
│   ├── figure.svg
│   ├── volcano_plot.png            # Plot type별 이름 (source_stem)
│   ├── volcano_plot.pdf
│   └── volcano_plot.svg
├── scripts/
│   └── figure.py                   # 재현 스크립트 (Python)
├── metadata/
│   └── metadata.yaml               # 플롯 메타데이터 + 파라미터
├── manifest.json                   # 번들 인벤토리 + 상태
└── README.md                        # (향후) 사용 설명서
```

### 1.2 구현된 모듈 (`src/utils/figure_bundle_export.py`)

**주요 함수**:

| 함수 | 역할 |
|---|---|
| `export_figure_bundle(context, output_dir, figure_slug, figure_title, plot_type)` | 번들 생성 진입점 |
| `_build_metadata_yaml(...)` | YAML 메타데이터 생성 |
| `_build_volcano_plot_script(...)` | Volcano plot 전용 재현 스크립트 생성 |
| `_build_generic_plot_script(...)` | 범용 plot 재현 스크립트 생성 |
| `_yaml_quote(value)` | YAML 이스케이프 유틸 |

**Context 구조**:
```python
context = {
    'figure': matplotlib.figure.Figure,      # 현재 plot 객체
    'dataframe': pd.DataFrame,               # 원본 데이터
    'plot_params': dict,                     # 플롯 스타일 파라미터
    'dataset_name': str,                     # 데이터셋 이름
    'plot_type': str,                        # 'volcano', 'heatmap', ...
    'figure_title': str,                     # 플롯 제목
    'figure_slug': str,                      # ID (URL-safe)
    'source_stem': str,                      # 파일명 (예: volcano_plot)
    'notes': str,                            # 메타 노트
    'statistics': pd.DataFrame,              # (선택) 통계 테이블
}
```

### 1.3 Volcano Plot 재현 스크립트 (`_build_volcano_plot_script`)

생성되는 `scripts/figure.py`의 로직:
1. **데이터 로드**: `inputs/data.csv` 읽음
2. **파라미터 복원**: plot_params에서 threshold/색상/크기 추출
3. **Regulation 분류**: 
   - up: `log2FC ≥ log2fc_threshold && padj ≤ padj_threshold`
   - down: `log2FC ≤ -log2fc_threshold && padj ≤ padj_threshold`
   - ns: 나머지
4. **산점도 렌더링**: regulation별로 색상 적용
5. **Threshold 선 표시**: 수평선(padj), 수직선(log2fc)
6. **축 레이블/범위**: plot_params에서 복원
7. **출력**: PNG/PDF/SVG 저장

**예시 (생성 스크립트 일부)**:
```python
df["-log10(padj)"] = -np.log10(df["padj"].replace(0, 1e-300))
df["regulation"] = "ns"
df.loc[(df["log2FC"] >= log2fc_threshold) & (df["padj"] <= padj_threshold), "regulation"] = "up"
df.loc[(df["log2FC"] <= -log2fc_threshold) & (df["padj"] <= padj_threshold), "regulation"] = "down"

for reg_type, color in [("ns", ns_color), ("down", down_color), ("up", up_color)]:
    subset = df[df["regulation"] == reg_type]
    ax.scatter(subset["log2FC"], subset["-log10(padj)"], 
               c=[color], s=dot_size, alpha=0.6, 
               label=f"{reg_type.upper()} ({len(subset)})")
```

### 1.4 UI 통합 (`src/gui/visualization_dialog.py` - VolcanoPlotWidget)

**추가된 메서드**:

```python
def get_bundle_context(self) -> dict:
    """현재 플롯 상태를 번들 export 가능한 형태로 반환."""
    return {
        'figure': self.figure,
        'dataframe': self.dataframe,
        'plot_params': self.get_plot_params(),
        'dataset_name': getattr(self, 'dataset_name', 'unknown'),
        'plot_type': 'volcano',
        'figure_title': self.plot_title or 'Volcano Plot',
        'figure_slug': 'volcano_plot',
        'source_stem': 'volcano_plot',
        'notes': 'Generated from cmg-seqviewer volcano plot',
    }

def _export_figure_bundle(self):
    """Bundle export 다이얼로그 + 진행."""
    from PyQt6.QtWidgets import QFileDialog, QMessageBox
    
    folder = QFileDialog.getExistingDirectory(self, "Select bundle output folder")
    if not folder:
        return
    
    try:
        bundle_dir = export_figure_bundle(
            self.get_bundle_context(),
            folder + "/volcano_plot_bundle",
            "volcano_plot",
            self.plot_title or "Volcano Plot",
            "volcano",
        )
        QMessageBox.information(self, "Bundle exported", f"Bundle created at:\n{bundle_dir}")
    except Exception as exc:
        QMessageBox.critical(self, "Bundle export failed", str(exc))
```

**UI 버튼**: 기존 volcano plot 대화상자에 "Export Bundle" 버튼 추가 (기존 export 버튼 옆).

### 1.5 메인 윈도우 통합 (`src/gui/main_window.py`)

**메뉴 항목**: File → Export Figure Bundle

```python
def _on_export_figure_bundle(self):
    """현재 탭의 플롯을 번들로 export."""
    current_tab = self.plot_tabs.currentWidget()
    if not current_tab:
        return
    
    if hasattr(current_tab, 'get_bundle_context'):
        # 번들 지원 플롯
        folder = QFileDialog.getExistingDirectory(...)
        if not folder:
            return
        
        try:
            context = current_tab.get_bundle_context()
            bundle_dir = export_figure_bundle(...)
            QMessageBox.information(...)
        except Exception as exc:
            QMessageBox.critical(...)
    else:
        QMessageBox.information(self, "Unsupported tab", 
                                "The current tab does not expose a bundle export context.")
```

---

## 2. 검증 및 테스트

### 2.1 테스트 커버리지 (`test/test_figure_bundle_export.py`)

| 테스트 | 목적 |
|---|---|
| `test_export_figure_bundle_creates_required_files()` | 번들 디렉토리/파일 생성 확인 |
| `test_generated_regeneration_script_runs()` | 생성 스크립트 구문 검증 (line plot) |
| `test_volcano_plot_regeneration_script_runs()` | Volcano plot 스크립트 실행 + 동적 검증 |

**실행 결과** (2026-07-09):
```
test/test_figure_bundle_export.py::test_export_figure_bundle_creates_required_files PASSED
test/test_figure_bundle_export.py::test_generated_regeneration_script_runs PASSED
test/test_figure_bundle_export.py::test_volcano_plot_regeneration_script_runs PASSED

3 passed in 3.95s
```

### 2.2 실제 번들 검증 (바탕화면 + 현재 작업 디렉토리)

**번들 생성 및 재현**:
```bash
# 번들 생성 (cmg-seqviewer에서 export)
$ python -c "export_figure_bundle(...)"
# 출력: Bundle created at: C:\Users\KimYG\Desktop\volcano_plot_bundle

# 재현 (외부 환경에서)
$ cd volcano_plot_bundle
$ python scripts/figure.py
# 결과: outputs/volcano_plot.png/pdf/svg 생성 완료
```

**확인 결과**:
- ✅ 37,782개 유전자 데이터 완벽 로드
- ✅ regulation 분류 정확함:
  - NS: 37,140개
  - DOWN: 355개
  - UP: 287개
- ✅ 재현된 volcano plot이 원본과 동일
- ✅ PNG (352KB), PDF (263KB), SVG (3MB) 모두 정상 생성

---

## 3. 현재 상태 & 다음 단계

### 3.1 구현 완료 항목
- ✅ 번들 export 모듈 (figure_bundle_export.py)
- ✅ Volcano plot 전용 재현 스크립트 생성
- ✅ VolcanoPlotWidget 통합 (get_bundle_context + _export_figure_bundle)
- ✅ 메인 윈도우 메뉴 통합
- ✅ 테스트 3개 (모두 통과)
- ✅ 실제 데이터 검증

### 3.2 선택적 개선 (향후)
1. **다른 플롯 타입 지원**:
   - Heatmap, PCA, MA plot, GO bar chart, ...
   - 각 플롯 타입별 `_build_{plot_type}_script()` 추가

2. **번들 README 자동 생성**:
   - `scripts/README.md` 또는 `README.md` in bundle root
   - 사용 방법, 환경 요구사항(Python 버전, 패키지), 메타데이터 요약

3. **Figure-atlas 연동** (외부 도구):
   - 번들 폴더 감시 → 자동 처리 스크립트
   - 또는 figure-atlas가 번들을 input으로 받아 처리

4. **번들 압축 & 전송**:
   - `.tar.gz` 또는 `.zip`으로 압축 옵션
   - 클라우드 스토리지 업로드 통합 (AWS S3, GCP, ...)

5. **메타데이터 확장**:
   - Git commit hash (재현성 추적)
   - Dataset versioning (언제 데이터가 갱신되었는지)
   - Author/timestamp

### 3.3 스케일링 고려사항
- **대용량 데이터**: 현재는 data.csv로 저장 (몇 MB까지는 OK). 매우 큰 파일은 parquet/HDF5 고려.
- **플롯 다양성**: 현재 volcano만 구현. ~25개 플롯 모두 지원하려면 각 타입별 렌더링 로직 필요 (아래 확장 전략).
- **성능**: 현재 python 스크립트 생성/실행이 빠르지만(초 단위), 매우 큰 데이터셋은 최적화 필요.

---

## 3.5 확장 전략: 전 플롯 지원 (Scaling to All Plots)

번들 산출물은 두 부분으로 나뉜다:
- **(universal)** 이미지(png/pdf/svg) + `data.csv` + `metadata.yaml`/`manifest.json` — `figure`와 `df`만 있으면
  **모든 플롯에 이미 동작**한다(`fig.savefig`, `df.to_csv`).
- **(per-plot)** `scripts/figure.py` 재현 스크립트 — 플롯별 렌더 로직이 필요한 **유일한** 부분.
  현재 volcano만 실제 스크립트가 있고, 나머지는 `_build_generic_plot_script`(사실상 무의미)로 떨어진다.

### 두 층위 (Level)

| | 재현 스크립트 | 유지보수 | 비용 |
|---|---|---|---|
| **Level 1** 이미지+데이터+메타 (전 플롯) | ❌ 없음 | 🟢 낮음 | 낮음(~1일) |
| **Level 2(a)** 손으로 스크립트 작성 | ✅ 있음 | 🔴 높음(다이얼로그와 로직 중복 → drift) | O(N)·지루 |
| **Level 2(b)** `render()` 순수 함수 추출 | ✅ 있음 | 🟢 낮음(단일 진실 공급원) | O(N)이나 고품질 |

- **Level 1과 Level 2는 배타적이지 않다.** Level 1은 모든 플롯의 **기본 바닥(안전망)**, Level 2(b)는
  그 위에 **충실 재현 스크립트를 얹는 업그레이드**.
- **Level 2(a)는 금지.** `_build_volcano_plot_script`가 지금 이 형태(다이얼로그 `_draw_plot`과 로직 중복)라
  아래 render() 추출로 전환한다.

### `render()` 규약 (Level 2(b))

- `src/plots/{type}.py` 에 `render_{type}(ax, df, params)` 순수 함수. **의존성은 matplotlib/pandas/numpy만**
  (Qt·다이얼로그 참조 금지). `params`는 해당 다이얼로그의 `get_plot_params()`와 동일 키.
- 다이얼로그 `_do_plot`/`_draw_plot`이 이 함수를 호출 → 화면·번들이 **같은 렌더 코드** 사용.
- 번들 export는 `inspect.getsource(render_{type})`로 함수 소스를 스크립트에 **inline** → 외부에서 cmg-seqviewer
  없이 독립 재현. drift 원천 차단.

### 로드맵

1. **Level 1 전 플롯 적용** — `BasePlotDialog`에 공용 `get_bundle_context()` + 다이얼로그별 dataframe 훅.
   ~25 플롯이 즉시 이미지+데이터+메타 번들을 가짐.
2. **Level 2(b) 점진 적용** — 고가치 플롯부터. **volcano가 레퍼런스 구현**
   (`src/plots/volcano.py::render_volcano`).

#### Level 2(b) render() 추출 진행 현황

| 플롯 | 렌더 모듈 (`src/plots/`) | plot_type | 상태 |
|---|---|---|---|
| Volcano | `volcano.py::render_volcano` | `volcano` | ✅ (레퍼런스) |
| Heatmap | `heatmap.py::render_heatmap` | `heatmap` | ✅ |
| GO Dot | `go_dot.py::render_go_dot` | `go_dot` | ✅ |
| GO Bar | `go_bar.py::render_go_bar` | `go_bar` | ✅ |
| MA Plot | `ma.py::render_ma` | `ma` | ✅ |
| PCA | `pca.py::render_pca` | `pca` | ✅ |
| Genomic Distribution | `genomic_distribution.py::render_genomic_distribution` | `genomic_distribution` | ✅ |
| Gene Expression Bar | `gene_expression_bar.py::render_gene_expression_bar` | `gene_expression_bar` | ✅ |
| GO Comparison Dot | `go_comparison_dot.py::render_go_comparison_dot` | `go_comparison_dot` | ✅ |
| Quadrant (RNA vs ATAC) | `quadrant.py::render_quadrant` | `quadrant` | ✅ |
| Integrated Volcano | `integrated_volcano.py::render_integrated_volcano` | `integrated_volcano` | ✅ |
| Meta Volcano | — | — | ⬜ (adjustText 자동 라벨은 적용됨) |
| Count Summary / Annotation Comparison | — | — | ⬜ (다중 데이터셋 → 번들 data.csv 병합 필요) |
| Venn / UpSet / GO Network | — | — | ⬜ (비-scatter, 후순위) |

- **패턴**: 렌더 함수는 `matplotlib/pandas/numpy`만 의존(Qt·utils 금지). 모듈 상수·헬퍼는
  getsource inline 시 함께 실리도록 **함수 내부 지역 정의** 또는 `_render_source(module, *funcs)`로
  다중 함수 inline (예: `go_comparison_dot`은 `_build_long_df` + 렌더 2개 inline).
- **자동 라벨**: gene/sample 라벨이 겹치는 플롯은 `adjustText`로 자동 배치(try/except ImportError).
  Volcano · MA · Meta Volcano · PCA 적용 완료.

---

## 4. 아키텍처 결정사항 (Design Decisions)

### 4.1 왜 Python 스크립트인가?
- ✅ **이동성**: 어디서나 Python이 설치되어 있으면 재현 가능
- ✅ **확장성**: 데이터 변환, 통계 계산, 스타일 가공이 자유로움
- ✅ **감시성**: 스크립트를 읽고 수정 가능 (블랙박스 아님)
- ✅ **무료**: 특수 소프트웨어(Prism, Origin) 필요 없음

**대안 검토 및 거절 이유**:
- R 스크립트: R 의존성 추가, cmg-seqviewer는 Python-only
- Jupyter notebook: 크기가 크고, nbconvert 외부 의존
- 직렬화된 Figure (pickle): 환경 간 호환성 낮음

### 4.2 왜 YAML + Python dict 혼합인가?
- YAML은 **사람이 읽기 좋음** (metadata.yaml의 가독성)
- Python dict는 **스크립트 내부에서 빠름** (JSON parse 오버헤드 없음)
- `repr(dict)` 사용 시 NaN/None/float 등 모두 Python 리터럴로 정확 표현

### 4.3 왜 메타데이터를 YAML과 manifest.json에 중복 저장하는가?
- YAML: 사람 읽기용, 메모장에서도 열 수 있음
- manifest.json: 프로그램 파싱용, 빠른 검증, figure-atlas 자동 감지용

---

## 5. 상태 추적 및 메타데이터 예시

### 5.1 manifest.json (번들 인벤토리)
```json
{
  "status": "ok",
  "figure_slug": "volcano_plot",
  "figure_title": "Volcano Plot",
  "plot_type": "volcano",
  "created_at": "2026-07-09T15:32:45.123456+00:00",
  "files": [
    "inputs/data.csv",
    "scripts/figure.py",
    "metadata/metadata.yaml",
    "outputs/volcano_plot.png",
    "outputs/volcano_plot.pdf",
    "outputs/volcano_plot.svg"
  ]
}
```

### 5.2 metadata.yaml (상세 메타데이터)
```yaml
figure_id: volcano_plot
figure_title: "Volcano Plot"
figure_slug: volcano_plot
plot_type: volcano
source_stem: volcano_plot
dataset_name: actual_volcano
claim_boundary: "Actual volcano plot from real RNA-seq data"
created_at: "2026-07-09T15:32:45.123456+00:00"
app_version: "cmg-seqviewer-bundle-export"
input_files:
  - inputs/data.csv
output_files:
  - outputs/figure.png
  - outputs/figure.pdf
  - outputs/figure.svg
statistics_tables:
  - inputs/statistics.csv
plot_params:
  padj_threshold: "0.05"
  log2fc_threshold: "1.0"
  down_color: "#0000ff"
  up_color: "#ff0000"
  ns_color: "#808080"
  ...
```

---

## 6. 사용자 플로우

### 6.1 cmg-seqviewer에서 export
1. **Plot 렌더링**: Volcano plot 다이얼로그 열기
2. **옵션 설정**: threshold, 색상, 레이블 조정
3. **Export 선택**: 
   - 메뉴: File → Export Figure Bundle
   - 또는 플롯 대화상자의 "Export Bundle" 버튼
4. **폴더 선택**: 번들을 저장할 위치 (로컬 또는 네트워크 드라이브)
5. **완료**: "Bundle exported at: C:\...\volcano_plot_bundle"

### 6.2 번들 검증 (외부 환경)
```bash
$ cd volcano_plot_bundle
$ python scripts/figure.py
# 또는
$ python scripts/figure.py --dpi 600 --format pdf
# (향후 인자 처리 추가)
```

### 6.3 Figure-atlas 처리 (향후)
```bash
$ figure-atlas ingest --bundle volcano_plot_bundle
# → 메타데이터 파싱 + 재현성 검증 + 스타일 가공 + README 생성
```

---

## 7. 라이선스 및 재현성 보장

**번들 포함 사항**:
- ✅ 원본 데이터 (data.csv)
- ✅ 플롯 파라미터 (metadata.yaml)
- ✅ 재현 스크립트 (figure.py)
- ✅ 현재 출력 (outputs/)
- ✅ 메타데이터 (manifest.json)

**재현성 수준**:
- **100% 재현 가능**: 같은 Python 버전, 같은 패키지 버전에서 정확히 동일한 이미지 생성
- **높은 호환성**: Python 3.8+, matplotlib 3.5+ 범위에서 시각적 유사성 보장 (폰트/미세 렌더링 제외)

**제약**:
- matplotlib 버전 간 DPI/렌더링 미세 차이 가능성 있음
- 폰트 미설치 환경에서 fallback 폰트 사용 (시각 다를 수 있음)
- 난수 시드가 없으므로 일부 stochastic 플롯(scatter jitter)은 완벽 동일하지 않을 수 있음

---

## 8. 파일 변경 로그

| 파일 | 변경 사항 | 일시 |
|---|---|---|
| `src/utils/figure_bundle_export.py` | 신규 생성 | 2026-07-09 |
| `src/gui/visualization_dialog.py` | VolcanoPlotWidget에 `get_bundle_context()` + `_export_figure_bundle()` 추가 | 2026-07-09 |
| `src/gui/main_window.py` | 메뉴 File → Export Figure Bundle + `_on_export_figure_bundle()` 추가 | 2026-07-09 |
| `test/test_figure_bundle_export.py` | 3개 테스트 케이스 추가 (번들 생성 + 스크립트 실행 검증) | 2026-07-09 |

---

## 9. 향후 확장 (Roadmap)

### Phase 2 (중기)
- [ ] 다른 플롯 타입 지원 (heatmap, PCA, GO, ...)
- [ ] 번들 README 자동 생성
- [ ] 메타데이터 확장 (Git hash, dataset version)

### Phase 3 (후기)
- [ ] Figure-atlas 연동 (외부 도구)
- [ ] 번들 압축 + 클라우드 업로드
- [ ] 대용량 데이터 포맷 지원 (parquet, HDF5)

### Phase 4 (선택)
- [ ] 난수 시드 저장 + 완벽 재현
- [ ] 멀티패널 번들 (여러 플롯 한 번에)
- [ ] 스타일 템플릿 라이브러리

---

## 10. 참고 자료

| 문서 | 링크 |
|---|---|
| 상위 계획 | [FIGURE_QUALITY_REPRODUCIBILITY_PLAN.md](FIGURE_QUALITY_REPRODUCIBILITY_PLAN.md) |
| P1 구현 | [FIGURE_QUALITY_P1_IMPLEMENTATION.md](FIGURE_QUALITY_P1_IMPLEMENTATION.md) |
| 테스트 코드 | `test/test_figure_bundle_export.py` |
| 모듈 코드 | `src/utils/figure_bundle_export.py` |
| UI 통합 | `src/gui/visualization_dialog.py::VolcanoPlotWidget` |
| 메인 윈도우 | `src/gui/main_window.py::_on_export_figure_bundle` |
