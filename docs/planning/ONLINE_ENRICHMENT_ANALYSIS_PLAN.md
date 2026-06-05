# On-line Enrichment Analysis Integration Plan

## Executive Summary

현재 CMG-SeqViewer는 DESeq2/limma/EdgeR 등 외부 분석 결과(`final_go_result.xlsx`)를 불러와 검색·필터·시각화에 활용하고, clustering 정도만 on-line 분석으로 제공한다. DEG 리스트와 GO/KEGG 결과가 모두 사전 확정된 상황이라 활용 유연성이 제한적이다.

본 계획은 **gseapy (Enrichr API)** 와 **GOATOOLS** 를 임베딩하여, 사용자가 직접 DEG 리스트를 입력해 GO/KEGG enrichment 분석을 즉석에서 수행할 수 있도록 확장한다.

**우선 지원 species:** Human, Mouse  
**코드 재사용률:** ~75% (기존 StandardColumns, 시각화 파이프라인 재활용)

---

## Background

### 현재 워크플로우의 한계

```
외부 분석 (DESeq2/limma/EdgeR)
        ↓
final_go_result.xlsx (결과 확정)
        ↓
CMG-SeqViewer (불러오기 → 검색/필터/시각화)
```

- DEG 기준(fold-change, FDR threshold)을 바꿔도 재분석 불가
- GO/KEGG 결과가 미리 정해져 있어 탐색적 분석 제한
- 새로운 gene set 시도 시 외부 도구로 재실행 필요

### 목표 워크플로우

```
DE 결과 파일 (gene symbol + log2FC + padj) 로드
        ↓
사용자 직접 DEG 필터 설정 (FC threshold, FDR cutoff, direction)
        ↓
Enrichment Analysis (on-the-fly)
  ├─ GO (BP / CC / MF)   ← GOATOOLS (로컬) 또는 gseapy Enrichr (서버)
  └─ KEGG Pathway        ← gseapy Enrichr API (서버)
        ↓
결과 → 기존 StandardColumns DataFrame으로 변환
        ↓
기존 Bar Chart / Dot Plot / Clustering / Network 다이얼로그 재사용
```

---

## 기술 선택: gseapy vs GOATOOLS

### gseapy.enrichr() — **Enrichr API 방식**

| 항목 | 내용 |
|---|---|
| 계산 위치 | **Enrichr 외부 서버** |
| 인터넷 | **필수** |
| 랩톱 부하 | 거의 없음 (결과 수신만) |
| 지원 데이터베이스 | GO_BP, GO_CC, GO_MF, KEGG, Reactome 등 300+ |
| 데이터 전송 범위 | **Gene symbol 리스트만 전송** (expression 값 미전송) |
| 구현 난이도 | 낮음 |
| 단점 | 인터넷 필수, gene list 외부 전송, rate limit |

### GOATOOLS — **완전 로컬 방식**

| 항목 | 내용 |
|---|---|
| 계산 위치 | **내 랩톱 (로컬)** |
| 인터넷 | 최초 파일 다운로드 시만 필요, 이후 오프라인 |
| 랩톱 부하 | go-basic.obo 로딩 ~1-2초, RAM ~300-500MB |
| 지원 범위 | GO (BP/CC/MF) 전용 (KEGG 미지원) |
| 데이터 전송 | 없음 |
| 구현 난이도 | 중간 (파일 관리, gene ID 매핑 필요) |
| 단점 | KEGG 미지원, 어노테이션 파일 관리 필요 |

### 권장 전략: **gseapy + GOATOOLS 혼용**

```
GO 분석   → GOATOOLS (오프라인, 재현성 보장)
KEGG 분석 → gseapy Enrichr API (인터넷, 구현 단순)
결과 포맷 → 기존 StandardColumns 구조로 통일
```

---

## 필요 파일/의존성

### 추가 패키지
```
gseapy>=1.1.0
goatools>=1.6.0
mygene>=3.2.0          # gene symbol → Entrez ID 매핑
statsmodels>=0.14.0    # GOATOOLS 다중 검정 보정 확장 (이미 있을 수 있음)
```

### GOATOOLS 로컬 데이터 (최초 1회 다운로드 후 캐시)
```
~/.cmg_seqviewer/
  go-basic.obo           # GO DAG 구조 (~8MB)
  gene2go_human.gz       # Human GO 어노테이션 (~8MB)
  gene2go_mouse.gz       # Mouse GO 어노테이션 (~5MB)
```

---

## 구현 계획

### Phase 1 — 기반 구축

- [ ] `EnrichmentAnalyzer` 유틸리티 클래스 작성 (`src/utils/enrichment_analyzer.py`)
  - gseapy Enrichr 호출 wrapper
  - GOATOOLS Fisher's exact test wrapper
  - 결과 → `StandardColumns` DataFrame 변환
- [ ] Gene Symbol → Entrez ID 매핑 모듈 (`src/utils/gene_id_mapper.py`)
  - mygene.info API 또는 로컬 캐시 파일 활용
- [ ] 어노테이션 파일 자동 다운로드/캐시 관리자

### Phase 2 — UI 구현

- [ ] `EnrichmentAnalysisDialog` 다이얼로그 (`src/gui/enrichment_analysis_dialog.py`)
  - DEG 필터 설정 (FC threshold, FDR cutoff, UP/DOWN/BOTH)
  - 분석 방법 선택 (gseapy Enrichr / GOATOOLS)
  - Species 선택 (Human / Mouse)
  - 분석 대상 선택 (GO BP, GO CC, GO MF, KEGG)
  - 진행 상황 표시 (QProgressBar)
- [ ] `EnrichmentWorker` QThread 구현 (`src/workers/`) — 기존 `GOEnrichmentWorker` placeholder 활용
- [ ] 완료 후 결과를 DatasetManager에 자동 로드 → 기존 시각화 다이얼로그 연결

### Phase 3 — 통합 및 검증

- [ ] 기존 `final_go_result.xlsx` 결과와 비교 검증 테스트
- [ ] Background gene set 처리 (DE 파일 전체 유전자 vs 사용자 커스텀)
- [ ] 오프라인 모드 graceful fallback (인터넷 없을 때 gseapy 대신 GOATOOLS로 자동 전환)
- [ ] 결과 Export (Excel / CSV) — 기존 Export 파이프라인 재사용

---

## 데이터 구조 변환 (결과 표준화)

gseapy/GOATOOLS 원본 결과를 기존 StandardColumns로 매핑:

| 원본 컬럼 (gseapy) | StandardColumns | 비고 |
|---|---|---|
| `Term` | `description` | GO Term / KEGG Pathway 이름 |
| `Overlap` | `gene_count` | 분자 (study genes in term) |
| `Adjusted P-value` | `fdr` | |
| `P-value` | `pvalue` | |
| `Genes` | `gene_symbols` | `;` → `/` 구분자 통일 |
| `Overlap` 파싱 | `gene_ratio` | "5/200" 형식 |
| 데이터베이스명 파싱 | `ontology` | BP/CC/MF/KEGG |
| 입력 direction | `direction` | UP/DOWN/TOTAL |
| 데이터베이스명 파싱 | `term_id` | GO:XXXXXXX 추출 |

---

## 고려사항

### 데이터 프라이버시
- gseapy Enrichr: gene symbol 리스트만 외부 전송, raw expression 값 미전송
- 미발표 데이터의 경우 연구실 정책 확인 권고
- 오프라인 완전 지원 필요 시 GOATOOLS 단독 사용 가능

### Background Gene Set
- 통계적 유효성을 위해 전체 발현 유전자 목록(background) 필요
- DE 결과 파일의 전체 유전자를 자동 background로 사용 (기본)
- 사용자 커스텀 background 파일 업로드 옵션 제공

### KEGG Rate Limit
- Enrichr API는 과도한 호출 시 일시적 제한 가능
- 결과 캐싱으로 동일 gene set 재분석 시 API 재호출 방지

---

## 기존 코드 재사용 계획

| 기존 모듈 | 재사용 방식 |
|---|---|
| `StandardColumns` | enrichment 결과 컬럼 표준화 |
| `GOKEGGLoader` | 변환된 결과 DataFrame 로딩 로직 참고 |
| `GOClusteringWorker` | `EnrichmentWorker` 구조 참고 |
| `GOEnrichmentWorker` (stub) | 실제 구현으로 교체 |
| Bar Chart / Dot Plot / Clustering 다이얼로그 | 결과 시각화 그대로 재사용 |
| `DatasetManagerWidget` | 분석 결과 자동 로드 |

---

## 검토 및 보완사항 (Gap Analysis)

> 본 계획을 코드베이스와 대조 검토한 결과. 큰 방향(StandardColumns 재사용, 시각화 다이얼로그 재활용, `GOEnrichmentWorker` stub 교체)은 **정확하고 실현 가능**하나, 배포·통합·통계 정확성 측면에서 아래 항목을 보완해야 한다.

### 🔴 Critical — 반드시 추가/수정

#### G1. PyInstaller 프리징 배포 영향 누락 (가장 큰 구멍)
이 앱은 PyInstaller로 빌드되어 GitHub Actions(`.github/workflows/build.yml`, `v*` 태그 트리거)에서 Windows/macOS 배포물로 나간다. 계획에 이 사실이 없다.
- `rna-seq-viewer.spec`, `cmg-seqviewer-macos.spec` **양쪽** `hiddenimports`에 `gseapy`, `goatools`, `mygene` 추가 필요. 두 패키지는 동적 import·데이터 파일이 많아 `collect_data_files`/`--collect-all` 검토 필요.
- `requirements.txt`, `setup.py` 양쪽 갱신. **`statsmodels`는 현재 미설치**(본문 "이미 있을 수 있음"은 오류), `requests`도 미설치.
- `go-basic.obo`(~8MB)·`gene2go`(수MB)를 번들 포함 vs 런타임 다운로드 결정 필요 → 빌드 크기·CI 영향. **런타임 캐시 다운로드 권장**.

#### G2. 캐시 디렉토리 규칙 충돌
본문의 신규 경로 `~/.cmg_seqviewer/`는 기존 규칙과 충돌:
- `src/utils/data_path_config.py` (frozen 시 실행파일 옆 `data/`)
- `~/.rna_seq_analyzer/column_mappings.json`, `QSettings("RNASeqDataView", ...)`

→ 신규 경로 난립 대신 `data_path_config.py` 확장 또는 한 규칙으로 통일. frozen 환경에서 **쓰기 가능한** 경로(예: `QStandardPaths.AppDataLocation`)인지 검증(프로그램 폴더는 보통 쓰기 불가).

#### G3. DEG 입력 — 기존 RNA 로딩 인프라 재사용 미반영
워크플로우가 "DE 결과 파일 **로드**"로 시작하나, 앱엔 이미:
- `StandardColumns`: `SYMBOL`, `LOG2FC`, `ADJ_PVALUE`, `PVALUE`
- `src/utils/data_loader.py` alias 자동매핑(`padj/fdr/qvalue → adj_pvalue`, `logfc/fc → log2fc`)
- 메모리에 로드된 `DatasetType.RNA_ANALYSIS` 데이터셋

→ 새 파일 로드 대신 **이미 로드된 RNA 데이터셋 + 기존 필터 패널**에서 DEG를 추출해 enrichment로 넘기는 흐름으로 설계. 진짜 재사용 포인트.

#### G4. `_gene_set` 내부 컬럼 생성 누락 (clustering/network 깨짐)
`GOClusteringDialog`/`GONetworkDialog`는 `gene_symbols`가 아니라 **`_gene_set`(Python set)** 컬럼을 요구(`go_kegg_loader._parse_gene_symbols`가 `/` 구분자로 생성). 데이터 변환 표에 이 단계가 없다.
→ gseapy `Genes`(`;` 구분)를 `/`로 통일 후 `_gene_set` set 컬럼까지 생성해야 클러스터링 재사용 성립.

#### G5. `gene_set` 라벨 + 멀티시트 Dataset 구조 미설계
기존 결과는 gene set(예: `UP_BP`, `KEGG_DOWN`)별 시트로 적재되고 `direction`/`ontology`는 그 라벨에서 파싱되며 dataset tree에 시트/탭으로 표시된다. 계획은 컬럼 매핑만 언급하고 **여러 (direction × ontology × DB) 결과를 하나의 `DatasetType.GO_ANALYSIS` Dataset의 시트들로 묶는 규칙**과 `gene_set` 컬럼 채우기를 정의하지 않음.

### 🟠 Important — 통계·매핑 정확성

#### G6. `bg_ratio` / `fold_enrichment` 누락 → Bar/Dot Plot 지표 결손
`GOBarChartDialog`·`GODotPlotDialog`는 `gene_ratio`뿐 아니라 **`fold_enrichment`**(= gene_ratio/bg_ratio)를 지표로 사용. 매핑 표엔 `Overlap → gene_ratio`만 있음.
→ `Overlap`("5/200")에서 gene_ratio, term/배경 크기로 bg_ratio 산출 후 기존 `_compute_fold_enrichment` 재사용. gseapy `Odds Ratio`/`Combined Score` 보존도 검토.

#### G7. Enrichr `term_id` 추출 한계
- GO: term_id가 별도 컬럼이 아니라 `Term` 문자열 괄호 안(`... (GO:0008150)`)에 있음 → 정규식 파싱.
- **KEGG: Enrichr Term에 KEGG ID(hsa#####)가 아예 없음** → KEGG `term_id`는 빔. 본문의 "GO:XXXXXXX 추출"은 KEGG 미적용. 빈 term_id의 다운스트림(클러스터링 키 등) 영향 확인.

#### G8. Enrichr 온라인 + 커스텀 background 비호환 위험
계획 핵심인 "DE 전체 유전자를 background로"는 gseapy `enrichr()`(온라인)에서 무시될 수 있음(전통적으로 Enrichr 고정 background 사용; 커스텀은 로컬 `enrich()`/speedrichr 경로). → 커스텀 background를 반영하려면 GOATOOLS 또는 gseapy 로컬 모드. **버전별 background 지원을 PoC로 검증**, 미지원 시 UI에 해석 주의 명시.

#### G9. GOATOOLS "완전 오프라인" 주장과 mygene 모순
GOATOOLS는 Entrez ID 기반인데 symbol→Entrez에 `mygene`(온라인 API)을 쓰면 "오프라인/재현성" 장점이 사라짐. → 진짜 오프라인엔 NCBI `gene_info`(local) 기반 매핑 캐시 필요.

#### G10. Species(Mouse) 처리 디테일
- Enrichr: mouse는 라이브러리/심볼 casing이 human과 다름(modEnrichr 또는 mouse 전용 gene set) → 라이브러리명 매핑 테이블 필요.
- GOATOOLS: gene2go taxid 필터(human 9606 / mouse 10090) 명시.

### 🟡 Minor — 정합성/완성도

- **G11. 명칭 오류:** `DatasetManagerWidget`는 존재하지 않음. 실제는 `DatasetTreePanel`(`src/gui/dataset_tree_panel.py`) + `main_presenter.load_go_kegg_data()` + main_window Analysis 메뉴(`_on_cluster_go_terms` 패턴, `main_window.py` ~440줄).
- **G12. Worker 시그니처:** 기존 `GOEnrichmentWorker(gene_list, background_genes, organism)`의 `finished`는 단일 DataFrame만 emit. 다중 gene_set/ontology를 한 번에 다루려면 시그널/반환 구조 재설계(또는 gene_set별 순차 실행).
- **G13. 테스트 전략:** pytest/pytest-qt 사용. 네트워크 의존 테스트는 mock 필요(Enrichr/mygene 응답 고정). Phase 3에 mock·픽스처 위치 명시.
- **G14. 에러/빈 결과 UX:** 매핑 0건, enrichment 0건, 타임아웃/rate-limit 처리 미정의. 오프라인 fallback 시 **KEGG는 GOATOOLS 미지원**이라 불가임을 UI에 알려야 함.
- **G15. 재현성 메타데이터:** obo 버전·gene2go 다운로드 일자·Enrichr 라이브러리 버전을 결과에 기록(`Analysis_Info` 시트 관행과 일치).

### ✅ 코드 대조로 확인된 정확한 전제 (수정 불필요)
- `StandardColumns` 재사용 — 모든 컬럼 상수 실재
- `GOEnrichmentWorker`가 stub이며 교체 대상 — `src/workers/go_workers.py:84-136`, dummy 결과 + TODO
- Bar/Dot/Clustering/Network 다이얼로그가 `Dataset`(표준 컬럼) 입력으로 재사용 가능
- gseapy는 gene symbol만 전송(expression 미전송) — 프라이버시 서술 정확
- 결과 캐싱으로 rate-limit 완화

### 권장 다음 단계
1. 위 🔴/🟠 항목을 본문 해당 섹션에 반영(특히 G1 배포, G3 DEG 입력 재사용, G4 `_gene_set`, G8 background).
2. **PoC**: 실제 DEG로 gseapy `enrichr()` 1회 호출 → 반환 컬럼 확인 → StandardColumns 변환(bg_ratio/fold_enrichment/term_id/`_gene_set`)이 기존 `GOBarChartDialog`/`GOClusteringDialog`에서 깨지지 않는지 검증.
3. PoC 후 Phase 1~3 일정 확정.
