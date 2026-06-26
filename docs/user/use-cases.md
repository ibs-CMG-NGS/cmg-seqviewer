# CMG-SeqViewer - 사용 시나리오 및 예제

## 📊 Overview

CMG-SeqViewer는 두 가지 주요 분석 모드를 제공합니다:
1. **Single Dataset Analysis**: 하나의 실험 결과 심층 분석
2. **Multi-Dataset Comparison**: 여러 실험 결과 비교 분석

---

## 🔬 Single Dataset Analysis

### Use Case 1: 기본 DEG (Differentially Expressed Genes) 분석

**시나리오**: 
- 특정 처리(treatment) vs 대조군(control) 비교
- RNA-seq 결과에서 유의미한 유전자 발굴

**워크플로우**:
```
1. 데이터 로딩
   └→ File → Open Dataset → DESeq2/edgeR 결과 엑셀 파일

2. 전체 데이터 확인
   └→ "Whole Dataset" 탭에서 모든 유전자 확인
   └→ Column Display Level: "DE" (gene, baseMean, log2FC, padj)

3. 통계 필터링
   └→ Filter → Statistical
   └→ adj. p-value ≤ 0.05, |log2FC| ≥ 1.0
   └→ → "Filtered by Statistics" 탭 생성

4. 시각화
   └→ Visualization → Volcano Plot
      - Up/down-regulated 유전자 분포 확인
      - 마우스 오버로 유전자명 확인
      - Threshold 조정 (interactive)
   
   └→ Visualization → P-value Histogram
      - p-value 분포 확인 (품질 체크)
   
   └→ Visualization → Heatmap
      - 상위 DEG의 발현 패턴 클러스터링

5. 특정 유전자 그룹 분석
   └→ Filter → Gene List
   └→ 관심 유전자 입력 (pathway, 문헌 기반)
   └→ 💾 Save to File (gene_list.txt)

6. 통계 분석
   └→ Analysis → Fisher's Exact Test
      - 입력한 유전자 리스트가 DEG와 유의미하게 겹치는지 검정
      - P-value, Odds Ratio 확인
      - 📝 Log 자동 저장 (analysis_logs/)
   
   └→ Analysis → GSEA Lite
      - 입력한 유전자들이 up/down 방향으로 편향되는지 확인
      - Mean log2FC, Wilcoxon p-value

7. 결과 내보내기
   └→ File → Export Data
   └→ 필터링된 결과를 엑셀로 저장
```

**실제 예시**:
```
연구 질문: "약물 A 처리 시 염증 관련 유전자의 발현 변화는?"

1. drug_A_vs_control.xlsx 로드
2. Statistical filter: padj ≤ 0.05, |log2FC| ≥ 1.5
   → 1,234개 DEG 발견

3. Volcano plot 확인
   → Up: 687개, Down: 547개

4. 염증 관련 유전자 리스트 입력:
   IL6, TNF, IL1B, NFKB1, STAT3, ... (50개)

5. Fisher's test 결과:
   P-value: 2.3e-8 (highly significant!)
   Odds Ratio: 4.5
   → 염증 유전자가 DEG에 4.5배 많이 포함됨

6. GSEA lite 결과:
   Mean log2FC: -2.3
   Direction: down-regulated
   → 염증 유전자들이 전체적으로 억제됨
   
결론: 약물 A는 염증 반응을 억제하는 것으로 보임
```

---

### Use Case 2: GO Enrichment 결과 탐색

**시나리오**:
- GO 분석 결과에서 유의미한 pathway 발굴
- 특정 biological process의 유전자 확인

**워크플로우**:
```
1. GO 분석 결과 로딩
   └→ File → Open Dataset → GO enrichment 결과

2. FDR 필터링
   └→ Filter → Statistical
   └→ FDR ≤ 0.05
   └→ → 유의미한 GO term만 표시

3. 관심 pathway 검색
   └→ Filter → Gene List (GO term ID나 description 검색)

4. 결과 정렬 및 확인
   └→ 테이블 헤더 클릭으로 FDR 정렬
   └→ Enrichment score 높은 pathway 확인

5. 데이터베이스에 저장 (자주 참고용)
   └→ File → Database Browser → Import Dataset
   └→ Alias: "Drug_A_GO_Inflammation"
   └→ Tags: drug_A, inflammation, pathway
```

**실제 예시**:
```
연구: "면역 관련 pathway가 enriched 되는가?"

1. GO_enrichment_results.xlsx 로드
2. FDR ≤ 0.05 필터링
   → 123개 유의미한 GO term

3. "immune" 키워드로 검색
   → 18개 면역 관련 pathway 발견

4. 상위 5개:
   - GO:0006955 immune response (FDR: 1.2e-15)
   - GO:0002376 immune system process (FDR: 3.4e-12)
   - GO:0006954 inflammatory response (FDR: 5.6e-10)
   ...

5. 자주 참고하므로 database에 저장
```

---

### Use Case 3: Pre-loaded Dataset 활용

**시나리오**:
- 자주 참고하는 대조군 데이터
- 이전 실험 결과와 빠른 비교

**워크플로우**:
```
1. Database에서 로딩
   └→ File → Database Browser
   └→ 검색/필터: "control", "baseline"
   └→ Load Dataset (15-30배 빠른 로딩!)

2. 현재 실험과 비교
   └→ Multi-dataset 탭으로 이동 (아래 참고)

3. 필요시 추가 데이터 import
   └→ Database Browser → Import Dataset
   └→ Parquet 형식으로 자동 변환 저장
```

---

## 🔀 Multi-Dataset Comparison

### Use Case 4: 시계열 실험 비교

**시나리오**:
- 동일 처리의 시간대별 반응 비교
- 0h, 6h, 12h, 24h 시점의 DEG 변화

**워크플로우**:
```
1. 여러 데이터셋 로딩
   └→ File → Open Dataset (반복)
   └→ treatment_0h.xlsx
   └→ treatment_6h.xlsx
   └→ treatment_12h.xlsx
   └→ treatment_24h.xlsx

2. Dataset Manager에서 선택
   └→ Multi-dataset Analysis 탭
   └→ 비교할 데이터셋 선택 (4개)

3. Venn Diagram 생성
   └→ Visualization → Venn Diagram
   └→ Common genes: 시간대에 관계없이 항상 변화
   └→ Unique genes: 특정 시점에만 변화

4. Statistics Comparison
   └→ Analysis → Compare Statistics
   └→ 각 시점의 DEG 개수, 방향성 비교
   └→ 공통/고유 유전자 수 확인

5. 결과 해석
   └→ Early response (6h): 234개 고유 유전자
   └→ Late response (24h): 567개 고유 유전자
   └→ Sustained response: 123개 공통 유전자
```

**실제 예시**:
```
연구: "약물 처리 후 시간대별 반응 패턴"

Venn Diagram 결과:
- Common (모든 시점): 89개
  → 약물의 핵심 타겟 유전자
  → 예: STAT3, IL6, TNF

- Only 6h: 156개
  → 즉각 반응 유전자 (immediate early genes)
  → 예: FOS, JUN, EGR1

- Only 24h: 234개
  → 지연 반응 유전자 (late response)
  → 예: 세포 증식, 분화 관련

결론: 약물은 단계적 반응을 유도 (immediate → sustained → late)
```

---

### Use Case 5: 약물/처리 조건 비교

**시나리오**:
- 서로 다른 약물의 효과 비교
- 동일 약물의 농도별 효과 비교

**워크플로우**:
```
1. 여러 조건 로딩
   └→ drug_A_vs_control.xlsx
   └→ drug_B_vs_control.xlsx
   └→ drug_C_vs_control.xlsx

2. 데이터셋 선택 (Multi-dataset)
   └→ 3개 데이터셋 모두 선택

3. Venn Diagram으로 비교
   └→ Common DEGs: 모든 약물의 공통 타겟
   └→ Drug-specific: 각 약물의 고유 효과

4. 공통 유전자 분석
   └→ Venn 영역 클릭 → 유전자 리스트 확인
   └→ Fisher's test로 pathway enrichment 확인

5. 약물 선택성 평가
   └→ Drug A only: 234개 → 특이적 효과
   └→ Drug A ∩ B: 567개 → 공통 메커니즘
```

**실제 예시**:
```
연구: "3가지 항염증제의 효과 비교"

데이터셋:
- Aspirin_vs_control: 1,234 DEGs
- Ibuprofen_vs_control: 1,456 DEGs
- Celecoxib_vs_control: 987 DEGs

Venn Diagram:
- 3-way overlap: 234개
  → COX2, PTGS2, IL6, TNF, NFKB1
  → 모든 항염증제의 공통 타겟

- Aspirin only: 156개
  → 혈소판 관련 유전자 (항응고 효과)

- Celecoxib only: 89개
  → COX2 선택적 억제 관련

결론: 
- 공통 메커니즘: 염증 매개체 억제
- Aspirin 특이성: 혈소판 기능 조절
- Celecoxib 특이성: COX2 선택성
```

---

### Use Case 6: 세포주/조직 간 비교

**시나리오**:
- 동일 처리의 세포주별 반응 차이
- 조직 특이적 유전자 발현 패턴

**워크플로우**:
```
1. 여러 세포주/조직 데이터 로딩
   └→ treatment_HepG2.xlsx (간암 세포주)
   └→ treatment_A549.xlsx (폐암 세포주)
   └→ treatment_MCF7.xlsx (유방암 세포주)

2. Multi-dataset 비교
   └→ 3개 데이터셋 선택
   └→ Venn Diagram

3. 세포주 특이적 반응 확인
   └→ HepG2 only: 간 대사 관련
   └→ A549 only: 폐 기능 관련
   └→ Common: 암세포 공통 반응

4. 조직 특이성 마커 발굴
   └→ Unique gene list 확인
   └→ GO 분석으로 기능 확인

5. Database에 참고용 저장
   └→ 각 세포주의 기본 특성 데이터
   └→ 향후 실험의 대조군으로 활용
```

---

### Use Case 7: 시퀀싱 플랫폼/파이프라인 비교

**시나리오**:
- DESeq2 vs edgeR 결과 비교
- 다른 분석 파이프라인 일치도 확인

**워크플로우**:
```
1. 동일 샘플의 다른 분석 결과 로딩
   └→ results_DESeq2.xlsx
   └→ results_edgeR.xlsx
   └→ results_limma.xlsx

2. Statistics Comparison
   └→ 각 방법의 DEG 개수 비교
   └→ 공통/차이 유전자 확인

3. Venn Diagram
   └→ 3-way overlap: 신뢰도 높은 DEG
   └→ Method-specific: 각 방법의 민감도

4. 일치도 평가
   └→ 80% 이상 overlap → 신뢰할 만한 결과
   └→ 낮은 overlap → 추가 검증 필요

5. Consensus gene list
   └→ 모든 방법에서 공통인 유전자 선택
   └→ 후속 실험 우선순위 설정
```

---

## 🎯 Advanced Use Cases

### Use Case 8: 데이터베이스 기반 메타 분석

**시나리오**:
- 다양한 실험 조건의 공통 패턴 발굴
- 문헌 기반 가설 검증

**워크플로우**:
```
1. Pre-loaded datasets 활용
   └→ Database Browser에서 태그 검색
   └→ Tag: "inflammation" → 10개 데이터셋

2. 순차적 로딩 및 비교
   └→ 각 데이터셋의 상위 DEG 확인
   └→ 공통 유전자 패턴 파악

3. Gene list 누적
   └→ 여러 실험에서 반복 등장하는 유전자
   └→ 핵심 염증 마커 후보

4. Fisher's test (메타 분석)
   └→ 문헌에서 알려진 유전자 리스트
   └→ 자체 데이터베이스와의 일치도 검증
```

---

### Use Case 9: 필터 조건 최적화

**시나리오**:
- 다양한 threshold 테스트
- 적절한 컷오프 값 결정

**워크플로우**:
```
1. 동일 데이터셋으로 여러 필터링
   └→ padj ≤ 0.01, |log2FC| ≥ 2.0 → 엄격한 기준
   └→ padj ≤ 0.05, |log2FC| ≥ 1.0 → 표준 기준
   └→ padj ≤ 0.1, |log2FC| ≥ 0.5 → 완화된 기준

2. 각 필터의 결과 비교
   └→ DEG 개수 변화
   └→ Volcano plot 패턴

3. P-value histogram 확인
   └→ 균일한 분포 → 좋은 실험
   └→ 0 근처 peak → 많은 DEG

4. 최적 기준 선택
   └→ 너무 엄격 → false negative
   └→ 너무 완화 → false positive
   └→ 균형점 찾기
```

---

## 📝 Typical Workflow Examples

### Example 1: 약물 스크리닝 분석

```
목표: 10개 후보 약물 중 효과적인 약물 선별

1. 10개 데이터셋 로딩 (각 약물 vs 대조군)

2. 빠른 스크리닝
   └→ 각 데이터셋의 DEG 개수 확인
   └→ Top 3 선택 (가장 많은 DEG)

3. Top 3 상세 비교
   └→ Multi-dataset Venn Diagram
   └→ 공통 타겟 확인

4. 문헌 검증
   └→ 알려진 효과적인 약물 마커 리스트
   └→ Fisher's test로 각 약물 평가

5. 최종 후보 선정
   └→ 통계적 유의성 + 공통 타겟
   └→ Drug A 선택 → 후속 실험
```

---

### Example 2: 복잡한 실험 디자인 (2x2 Factorial)

```
실험 디자인:
- Factor 1: Treatment (A vs Control)
- Factor 2: Genotype (WT vs KO)

4개 조건:
1. Control_WT
2. Control_KO (KO effect)
3. Treatment_WT (Treatment effect)
4. Treatment_WT_KO (Interaction)

분석:
1. Treatment effect 확인
   └→ Treatment_WT vs Control_WT
   └→ 약물의 기본 효과

2. Genotype effect 확인
   └→ Control_KO vs Control_WT
   └→ KO 자체의 영향

3. Interaction 확인
   └→ Treatment_KO vs Control_KO
   └→ KO에서 약물 효과 변화

4. Venn Diagram (4-way)
   └→ Common: 모든 조건에서 변화
   └→ Treatment-specific
   └→ Genotype-specific
   └→ Interaction-specific
```

---

## 💡 Tips & Best Practices

### Single Dataset
1. **먼저 Whole Dataset 확인** - 데이터 품질 체크
2. **P-value Histogram** - 실험 품질 평가
3. **적절한 threshold 선택** - 너무 엄격하지도, 완화되지도 않게
4. **Gene list는 저장** - 재현성 확보
5. **Analysis log 활용** - 결과 기록 및 논문 작성 시 참고

### Multi-Dataset
1. **먼저 각 데이터셋 개별 확인** - 품질 이상 없는지 체크
2. **Venn Diagram은 2-4개** - 너무 많으면 해석 어려움
3. **Common genes에 집중** - 재현성 높은 결과
4. **Database 활용** - 자주 비교하는 데이터는 미리 저장
5. **통계 비교 기록** - 각 데이터셋의 특성 문서화

---

## 🔬 연구 단계별 활용

### 1. 탐색 단계 (Exploratory)
- Single dataset: Volcano plot, Heatmap
- 전체적인 패턴 파악
- 흥미로운 유전자 발굴

### 2. 가설 검증 (Hypothesis Testing)
- Gene list filtering
- Fisher's test, GSEA lite
- 특정 pathway 집중 분석

### 3. 비교 분석 (Comparative)
- Multi-dataset Venn diagram
- 조건 간 차이/유사성 확인
- 메타 분석

### 4. 결과 정리 (Reporting)
- Export filtered results
- Analysis logs 수집
- 시각화 저장 (추후 구현 가능)

---

## 📚 Summary

| 분석 유형 | 주요 기능 | 대표 Use Case |
|----------|---------|--------------|
| **Single Dataset** | Filtering, Visualization, Statistical Test | 기본 DEG 분석, GO enrichment 탐색 |
| **Multi-Dataset** | Venn Diagram, Statistics Comparison | 시계열 비교, 약물 비교, 조직 비교 |
| **Database** | Fast Loading, Metadata Search | 메타 분석, 대조군 비교, 참고 데이터 |

**핵심**: 
- Single = 깊이 있는 분석
- Multi = 넓은 시야의 비교
- Database = 빠른 참조와 재현성
