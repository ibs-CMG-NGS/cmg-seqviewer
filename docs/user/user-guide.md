# CMG-SeqViewer 사용자 매뉴얼 (User Guide)

> 📖 CMG-SeqViewer의 모든 기능을 상세히 설명하는 종합 가이드

## 목차

1. [개요](#개요)
2. [인터페이스 구성](#인터페이스-구성)
3. [데이터 관리](#데이터-관리)
4. [필터링](#필터링)
5. [시각화](#시각화)
6. [통계 분석](#통계-분석)
7. [GO/KEGG 분석](#gokegg-분석)
8. [비교 분석](#비교-분석)
9. [내보내기](#내보내기)
10. [고급 기능](#고급-기능)
11. [바로가기 키](#바로가기-키)

---

## 개요

### CMG-SeqViewer란?

CMG-SeqViewer는 RNA-seq 분석 결과를 시각화하고 탐색하기 위한 데스크톱 애플리케이션입니다.

**주요 특징**:
- 🖥️ Excel 같은 친숙한 인터페이스
- 📊 다양한 시각화 (Volcano, Heatmap, Network 등)
- 🔍 강력한 필터링 기능
- 📈 통계 분석 도구
- 🧬 GO/KEGG 경로 분석
- 💾 다중 포맷 내보내기

**사용자 대상**:
- 생물정보학 연구자
- 분자생물학자
- 데이터 분석가
- 대학원생 및 교수진

---

## 인터페이스 구성

### 메인 윈도우

```
┌────────────────────────────────────────────────────┐
│ 메뉴바: File | Edit | View | Analysis | Help       │
├─────────────┬──────────────────────────────────────┤
│             │  탭 1   탭 2   탭 3   ...            │
│  Filter     ├──────────────────────────────────────┤
│  Panel      │                                      │
│             │         데이터 테이블                 │
│  - 필터설정  │                                      │
│  - 유전자   │                                      │
│    리스트   │                                      │
│             │                                      │
├─────────────┴──────────────────────────────────────┤
│  로그 터미널: [실시간 로그 메시지]                  │
└────────────────────────────────────────────────────┘
```

### 주요 구성 요소

#### 1. 메뉴바

**File**:
- Import Dataset - 데이터 로드
- Export Current Tab - 현재 탭 내보내기
- Recent Files - 최근 파일 (최대 10개)
- Exit - 종료

**Edit**:
- Copy Selection - 선택 영역 복사
- Select All - 전체 선택

**View**:
- Toggle Filter Panel - 필터 패널 토글
- Toggle Dataset Manager - 데이터셋 관리자 토글
- Refresh - 화면 새로고침

**Analysis**:
- Fisher's Exact Test - 유전자 리스트 enrichment
- GSEA Lite - Gene set enrichment
- Compare Datasets - 다중 데이터셋 비교

**Help**:
- Documentation (F1) - 도움말
- About - 버전 정보

#### 2. Filter Panel (왼쪽)

**필터 설정**:
- Adj.P-Value Threshold: 유의성 임계값
- Log2FC Threshold: Fold change 임계값
- Regulation Direction: Up/Down/Both

**유전자 리스트**:
- 텍스트 영역: 유전자 ID/symbol 입력
- 한 줄에 하나씩
- 공백 또는 쉼표로 구분

**버튼**:
- Apply Filter: 필터 적용
- Reset: 필터 초기화

#### 3. 탭 인터페이스 (중앙)

**탭 종류**:
- **원본 탭**: 로드된 데이터
- **Filtered 탭**: 필터링 결과
- **Comparison 탭**: 비교 결과

**탭 이름 형식**:
- `DatasetName` - 원본
- `DatasetName:Filtered` - 1차 필터링
- `DatasetName:Filtered:Filtered` - 2차 필터링

**탭 작업**:
- 클릭: 탭 전환
- 우클릭: 컨텍스트 메뉴 (Export, Close)
- 더블클릭: (작동 없음)

#### 4. Dataset Manager (우측, 선택사항)

**기능**:
- 로드된 모든 데이터셋 목록
- 클릭으로 탭 전환
- 더블클릭으로 이름 변경
- 우클릭으로 삭제

#### 5. 로그 터미널 (하단)

**표시 내용**:
- 데이터 로드 상태
- 필터링 결과 통계
- 시각화 생성 완료
- 오류 및 경고

**크기**: 고정 200-250px

---

## 데이터 관리

### 데이터 임포트

#### 지원 형식

**Excel 파일**:
- `.xlsx` (Excel 2007+)
- `.xls` (Excel 97-2003)

**필수 컬럼**:
- Gene ID (gene_id, gene_name, symbol, ensembl_id 등)
- Log2 Fold Change (log2FC, logFC, log2FoldChange 등)
- Adjusted P-value (adj.p.value, padj, FDR, qvalue 등)

**선택 컬럼**:
- P-value (p.value, pvalue)
- Base Mean (baseMean, AveExpr)
- Description (description, gene_name)

#### Import 다이얼로그

**1단계: 파일 선택**
```
File → Import Dataset → Excel 파일 선택
```

**2단계: 설정**

**Dataset Name**:
- 데이터셋 이름 입력
- 탭 제목으로 사용
- 나중에 변경 가능

**Data Type**:
- **Differential Expression**: RNA-seq DE 결과
- **GO/KEGG Enrichment**: GO/KEGG 분석 결과

**Sheet Selection**:
- Excel 시트 선택
- 미리보기로 확인

**Column Mapping**:
- 자동 감지 (30+ 컬럼명 패턴)
- 수동 선택 가능
- Preview 섹션에서 확인

**3단계: Import**
- **Import** 버튼 클릭
- 진행 상태 표시
- 완료 후 새 탭 생성

#### 자동 컬럼 매핑

**Gene ID 패턴**:
```
gene_id, gene_name, symbol, ensembl_id, 
gene, ID, id, Symbol, SYMBOL, GeneID
```

**Log2FC 패턴**:
```
log2FC, logFC, log2FoldChange, log2_fold_change,
log2fc, logfc, LFC, lfc
```

**Adj.P-Value 패턴**:
```
adj.p.value, padj, FDR, qvalue, q.value,
adj_pval, adjpvalue, adjusted_pvalue
```

자세한 내용: [컬럼 매핑 가이드](COLUMN_MAPPING_GUIDE.md)

### 데이터셋 관리

#### 이름 변경

**방법 1: Dataset Manager**
1. Dataset Manager에서 데이터셋 더블클릭
2. 새 이름 입력
3. Enter 키 또는 외부 클릭

**방법 2: 탭 우클릭** (작성 예정)

**효과**:
- 모든 탭 제목 자동 업데이트
- `OldName:Filtered` → `NewName:Filtered`

#### 데이터셋 삭제

**방법**:
1. Dataset Manager에서 데이터셋 우클릭
2. "Remove Dataset" 선택
3. 확인 다이얼로그 → Yes

**효과**:
- 데이터셋 및 관련 모든 탭 닫힘
- 메모리에서 제거

#### 외부 데이터 폴더 (v1.2.0+)

**위치**: 실행 파일 옆 `data/` 폴더

**구조**:
```
CMG-SeqViewer.exe (또는 .app)
data/
├── metadata.json       # 데이터셋 메타데이터
└── datasets/
    ├── dataset1.parquet
    ├── dataset2.parquet
    └── ...
```

**기능**:
- Database Browser → **Open Data Folder** 버튼
- 탐색기/Finder로 폴더 열림
- 파일 추가 후 **Refresh** 버튼
- metadata.json 자동 리로드

**우선순위**:
1. `data/` (외부 폴더) - 우선
2. `database/` (내장 폴더) - 백업

---

## 필터링

### 기본 필터

#### Adj.P-Value Threshold

**의미**: 통계적 유의성 임계값

**설정**:
- 슬라이더: 0.001 ~ 0.1
- 텍스트 입력: 임의 값
- 기본값: 0.05

**효과**: adj.p < threshold인 유전자만 선택

**예시**:
```
adj.p.value < 0.05  → 유의미한 유전자
adj.p.value < 0.01  → 매우 유의미한 유전자
```

#### Log2FC Threshold

**의미**: Fold change 크기 임계값

**설정**:
- 슬라이더: 0 ~ 3
- 텍스트 입력: 임의 값
- 기본값: 1

**효과**: |log2FC| > threshold인 유전자만 선택

**예시**:
```
|log2FC| > 1  → 2배 이상 변화
|log2FC| > 2  → 4배 이상 변화
|log2FC| > 3  → 8배 이상 변화
```

#### Regulation Direction

**옵션**:
- **Both**: Up + Down (모두)
- **Up-regulated only**: log2FC > 0
- **Down-regulated only**: log2FC < 0

**조합 효과**:
```
Both + |log2FC| > 1 + adj.p < 0.05
→ 2배 이상 증가 OR 감소하고 유의미한 유전자

Up-regulated + log2FC > 1 + adj.p < 0.05
→ 2배 이상 증가하고 유의미한 유전자만
```

### Gene List 필터

#### 사용법

**1단계**: Filter Panel의 텍스트 영역에 유전자 입력

**형식**:
```
# 한 줄에 하나
GAPDH
TP53
ACTB

# 또는 쉼표 구분
GAPDH, TP53, ACTB

# 또는 공백 구분
GAPDH TP53 ACTB
```

**2단계**: "Apply Filter" 클릭

**결과**: 입력한 유전자만 표시

#### 고급 사용

**파일에서 복사**:
1. 텍스트 파일에 유전자 리스트 준비
2. 전체 선택 (Ctrl+A) → 복사 (Ctrl+C)
3. Filter Panel에 붙여넣기 (Ctrl+V)

**Excel에서 복사**:
1. Excel에서 유전자 컬럼 선택
2. 복사 (Ctrl+C)
3. Filter Panel에 붙여넣기
4. (탭 문자 자동 제거됨)

**대소문자**:
- 대소문자 구분 안함
- `gapdh` = `GAPDH` = `Gapdh`

**매칭**:
- Gene ID 또는 Symbol 모두 검색
- 부분 매칭 지원 안함 (정확히 일치해야 함)

### Re-filtering (연속 필터링)

#### 개념

필터링된 결과를 다시 필터링

**예시 워크플로우**:
```
1. 원본 (10,000 유전자)
   ↓ adj.p < 0.05
2. Filtered (1,000 유전자)
   ↓ |log2FC| > 2
3. Filtered:Filtered (200 유전자)
```

#### 사용법

**1단계**: 첫 번째 필터 적용
```
Filter Panel → adj.p < 0.05 → Apply Filter
→ "Dataset:Filtered" 탭 생성
```

**2단계**: Filtered 탭 선택

**3단계**: 두 번째 필터 설정
```
Filter Panel → |log2FC| > 2 → Apply Filter
→ "Dataset:Filtered:Filtered" 탭 생성
```

**4단계**: 반복 가능

#### 주의사항

- 탭 이름이 길어질 수 있음
- 원본 데이터는 변경되지 않음
- 각 필터링 단계는 독립적

---

## 시각화

### Volcano Plot

#### 개요

**목적**: 전체 DE 결과를 한눈에 파악

**X축**: log2 Fold Change  
**Y축**: -log10(adj.p.value)

**색상**:
- 🔴 빨간색: Significant Up (adj.p < 0.05, log2FC > 1)
- 🔵 파란색: Significant Down (adj.p < 0.05, log2FC < -1)
- ⚫ 회색: Not significant

#### 생성 방법

**메뉴**: Visualization → Volcano Plot

**설정**:
- **Point size**: 점 크기 (10-200, 기본 50)
- **Alpha**: 투명도 (0-1, 기본 0.6)
- **Color scheme**: 색상 테마
- **Thresholds**: 임계선 표시
  - Adj.P < 0.05 (수평선)
  - |log2FC| > 1 (수직선)

**Generate** 버튼 → 새 창에 Plot 표시

#### 상호작용

**마우스 오버**:
- 유전자 이름 표시
- 좌표 (log2FC, -log10(p)) 표시

**클릭**: (현재 기능 없음)

**툴바**:
- 🏠 Home: 초기 뷰로 복귀
- ← → : 이전/다음 뷰
- ☰ Pan: 이동 모드
- 🔍 Zoom: 확대/축소 모드
- 💾 Save: PNG/SVG로 저장

#### 자동 스케일 (v1.0.11+)

**기능**: X, Y축 자동 조정

**효과**:
- 이상치 제거 (99 percentile)
- 데이터 중심 확대
- 가독성 향상

**비활성화**: Settings → Disable auto-scale (작성 예정)

### Heatmap

#### 개요

**목적**: 발현 패턴 클러스터링 및 시각화

**행**: 유전자  
**열**: 샘플 (있는 경우) 또는 단일 컬럼

**색상**: 발현 수준 (보통 log2FC)

#### 생성 방법

**메뉴**: Visualization → Heatmap

**설정**:

**Clustering**:
- **Method**: average, complete, single, ward
- **Metric**: euclidean, correlation, manhattan

**Color**:
- **Colormap**: RdBu_r, viridis, coolwarm, etc.
- **Center**: 0 (log2FC의 경우)

**Size**:
- **Figure width**: 인치
- **Figure height**: 인치

**Generate** → Heatmap 창 표시

#### 해석

**Dendrogram** (나무 그림):
- 유전자 간 유사도
- 가까운 가지 = 유사한 패턴

**Color**:
- 빨간색: 높은 발현 (Up)
- 파란색: 낮은 발현 (Down)
- 흰색: 중간 (No change)

**클러스터**:
- 같은 색상 그룹 = 비슷한 조절

### P-adj Histogram

#### 개요

**목적**: P-value 분포 확인

**X축**: adj.p.value bins  
**Y축**: 유전자 개수

#### 생성 방법

**메뉴**: Visualization → P-adj Histogram

**설정**:
- **Bins**: 구간 개수 (10-100, 기본 50)
- **Range**: 0-1 (고정)
- **Threshold line**: 0.05 (빨간 수직선)

#### 해석

**정상 분포**:
```
많음 ┤     
     │ ▁▂▃▅████▅▃▂▁   ← 왼쪽에 집중 (많은 유의미한 유전자)
적음 └─────────────→ adj.p
     0   0.05      1
```

**비정상 분포**:
```
많음 ┤ █████▃▂▁      ← 거의 모든 유전자가 유의미 (의심스러움)
     │
적음 └─────────────→ adj.p
```

### Venn Diagram

#### 개요

**목적**: 데이터셋 간 교집합 시각화

**지원**: 2-3 데이터셋 (최대 3개)

#### 생성 방법

**메뉴**: Analysis → Compare Datasets

**설정**:
- **Datasets**: 2-3개 선택
- **Comparison Mode**: Gene List
- **Operation**: Intersection (기본)

**Generate** → Venn Diagram 표시

#### 해석

**영역**:
- **A only**: A에만 있는 유전자
- **B only**: B에만 있는 유전자
- **A ∩ B**: 공통 유전자
- **A ∩ B ∩ C**: 세 개 모두 공통

**숫자**: 각 영역의 유전자 개수

---

## 통계 분석

### Fisher's Exact Test

#### 개요

**목적**: 유전자 리스트가 특정 gene set에 enrichment 되었는지 검증

**원리**: 2x2 contingency table

```
                In Gene Set    Not in Gene Set
In List              a               b
Not in List          c               d
```

**p-value**: 우연히 이렇게 많이 겹칠 확률

#### 사용법

**메뉴**: Analysis → Fisher's Exact Test

**입력**:

**Gene List**:
- Filter Panel에 유전자 입력
- 또는 Filtered 탭 사용

**Gene Set**:
- GMT 파일 (.gmt)
- 또는 내장 gene sets (작성 예정)

**Background**:
- 전체 유전자 우주
- 기본: 현재 데이터셋

**결과**:

**테이블**:
| Gene Set | P-value | Odds Ratio | Overlap |
|----------|---------|------------|---------|
| Pathway1 | 0.001   | 5.2        | 15/50   |
| Pathway2 | 0.05    | 2.1        | 8/30    |

**해석**:
- P-value < 0.05: 유의미한 enrichment
- Odds Ratio > 1: Over-representation
- Overlap: 겹치는 유전자 개수 / Gene Set 크기

### GSEA Lite

#### 개요

**목적**: Gene Set Enrichment Analysis (간소화 버전)

**특징**:
- Directionality 고려 (Up/Down)
- Pre-ranked GSEA
- 빠른 계산

#### 사용법

**메뉴**: Analysis → GSEA Lite

**입력**:

**Ranking Metric**:
- log2FC (기본)
- -log10(p) * sign(log2FC)
- Custom

**Gene Sets**:
- GMT 파일
- MSigDB collections (작성 예정)

**Parameters**:
- **Min size**: 최소 gene set 크기 (기본 15)
- **Max size**: 최대 gene set 크기 (기본 500)
- **Permutations**: (사용 안함 - pre-ranked)

**결과**:

**Enrichment Plot**:
- Running enrichment score
- Gene set 위치 표시

**테이블**:
| Gene Set | NES | P-value | FDR |
|----------|-----|---------|-----|
| Set1     | 2.1 | 0.001   | 0.01|
| Set2     |-1.8 | 0.01    | 0.05|

**해석**:
- NES > 0: Up-regulated enrichment
- NES < 0: Down-regulated enrichment
- FDR < 0.25: 유의미한 enrichment

---

## GO/KEGG 분석

### 데이터 로드

#### GO/KEGG 결과 형식

**필수 컬럼**:
- Term/Pathway ID (GO:0008150, hsa04110)
- Description (biological process, cell cycle)
- P-value 또는 FDR
- Gene Ratio (10/50) 또는 Count
- Genes (GAPDH/TP53/ACTB)

**예시 (GO)**:
| GO_ID      | Description      | P.adjust | GeneRatio | Genes         |
|------------|------------------|----------|-----------|---------------|
| GO:0008150 | cell cycle       | 0.001    | 15/100    | TP53/CDK1/... |

**예시 (KEGG)**:
| KEGG_ID | Description | pvalue | Count | Genes         |
|---------|-------------|--------|-------|---------------|
| hsa04110| Cell cycle  | 0.001  | 15    | TP53/CDK1/... |

#### Import

**방법**: File → Import Dataset

**Data Type**: **GO/KEGG Enrichment** 선택

**Column Mapping**:
- Term ID → GO_ID 또는 KEGG_ID
- Description → Description
- P-value → P.adjust 또는 pvalue
- Gene Ratio → GeneRatio 또는 Count
- Genes → Genes (선택사항)

### Clustering

#### 개요

**목적**: 유사한 GO/KEGG term을 그룹화

**방법**:
- **Jaccard Similarity**: 유전자 겹침 기반
- **Kappa Statistic**: 통계적 상관관계

**결과**: Cluster ID 컬럼 추가

#### Jaccard Similarity

**공식**:
```
J(A, B) = |A ∩ B| / |A ∪ B|

예시:
Term A genes: {TP53, CDK1, GAPDH}
Term B genes: {TP53, CDK1, ACTB}

A ∩ B = {TP53, CDK1} → 2개
A ∪ B = {TP53, CDK1, GAPDH, ACTB} → 4개

J(A, B) = 2/4 = 0.5
```

**임계값**: 0.4 (기본)

**의미**:
- J > 0.4: 비슷한 term (같은 클러스터)
- J < 0.4: 다른 term (다른 클러스터)

#### Kappa Statistic

**목적**: 우연을 고려한 term 간 일치도

**공식**: (복잡 - 통계 패키지 사용)

**임계값**: 0.3 (기본)

**장점**: Jaccard보다 통계적으로 엄격

#### Clustering 실행

**메뉴**: GO/KEGG → Clustering

**설정**:

**Method**:
- Jaccard Similarity (권장)
- Kappa Statistic

**Threshold**:
- Jaccard: 0.3-0.6 (기본 0.4)
- Kappa: 0.2-0.5 (기본 0.3)

**Linkage**: (Hierarchical clustering)
- average (권장)
- complete
- single
- ward

**Filters**:
- **Min cluster size**: 최소 클러스터 크기 (기본 2)
- **Max cluster size**: 최대 클러스터 크기 (기본 50)
- **Include singletons**: 단독 term 포함 여부

**Generate** → Clustered 결과 탭 생성

#### 결과

**새 컬럼**:
- `cluster_id`: 클러스터 번호 (0, 1, 2, ...)
- `cluster_representative`: 대표 term (가장 유의미한 것)

**예시**:
| GO_ID      | Description      | cluster_id | cluster_representative |
|------------|------------------|------------|------------------------|
| GO:0007049 | cell cycle       | 0          | TRUE                   |
| GO:0051726 | cell cycle regulation | 0     | FALSE                  |
| GO:0008283 | cell proliferation | 1        | TRUE                   |

### Visualizations

#### Dot Plot

**목적**: GO/KEGG term 비교 시각화

**X축**: Gene Ratio (10/50 = 0.2)  
**Y축**: GO/KEGG terms  
**점 크기**: Gene count  
**점 색상**: P-value 또는 FDR

**메뉴**: GO/KEGG → Dot Plot

**설정**:
- **Top N terms**: 표시할 term 개수 (10-50)
- **Color by**: P-value 또는 FDR
- **Sort by**: P-value 또는 Gene Ratio

#### Bar Chart

**목적**: Top enriched terms 시각화

**X축**: -log10(P-value) 또는 Gene count  
**Y축**: GO/KEGG terms

**메뉴**: GO/KEGG → Bar Chart

**설정**:
- **Top N terms**: 10-50
- **X-axis metric**: P-value 또는 Count
- **Color by**: P-value gradient

#### Network Visualization

**목적**: Cluster 기반 네트워크 시각화

**노드**: GO/KEGG terms  
**엣지**: Similarity (Jaccard 또는 Kappa)  
**색상**: Cluster ID  
**Convex Hull**: 클러스터 경계

**메뉴**: GO/KEGG → Network Visualization

**요구사항**: Clustering 먼저 실행

**설정**:

**Layout**:
- spring (기본)
- circular
- kamada_kawai

**Node**:
- **Size**: 10-500 (기본 100)
- **Label size**: 8-16 (기본 10)

**Edge**:
- **Alpha**: 0-1 (기본 0.3)
- **Min similarity**: 표시할 최소 similarity

**Cluster Colors**:
- 자동 할당 (tab10, tab20)
- Convex hull 표시

**Generate** → Network 창 표시

**상호작용**:
- **마우스 오버**: Term 정보 툴팁
- **클릭**: (현재 기능 없음)
- **Pan/Zoom**: matplotlib 툴바

### 컨텍스트 메뉴 (v1.2.0+)

#### Gene Annotation

**트리거**: 데이터 테이블에서 Gene ID/Symbol 컬럼 우클릭

**메뉴**:
- **NCBI Gene**: https://www.ncbi.nlm.nih.gov/gene/?term=GENE
- **GeneCards**: https://www.genecards.org/cgi-bin/carddisp.pl?gene=GENE
- **Ensembl**: https://www.ensembl.org/Multi/Search/Results?q=GENE
- **UniProt**: https://www.uniprot.org/uniprotkb?query=GENE
- **Google Scholar**: https://scholar.google.com/scholar?q=GENE

**효과**: 기본 브라우저에서 해당 페이지 열림

#### GO Annotation

**트리거**: GO 결과에서 GO_ID 컬럼 우클릭

**자동 ID 추출**: `GO:0008150` 형식 인식

**메뉴**:
- **QuickGO**: https://www.ebi.ac.uk/QuickGO/term/GO:0008150
- **AmiGO**: http://amigo.geneontology.org/amigo/term/GO:0008150
- **Gene Ontology**: http://geneontology.org/GO:0008150
- **NCBI**: https://www.ncbi.nlm.nih.gov/gene?term=GO:0008150

#### KEGG Annotation

**트리거**: KEGG 결과에서 KEGG_ID 컬럼 우클릭

**자동 ID 추출**: `hsa04110` 또는 `path:hsa04110` 형식 인식

**메뉴**:
- **KEGG Pathway**: https://www.genome.jp/pathway/hsa04110
- **Reactome**: https://reactome.org/content/query?q=hsa04110
- **WikiPathways**: https://www.wikipathways.org/index.php?query=hsa04110

---

## 비교 분석

### Multi-dataset Comparison

#### 개요

**목적**: 2-5개 데이터셋 동시 비교

**Comparison Modes**:
- **Gene List**: 유전자 리스트 교집합/합집합
- **Statistics**: 통계값 비교

#### Gene List Mode

**메뉴**: Analysis → Compare Datasets

**설정**:

**Datasets**: 2-5개 선택 (체크박스)

**Operation**:
- **Intersection** (교집합): A ∩ B
- **Union** (합집합): A ∪ B

**Filter**:
- 각 데이터셋에 필터 적용 여부
- "Use filtered data" 체크박스

**Generate** → Comparison 결과 탭 + Venn Diagram

**결과 탭 컬럼**:
- gene_id
- Dataset1_log2FC
- Dataset1_adj.p
- Dataset2_log2FC
- Dataset2_adj.p
- ...

#### Statistics Mode

**목적**: 통계값 직접 비교 및 시각화

**설정**:

**Comparison Metric**:
- Pearson correlation
- Spearman correlation
- Fold change concordance

**Visualization**:
- Scatter plot (2 datasets)
- Dot plot (3+ datasets)
- Heatmap (all datasets)

**Generate** → Scatter plot 또는 Heatmap

**Scatter Plot** (2 datasets):
- X축: Dataset A log2FC
- Y축: Dataset B log2FC
- 대각선: 완벽한 일치
- R² 값 표시

#### Venn Diagram (2-3 datasets)

**자동 생성**: Gene List Mode에서

**영역 클릭**: (작성 예정)
- 해당 영역 유전자 리스트 표시
- 새 탭으로 Export 가능

**Export**: Venn Diagram 이미지 저장 (PNG, SVG)

#### UpSet Plot (4-5 datasets)

**사용**: 4개 이상 데이터셋

**목적**: Venn Diagram 대안 (더 명확)

**구조**:
- 하단: 데이터셋 조합 매트릭스
- 상단: 각 조합의 유전자 개수 (bar chart)

**해석**:
```
●●○○○  ← Dataset A, B만 공통: 50개
●○●○○  ← Dataset A, C만 공통: 30개
●●●○○  ← Dataset A, B, C 공통: 100개
```

---

## 내보내기

### 현재 탭 Export

#### 지원 형식

**Excel (.xlsx)**:
- 권장 형식
- 모든 컬럼 보존
- 포맷팅 유지

**CSV (.csv)**:
- 범용 텍스트 형식
- 쉼표 구분
- 다른 도구와 호환성 좋음

**TSV (.tsv)**:
- 탭 구분 텍스트
- Unix 도구에 적합

#### Export 방법

**메뉴**: File → Export Current Tab

**또는**: 탭 우클릭 → Export

**다이얼로그**:
1. 저장 위치 선택
2. 파일 이름 입력
3. 형식 선택 (xlsx/csv/tsv)
4. **Save** 버튼

**결과**: 파일 생성 완료 메시지

#### Export 내용

**포함**:
- 현재 탭의 모든 행
- 모든 컬럼
- 정렬 상태 유지

**미포함**:
- 다른 탭 데이터
- 시각화 이미지 (별도 저장)

### 시각화 Export

#### 이미지 저장

**방법**: Matplotlib 툴바 → 💾 Save 아이콘

**형식**:
- **PNG**: 래스터 이미지 (기본)
- **SVG**: 벡터 이미지 (권장 - 편집 가능)
- **PDF**: 문서용
- **EPS**: 출판용

**설정**:
- **DPI**: 해상도 (72-600, 기본 300)
- **Transparent**: 배경 투명

#### SVG 편집

**도구**:
- Inkscape (무료)
- Adobe Illustrator
- CorelDRAW

**편집 가능 요소**:
- 텍스트 (폰트, 크기, 색상)
- 색상 (점, 선, 배경)
- 축 범위
- 레이아웃

---

## 고급 기능

### Database Browser (v1.2.0+)

#### 기능

**위치**: Database → Browse Database (메뉴)

**표시**:
- 모든 로드 가능한 데이터셋 목록
- 메타데이터 (이름, 날짜, 크기)
- 소스 (data/ 또는 database/)

**작업**:
- **Load**: 데이터셋 로드
- **Refresh**: metadata.json 리로드
- **Open Data Folder**: 탐색기/Finder로 data/ 폴더 열기

#### 외부 데이터 추가

**1단계**: Open Data Folder 클릭

**2단계**: `datasets/` 폴더에 parquet 파일 복사

**3단계**: `metadata.json` 편집

```json
{
  "datasets": [
    {
      "id": "new_dataset",
      "name": "New Dataset",
      "file_path": "datasets/new_dataset.parquet",
      "data_type": "DE",
      "created_at": "2026-03-01T12:00:00",
      "description": "Description here"
    }
  ]
}
```

**4단계**: Database Browser → Refresh

**5단계**: 새 데이터셋 로드

### 설정 (작성 예정)

#### 현재 구현 안됨

향후 버전에서:
- 필터 프리셋 저장
- 색상 테마 커스터마이징
- 기본값 설정
- 바로가기 키 변경

### 플러그인 시스템 (계획)

**v2.1.0 이후**:
- 사용자 정의 분석 모듈
- Python 스크립트 실행
- R 통합
- Custom visualizations

---

## 바로가기 키

### 전역

| 키 | 기능 |
|----|------|
| `Ctrl+O` | Import Dataset |
| `Ctrl+S` | Export Current Tab |
| `Ctrl+W` | 현재 탭 닫기 |
| `Ctrl+Tab` | 다음 탭 |
| `Ctrl+Shift+Tab` | 이전 탭 |
| `F1` | 도움말 |
| `F5` | Refresh |
| `Ctrl+Q` | 종료 |

### 테이블

| 키 | 기능 |
|----|------|
| `Ctrl+A` | 전체 선택 |
| `Ctrl+C` | 복사 |
| `Ctrl+F` | 검색 (작성 예정) |
| `Up/Down` | 행 이동 |
| `Page Up/Down` | 페이지 스크롤 |

### 필터 패널

| 키 | 기능 |
|----|------|
| `Enter` | Apply Filter |
| `Esc` | Reset Filter |

---

## 문제 해결

일반적인 문제는 [문제 해결 가이드](troubleshooting.md)를 참조하세요. (작성 예정)

---

## 추가 리소스

- [빠른 시작 가이드](quick-start.md) - 5분 튜토리얼
- [설치 가이드](installation.md) - 설치 및 첫 실행
- [컬럼 매핑 가이드](COLUMN_MAPPING_GUIDE.md) - 데이터 임포트
- [FAQ](faq.md) - 자주 묻는 질문 (작성 예정)
- [GitHub Issues](https://github.com/ibs-CMG-NGS/cmg-seqviewer/issues)

---

**마지막 업데이트**: 2026-03-01  
**버전**: v1.2.0
