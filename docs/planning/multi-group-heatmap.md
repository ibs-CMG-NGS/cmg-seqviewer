# PLAN: Multi-Group Heatmap & Clustering Feature

**Created**: 2026-04-10  
**Status**: Planning  
**Branch**: master (작업 시작 시 feature branch 생성 권장)

---

## 1. 목표

pairwise DESeq2 결과(2군 비교) 외에, **3군 이상의 time-series / multi-condition 실험**
(예: control / +4h / +6h)에서도 전체 발현 패턴을 heatmap 및 hierarchical clustering으로
시각화할 수 있도록 지원한다.

---

## 2. 전체 워크플로우

```
[R DESeq2 파이프라인]
  LRT omnibus test + VST abundance
        |
        v
  통합 CSV 파일 1개 (multi_group_result.csv)
        |
        v
[CMG-SeqViewer]
  MULTI_GROUP 타입으로 로드
        |
        +-- 통계 필터 (padj < 0.05, baseMean > 10 등)
        +-- Heatmap (Z-score, 계층적 clustering)
        +-- Gene clustering (k-means / hierarchical)
        +-- GO enrichment 연계 (클러스터별)
```

---

## 3. Step 1: R 파이프라인 출력 파일 규격

### 3-1. 생성 방법 (R 코드 예시)

```r
library(DESeq2)
library(dplyr)
library(tibble)

# 1. LRT omnibus test
dds <- DESeqDataSetFromMatrix(countData = counts,
                              colData   = coldata,
                              design    = ~ condition)
dds <- DESeq(dds, test = "LRT", reduced = ~ 1)
res_lrt <- results(dds) %>%
  as.data.frame() %>%
  rownames_to_column("gene_id")

# 2. VST normalized abundance
vst_mat <- assay(vst(dds, blind = FALSE)) %>%
  as.data.frame() %>%
  rownames_to_column("gene_id")

# 3. gene symbol 추가 (선택)
# res_lrt$gene_symbol <- mapIds(org.Mm.eg.db, res_lrt$gene_id, "SYMBOL", "ENSEMBL")

# 4. 통합 후 저장
out <- left_join(res_lrt, vst_mat, by = "gene_id")
write.csv(out, "multi_group_result.csv", row.names = FALSE)
```

### 3-2. 출력 파일 컬럼 구조

| 구분 | 컬럼명 | 설명 |
|------|--------|------|
| ID | `gene_id` | ENSEMBL ID 또는 gene symbol |
| ID (선택) | `gene_symbol` | Human-readable name |
| Omnibus | `baseMean` | 평균 발현량 |
| Omnibus | `stat` | LRT chi-square statistic |
| Omnibus | `pvalue` | raw p-value |
| Omnibus | `padj` | BH-adjusted p-value |
| Abundance | `ctrl_1`, `ctrl_2`, `4h_1`, `4h_2`, ... | VST 또는 normalized count |

**예시**:
```
gene_id,gene_symbol,baseMean,stat,pvalue,padj,ctrl_1,ctrl_2,4h_1,4h_2,6h_1,6h_2
ENSMUSG00000001,Brca1,1234,45.2,1e-8,2e-6,8.1,8.2,9.5,9.4,10.2,10.1
ENSMUSG00000002,Tp53,987,12.3,0.003,0.02,7.5,7.6,7.2,7.1,6.8,6.9
```

### 3-3. 샘플 컬럼 명명 규칙 (권장)

앱에서 자동 감지를 위해 샘플 컬럼명을 일관되게 지정:

- `{group}_{replicate}` 형식 권장: `ctrl_1`, `ctrl_2`, `4h_1`, `4h_2`
- 또는 순수 숫자형 컬럼으로 나머지 통계 컬럼과 구분

앱은 아래 **알려진 통계 컬럼을 제외한 나머지 숫자형 컬럼**을 샘플로 자동 감지:
```
gene_id, gene_symbol, baseMean, stat, pvalue, padj, log2FC, lfcSE
```

---

## 4. Step 2: CMG-SeqViewer 앱 구현 계획

### Phase A: 데이터 타입 & 로더 (MVP)

**A-1. `DatasetType.MULTI_GROUP` 추가**
- 파일: `src/models/data_models.py`
- `DatasetType` enum에 `MULTI_GROUP = "multi_group"` 추가

**A-2. `MultiGroupLoader` 작성**
- 파일: `src/utils/multi_group_loader.py` (신규)
- 기능:
  - CSV/Excel/parquet 로드
  - 통계 컬럼 자동 감지 (`baseMean`, `stat`, `pvalue`, `padj`)
  - 샘플 컬럼 자동 감지 (숫자형 중 통계 컬럼 제외)
  - 샘플 그룹 파싱 (`ctrl_1`, `ctrl_2` → group=`ctrl`)
  - 결과: `Dataset` 객체 + `sample_columns: list[str]` + `sample_groups: dict`

**A-3. 파일 타입 자동 감지 로직 수정**
- 파일: `src/utils/data_loader.py`
- 조건: `padj` 컬럼 있음 + `log2FC` 컬럼 없음 + 샘플 컬럼 3개 이상 → `MULTI_GROUP`

---

### Phase B: 통계 필터 UI

**B-1. 기존 Statistical Filter 패널 확장**
- 파일: `src/gui/filter_panel.py`
- MULTI_GROUP 모드 시 표시:
  - `padj <=` (기본 0.05)
  - `baseMean >=` (기본 10, 저발현 유전자 제거)
  - 필터 적용 → 유의 유전자만 추출

---

### Phase C: Heatmap 시각화

**C-1. `MultiGroupHeatmapDialog` 신규 작성**
- 파일: `src/gui/multi_group_heatmap_dialog.py` (신규)
- 기능:
  - `seaborn.clustermap()` 기반
  - Z-score 정규화 옵션 (row / column / none)
  - 샘플 그룹 annotation bar (상단 color bar)
  - 유전자 수 제한 옵션 (상위 N개, 기본 500)
  - 계층적 clustering 방법 선택 (ward / average / complete)
  - 이미지 저장 (PNG / SVG)

**C-2. 메뉴 연결**
- 파일: `src/gui/main_window.py`
- `Visualization` 메뉴에 `Multi-Group Heatmap` 항목 추가
- MULTI_GROUP 타입일 때만 활성화

---

### Phase D: Gene Clustering (선택적 확장)

- k-means clustering (클러스터 수 K 지정)
- 클러스터별 발현 패턴 line plot (평균 ± SE)
- 클러스터별 GO enrichment 연계 (기존 GO filter/network 활용)
- 결과 컬럼 `gene_cluster` 추가 후 export

---

## 5. 파일 변경 목록 요약

| 파일 | 변경 유형 | 내용 |
|------|----------|------|
| `src/models/data_models.py` | 수정 | `DatasetType.MULTI_GROUP` 추가 |
| `src/utils/multi_group_loader.py` | 신규 | 로더, 샘플 컬럼 감지, 그룹 파싱 |
| `src/utils/data_loader.py` | 수정 | MULTI_GROUP 자동 감지 조건 추가 |
| `src/gui/filter_panel.py` | 수정 | MULTI_GROUP 필터 UI |
| `src/gui/multi_group_heatmap_dialog.py` | 신규 | Heatmap dialog |
| `src/gui/main_window.py` | 수정 | 메뉴 항목 추가, 타입별 활성화 |
| `src/presenters/main_presenter.py` | 수정 | MULTI_GROUP 분기 처리 |

---

## 6. 작업 순서 (권장)

```
[사용자]  R 파이프라인에서 multi_group_result.csv 생성
    |
    v
[사용자]  샘플 파일을 개발자에게 제공
    |
    v
[개발]  Phase A: 로더 구현 + 파일 정상 로드 확인
    |
    v
[개발]  Phase B: 필터 UI (padj, baseMean)
    |
    v
[개발]  Phase C: Heatmap dialog MVP
    |
    v
[개발]  Phase D: Gene clustering (선택)
```

---

## 7. 작업 재개 시 체크리스트

- [ ] `multi_group_result.csv` 샘플 파일 확보
- [ ] 컬럼 구조 확인 (샘플 컬럼명 패턴 파악)
- [ ] `DatasetType.MULTI_GROUP` 추가
- [ ] `MultiGroupLoader` 작성 및 테스트
- [ ] Heatmap dialog MVP 구현
- [ ] 메뉴 연결 및 통합 테스트

---

## 8. 관련 문서

- [PLAN_DATASET_TREE_PANEL.md](PLAN_DATASET_TREE_PANEL.md) — Dataset Tree Panel 구현 계획
- [RECENT_UPDATES.md](RECENT_UPDATES.md) — 릴리즈 노트
