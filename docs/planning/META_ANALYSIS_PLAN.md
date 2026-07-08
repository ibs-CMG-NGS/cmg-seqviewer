# 전사체 메타 분석 — CMG-SeqViewer 기능 확장 계획

> 이 문서는 세션 중 plan 파일에 작성했다가 이후 다른 계획으로 덮어써진 메타 분석 계획을
> 영구 보존용으로 복원한 것이다. (plan 파일은 계획마다 덮어써지므로 durable 위치에 저장)

## Context

`NGS 메타 분석 파이프라인 구축 전략` 문서가 다루는 종간(cross-species) 전사체 메타 분석의
핵심 전략은 **사후 통합(late integration)**: 각 코호트에서 독립적으로 DE 분석 →
p-value / effect size 를 통계적으로 결합. 이는 CMG-SeqViewer의 Compare 기능이 이미 하는 일과
큰 틀에서 같다.

| 메타 분석 단계 | CMG-SeqViewer 현황 |
|---|---|
| 각 코호트 독립 DE 분석 | ✅ 각 DE 파일을 개별 데이터셋으로 로드 |
| 결과를 넓은 행렬로 합치기 | ✅ Compare > Statistics Filtering → `{DS}_log2fc`, `{DS}_padj` 와이드 테이블 |
| Fisher / Stouffer p-value 결합 | ❌ **없음** — 추가 시 완전한 메타 분석이 됨 |
| Cross-species 유전자 심볼 통합 | ❌ **없음** — 같은 종 데이터셋만 비교 가능 |
| 메타 시그널 시각화 (Volcano) | ❌ **없음** |

### 범위 원칙

CMG-SeqViewer 철학: **외부 파이프라인 결과(DE/GO parquet)를 받아 탐색·시각화**. 원시 데이터
재처리는 하지 않는다.

**범위 내** (DE 결과 + scipy + 번들 CSV 만으로 구현):
- Fisher/Stouffer 통계 결합
- human-mouse-rat 1:1 상동 유전자 매핑 (BioMart 정적 스냅샷 CSV 번들)
- 메타 Volcano 시각화

**범위 밖** (원시 count matrix 또는 R 전용 툴 필요):
- ComBat-seq 배치 보정, Seurat CCA/RPCA, SAMap
- CIBERSORTx, CARD, ptalign, MetaNeighbor

---

## Phase M1: 메타 통계 — Fisher/Stouffer 결합 컬럼
**우선순위: 높음 | 난이도: 낮음 | 예상 1–2일**

**목적:** Compare > Statistics Filtering 결과 와이드 테이블에 각 유전자의 메타 p-value와
결합 effect size 컬럼을 추가. DB에 쌓인 여러 연구(같은 종, 다른 시점/조건)에서 공통 신호를
통계적으로 포착.

**구현 위치:** 와이드 테이블을 만드는 곳 — `main_window.py`의 `_compare_statistics()`
(또는 `src/utils/statistics.py`의 비교 집계). 데이터셋별 `{DS}_log2fc`, `{DS}_padj`가
이미 있으므로 그 값들로 행별 결합.

**추가 컬럼:**
```python
import numpy as np, scipy.stats as st
# 유전자별로 K개 데이터셋의 pvals(=padj), lfcs 수집 (NaN 데이터셋은 K에서 제외)
pvals = np.clip(pvals, 1e-300, 1.0)           # log(0) 방지

# Fisher: -2*sum(ln p) ~ chi2(2K)
chi2 = -2.0 * np.sum(np.log(pvals))
meta_pvalue_fisher = st.chi2.sf(chi2, df=2*len(pvals))

# Stouffer (방향성 반영): z = Φ^-1(1-p) * sign(lfc)
z = st.norm.ppf(1 - pvals/2) * np.sign(lfcs)  # 양측 p → z, 부호는 lfc
meta_z = np.sum(z) / np.sqrt(len(z))
meta_pvalue_stouffer = 2 * st.norm.sf(abs(meta_z))

meta_log2fc_mean = float(np.mean(lfcs))
meta_direction   = "concordant" if np.all(np.sign(lfcs)==np.sign(lfcs[0])) else "discordant"
meta_found_in    = len(pvals)   # K개 중 유효 데이터셋 수
```

**UI:** ComparisonPanel 변경 없음 — 기존 "Statistics Filtering" 실행 시 자동으로 컬럼 추가.
열 순서: `meta_pvalue_fisher`, `meta_pvalue_stouffer`, `meta_log2fc_mean`, `meta_direction`,
`meta_found_in`, 이후 기존 `{DS}_*`.

---

## Phase M2: Cross-Species 상동 유전자 매핑
**우선순위: 중간 | 난이도: 중간 | 예상 2–3일**

**목적:** 서로 다른 종의 DE 데이터셋(mouse Trp53 / human TP53 / rat Tp53)을 하나의
인간 유전자 심볼 공간에서 비교.

**데이터:** `data/orthologs/human_mouse_rat_1to1.csv` (번들, Ensembl BioMart 정적 스냅샷)
- 컬럼: `human_symbol, mouse_symbol, rat_symbol, ensembl_human_id`
- ~16,000 1:1 ortholog, ~400KB

**흐름:**
1. ComparisonPanel에 "Cross-species harmonization" 체크박스 (또는 organism 상이 시 자동 감지)
2. 비인간 데이터셋의 gene symbol → human_symbol 치환 (1:1만, 매핑 안 되는 유전자 제외)
3. 매핑 후 기존 Statistics Filtering 로직 그대로 실행
4. 결과 헤더에 `(mouse→human)` 등 종 정보 표시, 매핑 실패 개수 경고

**구현 위치:**
- 신규 `src/utils/ortholog_mapper.py`: `OrthologMapper.map_to_human(df, source_organism)`
- `statistics.py` / `_compare_statistics` 전처리 단계에 매핑 삽입
- `src/gui/comparison_panel.py`: 체크박스

---

## Phase M3: 메타 Volcano Plot
**우선순위: 중간 | 난이도: 낮음 | 예상 1일**

**목적:** Fisher 메타 p-value + 평균 log2FC 로 재현성 높은 공통 신호를 한눈에.

**시각화:**
- X = `meta_log2fc_mean`, Y = `-log10(meta_pvalue_fisher)`
- 색 = `meta_found_in` (N/K), 옵션으로 concordant/discordant 구분
- 상위 유의 유전자 auto-label

**구현 위치:**
- 신규 `src/gui/meta_volcano_dialog.py` (`BasePlotDialog` 상속)
- `main_window.py` Visualization → 🧩 Cross-Dataset Comparison 서브메뉴에
  "🌋 Meta Volcano Plot" 추가 (Comparison: Statistics 탭 + meta_ 컬럼 존재 시 활성)

---

## 철학 정합성

- **반복 탐색:** DB에 모은 여러 연구를 포함/제외해가며 메타 신호를 확인 — 핵심 사용 패턴과 일치
- **외부 의존 최소:** ComBat-seq/orthogene(R) 없이 번들 CSV + scipy 만으로 구현, 별도 설치 불필요
- **데이터 축적 → 인사이트:** 여러 연구자가 같은 DB에 쌓은 결과를 가장 효과적으로 활용

## 권장 순서

| Phase | 내용 | 난이도 | 의존성 | 순서 |
|---|---|---|---|---|
| M1 | Fisher/Stouffer 메타 통계 | ★☆☆ | scipy(기존) | 1 |
| M3 | 메타 Volcano Plot | ★☆☆ | M1 | 2 |
| M2 | Cross-species ortholog | ★★☆ | 번들 CSV | 3 |

## 검증

1. **M1:** mouse DE 2–3개로 Statistics Filtering → `meta_pvalue_fisher` 컬럼 확인 →
   알려진 일관 신호 유전자가 상위에 오는지
2. **M2:** human DE + mouse DE 혼합 → Cross-species 체크 → 인간 심볼로 통합, 매핑 실패 경고
3. **M3:** M1 후 Meta Volcano → `meta_found_in ≥ K` 필터 → Export 동작
