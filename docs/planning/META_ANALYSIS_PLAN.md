# 전사체 메타 분석 — CMG-SeqViewer 기능 확장 계획

> 이 문서는 세션 중 plan 파일에 작성했다가 이후 다른 계획으로 덮어써진 메타 분석 계획을
> 영구 보존용으로 복원한 것이다. (plan 파일은 계획마다 덮어써지므로 durable 위치에 저장)

## 진행 상태 (2026-07-08)

| Phase | 상태 | 커밋 |
|---|---|---|
| **M1** Fisher/Stouffer 메타 통계 컬럼 (유전자 수준) | ✅ **완료** | `08585b1`, `a591977` |
| **M3** 메타 Volcano Plot | ✅ **완료** | `8602121` |
| **M4a** GO/pathway term 수준 메타 (late aggregation) | ✅ **완료** | `1e6f221` |
| **M5** 효과크기 random-effects 메타 (log2FC+SE) | ✅ **완료** | `<this>` |
| **M2** Cross-species ortholog 매핑 | ⬜ 다음 | — |
| **M4b** meta-signature → enrichment (early aggregation) | ⬜ 미착수 (online enrichment 엔진 의존) | — |

**구현된 것 (M1+M3):**
- `src/utils/meta_stats.py` — `combine_pvalues(pvals, lfcs)` (Fisher + 방향성 Stouffer + 평균 log2FC + concordant/discordant + found_in)
- `main_window.py` `_compare_statistics` — 필터 이전 전체 데이터에서 유전자별 (log2fc, padj)를 조회(`_full_gene_stats`)해 편향 없이 결합. `Comparison: Statistics` 시트에 `meta_pvalue_fisher / meta_pvalue_stouffer / meta_log2fc_mean / meta_direction / meta_found_in` 컬럼 자동 추가. p-value 계열 컬럼은 scientific notation 표시.
- `src/gui/meta_volcano_dialog.py` — Visualization → 🧩 Cross-Dataset Comparison → 🌋 Meta Volcano Plot. Fisher/Stouffer 선택, 임계값·found-in·top-N 라벨, up/down/discordant 색 구분, Export.

**남은 것:** M2 (아래) — human/mouse/rat 1:1 ortholog 번들 CSV 확보 + 매핑.

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

## Phase M1: 메타 통계 — Fisher/Stouffer 결합 컬럼  ✅ 완료 (`08585b1`)
**우선순위: 높음 | 난이도: 낮음 | 예상 1–2일**

> **구현 노트:** 계획대로 구현. 핵심 결정 — 와이드 테이블의 유의 hit만 결합하면 편향되므로,
> `_full_gene_stats()`로 **필터 이전 전체 데이터셋**에서 유전자별 (log2fc, p)를 조회해
> 검정된 모든 데이터셋을 결합한다. Fisher는 극유의 유전자에서 0으로 underflow → Stouffer 컬럼으로 순위 구분.
>
> **정합성 보강(`후속`):** 교과서적 Fisher/Stouffer에 맞춰 study 내 보정된 padj가 아니라 **raw `pvalue`로 결합**
> (없으면 padj 폴백), 결합 후 유전자 전체에 **BH 보정한 `meta_fdr_fisher` 컬럼 추가**
> (`meta_stats.benjamini_hochberg`). Fisher=크기 / Stouffer=방향 역할 분리는 유지(단측 Fisher는
> Stouffer와 중복이라 미채택). Meta Volcano p-source에 Fisher/Fisher FDR/Stouffer 선택 추가.

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

## Phase M2: Cross-Species 상동 유전자 매핑  ⬜ 다음 차례
**우선순위: 중간(종간 비교 필요 시) | 난이도: 코드 낮음~중간 / 데이터 확보가 관문 | 예상: 코드 ~1일 + 데이터 준비**

**목적:** 서로 다른 종의 DE 데이터셋(mouse Trp53 / human TP53 / rat Tp53)을 하나의
인간 유전자 심볼 공간으로 통일해 비교. 통일 후에는 **M1·M4a·M5 메타 통계가 그대로 재사용**된다
(심볼 공간만 맞추면 됨).

### 난이도 요약

- **코드: 쉬움~중간 (~1일).** OrthologMapper(~40줄) + `_compare_statistics` 전처리 한 단계 +
  ComparisonPanel 체크박스. 메타 통계 로직은 **손대지 않음**.
- **데이터: 실질적 관문 (한 번만).** human/mouse/rat 1:1 ortholog CSV를 **외부(Ensembl/MGI)에서
  생성**해야 함 — 네트워크 필요. 오프라인 개발 셸에서는 만들 수 없으므로 생성 스크립트를 사용자가
  한 번 실행하는 방식으로 조달.

### 데이터 조달 (블로커)

**대상 파일:** `data/orthologs/human_mouse_rat_1to1.csv` (번들, ~16k행, ~400KB)
- 컬럼: `human_symbol, human_ensembl, mouse_symbol, mouse_ensembl, rat_symbol, rat_ensembl`
- **1:1 orthologs만** (다대다 aggregation 회피 → 노이즈 최소, 계획 확정 사항)

**출처 후보:**
- **Ensembl BioMart** (표준) — `pybiomart` 또는 BioMart 웹. human 기준으로 mouse/rat
  `homolog_orthology_type == 'ortholog_one2one'` 필터.
- MGI/JAX homology (`HOM_MouseHumanSequence.rpt`) — human-mouse 위주, 무료.
- NCBI HomoloGene / DIOPT — 대안.

**조달 방식 (택1):**
- **방법 A (권장):** 신규 `scripts/build_ortholog_table.py`(pybiomart 기반)를 제공 → 사용자가
  인터넷 되는 환경에서 1회 실행 → CSV 생성 → 리포에 커밋.
- **방법 B:** 사용자가 Ensembl/MGI 파일을 내려받으면 표준화 파서를 붙여 CSV 생성.

### 숨은 복잡도 (난이도를 "중간"으로 올리는 요인)

1. **organism 감지** — 각 데이터셋의 종을 알아야 함. 우선순위:
   `Dataset.metadata['organism']` → 없으면 **gene_id 접두사 패턴**(`ENSG`=human, `ENSMUSG`=mouse,
   `ENSRNOG`=rat)으로 폴백. 심볼 casing도 보조 단서.
2. **매핑 키 — 심볼보다 Ensembl ID가 robust.** mouse `Trp53`→human `TP53`은 단순 대문자화로
   안 됨. **가능하면 gene_id(ENSMUSG→ENSG)로 매핑** 후 human_symbol 부여; gene_id 없으면 심볼로
   ortholog 테이블 조회.
3. **1:1 엄격 필터** — 1:1 아닌(1:다/다:다) 유전자는 제외. 매핑 실패·모호 개수를 UI 경고로 표시.
4. **배포(PyInstaller)** — 번들 CSV를 `rna-seq-viewer.spec` / `cmg-seqviewer-macos.spec`의
   `datas`에 포함해야 frozen 빌드에서 로드됨 (ONLINE_ENRICHMENT_ANALYSIS_PLAN G1과 동일 이슈).
   경로는 `data_path_config.py` 규칙에 맞춰 frozen/dev 양쪽 해석.

### 구현 흐름

1. **organism 감지** → 비인간 데이터셋 식별.
2. **OrthologMapper.map_to_human(df, source_organism)** — 비인간 df의 gene_id/symbol을
   human_symbol(+human_ensembl)로 치환, 1:1 매핑 실패 행 제외, (원본→human) 이력 보존.
3. 매핑 후 **기존 `_compare_statistics` 그대로 실행** → M1/M5 메타 컬럼 자동 생성.
4. 결과 헤더/메타데이터에 `(mouse→human)` 등 종 표기, **매핑 실패 개수 경고**.
5. cross-species → **M4b(early aggregation)로 이어질 때 M2가 선행**(공통 유전자 공간 확보 후 enrichment).

### 구현 위치

- 신규 `src/utils/ortholog_mapper.py`: `OrthologMapper`(CSV 로드/캐시, `map_to_human`, organism 감지 헬퍼)
- 신규 `scripts/build_ortholog_table.py`: BioMart→CSV 생성기 (사용자 1회 실행)
- `data/orthologs/human_mouse_rat_1to1.csv`: 번들 데이터
- `main_window.py` `_compare_statistics` 전처리 단계에 매핑 삽입
- `src/gui/comparison_panel.py`: "Cross-species harmonization" 체크박스
- `*.spec`: 번들 CSV `datas` 추가

### 현실적 우선순위 메모

현재 랩 데이터는 대부분 **mouse** → 같은 종 비교가 주력이면 M2 우선순위 낮음(M1/M4a/M5로 충분).
"인간 질환 vs 동물 모델" 같은 **종간 메타가 실제로 필요해질 때** 착수 권장. 데이터 조달이
선행되어야 하므로, 착수 시 **생성 스크립트 → CSV 커밋 → 코드 구현** 순서.

### 검증

human DE + mouse DE 혼합 선택 → Cross-species 체크 → 인간 심볼로 통합, 알려진 ortholog 쌍
(예: mouse Trp53 ↔ human TP53)이 한 행으로 합쳐지는지, 1:1 매핑 실패 개수가 경고에 표시되는지.

---

## Phase M3: 메타 Volcano Plot  ✅ 완료 (`8602121`)
**우선순위: 중간 | 난이도: 낮음 | 예상 1일**

> **구현 노트:** `Comparison: Statistics` 시트가 활성일 때 실행. Fisher/Stouffer p-source 토글,
> meta-p·|mean log2FC| 임계값, found-in 필터, top-N 라벨. Fisher underflow(=0) 대비 p를 1e-300으로 clip.

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

## Phase M4: 모듈(패스웨이/GO) 수준 메타 분석  ⬜ 미착수
**우선순위: 중간 | 배경: 유전자 수준(M1)의 상위 층위**

M1/M3은 **유전자 수준** 결합이다. 실무에서 가장 흔한 모듈은 GO/KEGG인데, 모듈 수준 메타에는
정석 두 갈래가 있고 **의존성이 달라 M4a/M4b로 분리**한다.

### 배경: 두 가지 정석 (반드시 구분)

- **A. Early aggregation** — 유전자 수준에서 먼저 결합(meta-signature) → 그 **통합 결과 하나**에
  enrichment를 **한 번만** 수행 (meta-DEG → ORA, 또는 meta 랭킹 → GSEA prerank).
  통계적으로 더 강력(threshold-free, 단일 background). 첨부 문서 9장이 택한 방식.
  **단, enrichment 엔진이 있어야 가능** → ONLINE_ENRICHMENT_ANALYSIS_PLAN 의존.
- **B. Late aggregation** — 각 연구가 독립적으로 enrichment한 결과의 **패스웨이별 p-value를 결합**
  (M1을 term 단위로 재사용). CMG의 GO Term Comparison 와이드 테이블에 그대로 얹힌다.
  **enrichment 엔진 불필요, 지금 가능.**

### 모듈 수준에서 반드시 조심 (계획에 박아둘 값)

1. **온톨로지 버전 일치** — 연구 간 GO/KEGG term_id가 같은 릴리스여야 결합 유효.
2. **Background 이질성 / ORA 임계값 민감도** — 연구별 검정 유전자 집합·DEG 컷오프 차이가 term p를
   흔든다. A(early, 단일 background·GSEA)가 이 문제를 우회.
3. **방향성** — 패스웨이도 up/down이 갈린다. GSEA면 sign(NES)로 Stouffer, ORA면 up/down 리스트 분리.
4. **GO는 종-불문(species-agnostic)** — 모듈 수준(B)은 **M2(ortholog) 없이도** cross-species 비교가
   상당 부분 가능. 반면 A는 종이 다르면 **M2로 공통 유전자 공간 매핑 후** meta-signature → enrichment
   (사슬: **M2 → M4b**).

### M4a — GO/pathway term 수준 late aggregation (B)  ✅ 완료
**우선순위: 중간 | 난이도: 낮음**

> **구현 노트:** `_compare_go_terms`가 term별 raw `pvalue` + log2(fold enrichment)를 수집해
> `combine_pvalues`로 결합 → `meta_pvalue_fisher / meta_fdr_fisher / meta_pvalue_stouffer /
> meta_log2fe_mean / meta_direction / meta_found_in` 추가(BH는 `benjamini_hochberg`). effect를
> log2(FE)로 주어 방향(enriched/depleted)이 자연스럽게 반영됨. **Meta Volcano가 term 수준을
> 자동 인식**(x=meta_log2fe_mean)해 유전자/term 겸용. 헤드리스 검증: 신경 관련 term이 일관 상위.

- 대상: `Comparison: GO Terms` 시트(또는 GO Term Comparison 와이드 테이블). GO parquet엔 term별
  raw `pvalue`가 이미 있다(fdr/qvalue와 별도) → 그 값을 결합.
- 구현: 유전자 수준 M1의 term 버전. `meta_stats.combine_pvalues` / `benjamini_hochberg` **그대로 재사용**.
  term별로 연구 간 enrichment p 결합 → `meta_pvalue_fisher/stouffer`, `meta_fdr_fisher`, `meta_found_in`.
  방향성은 GO 데이터에 `direction`이 있으면 Stouffer, 없으면 Fisher만.
- 결과: "여러 실험에서 **일관되게 enriched된 term**" 컬럼. Meta Volcano의 term 버전 또는 기존
  GO Dot Plot에 메타 지표 강조.
- 구현 위치: `_compare_go_terms`(GO 비교 와이드 테이블 생성부)에 메타 컬럼 추가.

### M4b — meta-signature → enrichment (early aggregation, A)  ⬜ 엔진 의존
**우선순위: 중간 | 난이도: 낮음(엔진 위에서) | 의존: ONLINE_ENRICHMENT_ANALYSIS_PLAN**

- online enrichment 엔진이 착지하면 **거의 공짜**로 얻어진다 — 엔진의 DEG 입력 소스에
  **"Comparison: Statistics 시트의 meta-DEG / meta 랭킹"** 을 추가하기만 하면 된다.
- ORA 경로: meta FDR 임계 → meta-DEG → Enrichr/GOATOOLS ORA.
- GSEA 경로(더 엄밀): meta 랭킹(meta_z 또는 −log10 meta p × sign) → gseapy `prerank`.
- cross-species는 **M2 → meta-signature → enrichment** 순.
- **연동 지점은 ONLINE_ENRICHMENT_ANALYSIS_PLAN에 명시**(입력 소스 + GSEA prerank 검토).

---

## Phase M5: 효과크기 random-effects 메타 (log2FC + SE)  ✅ 완료
**우선순위: 높음 | 난이도: 낮음(numpy만) | 대상: DE/DA (유전자/peak)**

> **구현 노트:** `meta_stats.random_effects(effects, ses)` (DerSimonian-Laird) 추가. `_full_gene_stats`가
> (log2fc, pvalue, **lfcSE**) 3-튜플로 확장(SE 컬럼: `lfcse/lfcSE/lfc_se/stderr/se`). `_compare_statistics`가
> 유전자별로 `random_effects` 호출 → `meta_effect_log2fc / meta_effect_se / meta_ci_low / meta_ci_high /
> meta_pvalue_re / meta_i2` 추가. Meta Volcano에 **X축 소스 콤보(Pooled log2FC(RE) 기본 / Mean log2FC)**,
> P소스에 Random-effects 추가. lfcSE 없는 데이터셋은 M5에서만 제외(M1은 유지). 헤드리스 검증: 세포주기
> 유전자 일관 down, I²로 이질성 구분(0~44%), 방향 상쇄 시 pooled≈0·p=1.

M1(Fisher/Stouffer)은 **p-value 결합(증거 aggregation)** 이다. M5는 **효과크기 결합(추정)** —
서로 다른 통계 계열이며 **상보적**이다. 우리 DE parquet엔 `lfcse`(=log2FC의 SE)가 이미 있으므로
바로 적용 가능하다. (GO term 수준(M4a)엔 효과크기 SE가 없어 적용 불가 — p 결합만.)

### 두 계열 구분 (문서에 박아둘 값)

| | M1 Fisher/Stouffer | **M5 random-effects** |
|---|---|---|
| 성격 | 증거(p) 결합 | **효과크기 추정** |
| 결과 | 결합 p-value | **통합 log2FC + CI + p** |
| 연구 가중 | 동등 | **역분산 가중(1/SE²)** |
| 이질성 | 없음 | **I²/τ²/Q 모델링** |
| 입력 | p(+부호) | **log2FC + SE(lfcSE)** |

랩처럼 **비슷하지만 다른 조건**(시점·농도·연구자)을 합칠 때, I²로 "신호가 조건 전반에서 견고한가
vs 특정 조건 특이적인가"를 정량화 → 매우 유용. 현재 `meta_log2fc_mean`(단순 평균)을
**역분산 가중 통합 추정치로 승격**하는 셈.

### 방법: DerSimonian-Laird random-effects

각 유전자 g에 대해 검정된 K개 데이터셋의 (yᵢ=log2FC, sᵢ=SE):

```
# Fixed-effect 가중과 통합
wᵢ = 1/sᵢ²
ȳ_fixed = Σwᵢyᵢ / Σwᵢ
Q  = Σwᵢ(yᵢ − ȳ_fixed)²                 # 이질성 통계량
τ² = max(0, (Q − (K−1)) / (Σwᵢ − Σwᵢ²/Σwᵢ))   # DL 추정
I² = max(0, (Q − (K−1))/Q) * 100        # % 이질성

# Random-effects: 가중에 τ² 추가
wᵢ* = 1/(sᵢ² + τ²)
meta_effect = Σwᵢ*yᵢ / Σwᵢ*
meta_effect_se = sqrt(1/Σwᵢ*)
z = meta_effect / meta_effect_se
meta_pvalue_re = 2·norm.sf(|z|)
CI95 = meta_effect ± 1.96·meta_effect_se
```

K=1이면 통합 불가(None). sᵢ 결측/0이면 해당 연구 제외(또는 작은 하한).

### 구현

- **신규** `src/utils/meta_stats.py`에 `random_effects(effects, ses)` 추가
  (`combine_pvalues`와 병렬). 순수 numpy/scipy, 새 의존성 없음.
- `_full_gene_stats`를 **(log2fc, pvalue, lfcSE)** 3-튜플로 확장(현재 (log2fc, pvalue)).
  lfcSE 컬럼 변형: `lfcse`, `lfcSE`, `lfc_se`, `stderr`.
- `_compare_statistics`: 유전자별로 `random_effects` 호출 → 컬럼 추가
  `meta_effect_log2fc`, `meta_effect_se`, `meta_ci_low`, `meta_ci_high`,
  `meta_pvalue_re`(scientific), `meta_i2`.
- **Meta Volcano X축 옵션**: 단순 평균(`meta_log2fc_mean`) 대신 **통합 log2FC(`meta_effect_log2fc`)**
  선택 가능하게(콤보 또는 자동 우선). Y축은 `meta_pvalue_re`도 소스로 추가.
- lfcSE가 없는 데이터셋이 섞이면 그 데이터셋만 M5에서 제외(경고), M1은 그대로.

### 검증

DE 2–3개로 Statistics Filtering → `meta_effect_log2fc`/`meta_i2` 확인 →
(a) 통합 log2FC가 개별값들 사이의 정밀도 가중 평균인지, (b) 방향 엇갈리는 유전자에서 I² 높은지,
(c) `meta_pvalue_re`가 M1 결과와 상관되나 동일하진 않은지(다른 계열).

---

## 철학 정합성

- **반복 탐색:** DB에 모은 여러 연구를 포함/제외해가며 메타 신호를 확인 — 핵심 사용 패턴과 일치
- **외부 의존 최소:** ComBat-seq/orthogene(R) 없이 번들 CSV + scipy 만으로 구현, 별도 설치 불필요
- **데이터 축적 → 인사이트:** 여러 연구자가 같은 DB에 쌓은 결과를 가장 효과적으로 활용

## 권장 순서

| Phase | 내용 | 난이도 | 의존성 | 순서 | 상태 |
|---|---|---|---|---|---|
| M1 | Fisher/Stouffer 메타 통계 (유전자) | ★☆☆ | scipy(기존) | 1 | ✅ 완료 |
| M3 | 메타 Volcano Plot | ★☆☆ | M1 | 2 | ✅ 완료 |
| M4a | GO term 수준 메타 (late) | ★☆☆ | meta_stats 재사용 | 3 | ✅ 완료 |
| M5 | 효과크기 random-effects (log2FC+SE) | ★☆☆ | lfcSE(기존) | 4 | ✅ 완료 |
| M2 | Cross-species ortholog | ★★☆ | 번들 CSV | 5 | ⬜ 다음 |
| M4b | meta-signature → enrichment (early) | ★☆☆ | **online enrichment 엔진** | 엔진과 동시 | ⬜ |

## 검증

1. **M1** ✅: mouse DE 2–3개로 Statistics Filtering → `meta_pvalue_fisher` 컬럼 확인 →
   일관 신호 유전자가 상위에 오는지. (헤드리스 검증 완료: 673행 비교 테이블에 메타 5컬럼, 방향성 로직 정확)
2. **M3** ✅: 비교 시트에서 Meta Volcano → `meta_found_in ≥ K` 필터 → Export 동작.
   (헤드리스 검증 완료: 589점 렌더, Fisher↔Stouffer 전환, 임계값 필터 정상)
3. **M4a** ✅: GO 데이터셋 2–3개로 GO Term Comparison → term별 `meta_pvalue_fisher`/`meta_fdr_fisher`
   확인 → 일관 enriched term이 상위에 오는지. (헤드리스 검증 완료: 40 term 결합, FDR≥raw p, 신경 term 상위,
   Meta Volcano term 모드 자동 전환)
4. **M5** ✅: DE 2–3개로 Statistics Filtering → `meta_effect_log2fc`/`meta_i2` 확인 →
   정밀도 가중 통합·방향 엇갈릴 때 I² 상승·`meta_pvalue_re`가 M1과 상관되나 별개인지.
   (헤드리스 검증 완료: 673행, 세포주기 유전자 일관 down, I² 0~44%, 방향 상쇄 시 pooled≈0)
5. **M2** ⬜: human DE + mouse DE 혼합 → Cross-species 체크 → 인간 심볼로 통합, 매핑 실패 경고
6. **M4b** ⬜: Comparison: Statistics 시트에서 meta-DEG를 enrichment 입력으로 → 보존 시그니처 패스웨이 도출
