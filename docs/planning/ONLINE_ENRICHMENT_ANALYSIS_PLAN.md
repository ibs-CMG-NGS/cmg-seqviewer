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
