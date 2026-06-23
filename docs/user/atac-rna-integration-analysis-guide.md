# ATAC-seq 단독 분석 & RNA-ATAC 통합 분석 가이드

이 문서는 CMG-SeqViewer가 지원하는 ATAC-seq 관련 분석 기능을 시나리오별로 정리한다. 각 시나리오마다 **① 분석의 목적, ② 사용 알고리즘/통계, ③ 입력 데이터, ④ 출력 데이터, ⑤ 결과 해석, ⑥ CMG-SeqViewer 시각화 연결**의 순서로 설명한다. ATAC-seq나 다중오믹스 통합 분석에 익숙하지 않은 연구자도 따라갈 수 있도록 배경 설명을 포함했다.

---

## 0. 전체 지도

```
ATAC-seq 원본 데이터 (peak calling 이후)
        │
        ▼
┌───────────────────────────────────────────────┐
│ Part A. ATAC-seq 단독 분석 (Standalone)         │
│                                                 │
│  A1. Differential Accessibility (DA) Peak 분석  │  ← 기반 데이터, 모든 분석의 시작점
│  A2. Genomic Annotation 분포                    │  ← peak이 어디에 위치하는가
│  A3. TSS Distance 분포                          │  ← promoter-proximal 정도
│  A4. MA Plot                                    │  ← 발현량(accessibility) vs 변화량
│  A5. TF Motif Enrichment (HOMER/AME)            │  ← 어떤 TF 모티프가 풍부한가
│  A6. TF Footprinting (TOBIAS)                   │  ← 그 모티프에 실제 결합 흔적이 있는가
│  A7. chromVAR Differential TF Activity          │  ← 샘플별 TF 활성 추정
│  A8. Multi-Condition DA Peak Overlap            │  ← 조건 간 peak이 얼마나 겹치는가
└───────────────────────────────────────────────┘
        │
        ▼ (RNA-seq DE 결과와 결합)
┌───────────────────────────────────────────────┐
│ Part B. RNA + ATAC 통합 분석                    │
│                                                 │
│  B1. Gene-level Concordance 통합                │  ← 발현 변화와 chromatin 변화가 같은 방향인가
└───────────────────────────────────────────────┘
```

**핵심 배경 지식 (분석에 익숙하지 않다면 먼저 읽기):**

ATAC-seq는 "어디가 열려있는가(open chromatin)"를 측정하는 기술이다. RNA-seq가 유전자 발현량을 직접 재는 것과 달리, ATAC-seq는 DNA가 nucleosome으로부터 얼마나 노출되어 있는지를 측정하며, 이는 **그 부위에서 transcription factor(TF)가 결합하거나 transcription이 일어날 수 있는 물리적 가능성**을 나타낸다. 따라서 ATAC-seq 결과는 유전자 자체가 아니라 **peak**(염색체 상의 특정 구간)을 단위로 만들어지며, 이 peak을 유전자에 연결하는 것은 추가적인 annotation(주석) 단계가 필요하다 — 이 문서 전체에서 반복적으로 강조되는 지점이다.

---

## Part A. ATAC-seq 단독 분석 (Standalone)

### A1. Differential Accessibility (DA) Peak 분석

**① 목적**

두 조건(예: 처리군 vs 대조군) 사이에서 어떤 genomic 영역의 chromatin accessibility가 통계적으로 유의미하게 변했는지 찾는다. RNA-seq의 DEG(차등발현유전자) 분석과 개념적으로 동일하지만, 분석 단위가 유전자가 아니라 **peak**(genomic interval)이다. 이 결과가 ATAC-seq 분석 전체의 기반 데이터이며, 이후 모든 분석(A2~A8, B1)이 이 DA 결과를 출발점으로 삼는다.

**② 알고리즘**

- 일반적으로 **DESeq2**(또는 edgeR)를 사용한다. Peak 단위로 만들어진 count matrix(각 peak에 정렬된 read 수)에 대해 negative binomial GLM(Generalized Linear Model)을 적합시키고, 조건 간 차이를 **Wald test**로 검정한다.
- 다중 비교 보정은 **Benjamini-Hochberg(BH) FDR**(`padj`)을 사용한다.
- peak의 genomic 위치 annotation(어떤 유전자 근처인지, promoter/intron/distal 등)은 R의 **ChIPseeker** 패키지로 별도로 수행되며, DA 결과 테이블에 합쳐진다.

**③ 입력 데이터**

CMG-SeqViewer는 Excel(.xlsx) 또는 Parquet(.parquet) 형식을 모두 지원한다.

| 컬럼(허용되는 원본 이름 예시) | 의미 | 필수 여부 |
|---|---|---|
| `peak_id` / `peakid` / `interval` | peak 고유 ID | 필수 |
| `chr` / `chromosome` / `seqnames` | 염색체 | 권장 |
| `start`, `end` | peak 좌표(bp) | 권장 |
| `gene_name` / `nearest_gene` / `symbol` | 가장 가까운 유전자 심볼 | 권장 |
| `gene_id` | Ensembl 등 유전자 ID | 선택 |
| `annotation` | ChIPseeker가 분류한 genomic feature(Promoter/Intron/Distal Intergenic 등) | 선택(있으면 A2 가능) |
| `distance_to_tss` | TSS까지 거리(bp, 음수=upstream) | 선택(있으면 A3 가능) |
| `baseMean` / `base_mean` | 평균 accessibility(정규화된 count 평균) | 권장 |
| `log2FoldChange` / `log2fc` | log2 fold change | 필수 |
| `pvalue`, `padj` | 원본/보정 p-value | 필수(`padj`) |

생성 예시(R, DESeq2):
```r
library(DESeq2)
res <- results(dds)
df <- as.data.frame(res)
df$annotation      <- peak_anno@anno$annotation
df$distance_to_tss <- peak_anno@anno$distanceToTSS
df$nearest_gene    <- peak_anno@anno$SYMBOL
write.xlsx(df, "final_da_result.xlsx", sheetName = "DA_Results")
```

**④ 출력 데이터 (CMG-SeqViewer 내부 표준화 후)**

`peak_id, chromosome, peak_start, peak_end, nearest_gene, gene_id, annotation, distance_to_tss, base_mean, log2fc, lfcse, pvalue, adj_pvalue, peak_width(자동 계산)`

**⑤ 해석**

- **`log2fc` 양수** = 그 조건에서 해당 peak이 더 열림(accessible), **음수** = 더 닫힘.
- **`padj` ≤ 0.05**가 통상적인 유의성 기준이지만, ATAC-seq peak 수는 보통 RNA-seq 유전자 수(2만 개대)보다 훨씬 많아(수십만 개) multiple testing burden이 크다는 점을 감안해야 한다.
- **`annotation`과 `distance_to_tss`를 같이 봐야 하는 이유**: 같은 `log2fc`라도 promoter 근처에서 일어난 변화(직접적인 transcription 조절 신호일 가능성)와 distal intergenic에서 일어난 변화(enhancer 활성화 후보, 타겟 유전자 불확실)는 생물학적 의미가 다르다. `nearest_gene`은 가장 가까운 유전자일 뿐, 실제로 그 유전자를 조절한다는 증거는 아니다 — 이는 이 문서 전체에서 반복되는 핵심 주의사항이다.

**⑥ CMG-SeqViewer 시각화 연결**

- `File → Open ATAC-seq Dataset...`로 반입
- `Visualization → Volcano Plot`: `log2fc` vs `-log10(padj)`, up/down/ns 분류, threshold 조절 가능, hover로 `nearest_gene` 표시
- `Filter Panel → DA Analysis Filtering`: `padj`/`log2fc` 임계값, Annotation 드롭다운, `|TSS| ≤`, Peak Width 범위 필터(필터 결과는 새 탭으로 분리되어 다른 분석에도 그대로 이어짐)
- A2~A8, B1 분석은 모두 이 DA 데이터셋(또는 그 필터링 결과)을 입력으로 받는다

---

### A2. Genomic Annotation 분포 (Pie Chart)

**① 목적**

DA peak들이 promoter, intron, distal intergenic, exon 등 어떤 genomic feature에 주로 분포하는지 한눈에 파악한다. "이번 조건 변화가 주로 promoter-proximal 조절인지, distal enhancer 조절인지"를 가늠하는 첫 단계.

**② 알고리즘**

통계적 검정이 아니라 단순 **빈도 집계(value_counts)**다. ChIPseeker/HOMER가 만든 세부 annotation 문자열(예: `"intron (ENSMUSG00000092329, intron 1 of 15)"`)에서 첫 번째 `(` 앞부분만 추출해 대분류로 정규화한 뒤 카운트한다.

**③ 입력 데이터**

A1의 DA 데이터셋 중 `annotation` 컬럼.

**④ 출력 데이터**

카테고리별 peak 개수(상위 9개 + "Others"로 묶은 나머지).

**⑤ 해석**

- Promoter-TSS 비율이 높다 → 이번 변화는 transcription initiation과 직접 연관된 조절일 가능성이 큼
- Distal Intergenic 비율이 높다 → enhancer 활성 변화 후보. 이 경우 타겟 유전자가 불확실하므로 B1(RNA 통합) 해석에 더 신중해야 함
- 이 분포 자체는 "유의미한 peak"만 본 것인지 "전체 peak"을 본 것인지에 따라 결론이 달라지므로, Filter Panel에서 유의성 필터를 먼저 적용한 탭을 대상으로 그리는 것을 권장

**⑥ CMG-SeqViewer 시각화 연결**

`Visualization → Genomic Distribution Plot (ATAC-seq)` (ATAC 탭 활성 시 메뉴 활성화). `annotation` 컬럼이 없으면 안내 메시지가 표시된다.

---

### A3. TSS Distance 분포 (Histogram)

**① 목적**

DA peak이 TSS(transcription start site)로부터 얼마나 떨어져 있는지의 분포를 정량적으로 확인한다. A2가 범주형 분류라면, A3는 "promoter-proximal 정도"를 연속값으로 보는 것이다.

**② 알고리즘**

`distance_to_tss` 값의 히스토그램. 통계 검정 없음 — 분포 시각화.

**③ 입력 데이터**

A1의 `distance_to_tss` 컬럼.

**④ 출력 데이터**

지정한 범위(기본 ±50kb)·bin 수(기본 100)로 나눈 히스토그램 + `≤2kb`, `≤5kb` 비율 요약.

**⑤ 해석**

- TSS 근처(±2kb)에 몰린 peak이 많다 → promoter-driven 조절이 우세
- 넓게 퍼져있다 → distal regulatory element(enhancer 등) 비중이 큼
- A1에서 설명했듯, "근처 유전자"가 실제 조절 대상인지의 확신도는 거리가 가까울수록 높아진다 — B1 통합 분석에서 `promoter_only` 모드를 쓸지 판단하는 근거가 된다

**⑥ CMG-SeqViewer 시각화 연결**

`Visualization → TSS Distance Plot (ATAC-seq)`. Range/Bins를 UI에서 조절 가능.

---

### A4. MA Plot

**① 목적**

"전체적으로 accessibility가 높은 peak일수록 fold change가 더 신뢰할 만한가"를 확인하는 품질 점검(QC) 차트이자, RNA-seq의 MA plot과 동일한 개념을 ATAC-seq에 적용한 것.

**② 알고리즘**

X축 = `log2(base_mean)`, Y축 = `log2fc`. 검정 없음 — `padj`/`log2fc` 임계값으로 up/down/ns만 분류해 색칠.

**③ 입력 데이터**

A1의 `base_mean`, `log2fc`, `adj_pvalue`.

**④ 출력 데이터**

Up/Down/NS 분류가 추가된 산점도.

**⑤ 해석**

- 정상적인 경우 점들은 깔때기(funnel) 모양으로 분포한다 — accessibility가 낮은(왼쪽) peak일수록 fold change의 분산이 커야 정상이다. 이 모양이 깨져 있으면(예: 낮은 accessibility 영역에서도 분산이 작음) 정규화 문제를 의심할 수 있다.
- Up/Down이 X축 특정 구간에 쏠려 있으면, 그 accessibility 구간에서만 검정력이 충분했다는 의미일 수 있다(통계적 검정력 문제)

**⑥ CMG-SeqViewer 시각화 연결**

`Visualization → MA Plot (ATAC-seq)`. Hover 시 `nearest_gene`(우선) 표시, gene label 모드(Top N / Custom list) 지원.

---

### A5. TF Motif Enrichment (HOMER / MEME-Suite AME)

**① 목적**

유의미하게 변한 peak들(예: UP peak) 안에 어떤 transcription factor의 결합 모티프가 통계적으로 풍부하게(enriched) 나타나는지 찾는다. "이 chromatin 변화 뒤에 어떤 TF가 작동했을 가능성이 있는가"를 처음으로 묻는 분석 — A1~A4가 "어디서, 얼마나" 변했는지를 보는 것이었다면, A5부터는 "왜(어떤 TF 때문에)"를 묻는다.

**② 알고리즘**

- **HOMER (`findMotifsGenome.pl`)**: target 서열 집합(예: UP peak)과 background 서열 집합(예: 전체 peak) 각각에서 특정 모티프의 출현 빈도를 비교해, **cumulative hypergeometric 분포 기반 enrichment test**로 p-value를 계산한다. HOMER에 내장된 참조 모티프 라이브러리(known motif database, 보통 수백 개)에 들어있는 **모든 모티프를 매번 전부 검정**하며, 그중 p-value가 낮은 것을 "enriched"라고 본다.
- **MEME-Suite AME**: 설정에 따라 **Fisher's exact test**(이분류) 또는 **rank-sum test**(점수 기반)를 사용해 동일한 종류의 enrichment를 계산한다.
- 둘 다 다중 비교 보정으로 q-value(Benjamini)를 함께 제공한다.

**③ 입력 데이터**

A1의 DA 결과에서 UP/DOWN peak을 BED로 분리해 외부에서 HOMER/AME를 실행한 산출물:

- HOMER: `knownResults.txt` (탭 구분 텍스트)
- AME: `ame.tsv` (`#` 주석 행 포함 탭 구분 텍스트)

| 표준화된 컬럼 | 의미 |
|---|---|
| `motif_name` | TF 이름(HOMER는 `"IRF1(IRF)/HepG2.../Homer"`에서 `IRF1`만 추출) |
| `motif_id` | 모티프 DB ID |
| `consensus` | 컨센서스 서열 |
| `motif_pvalue` | enrichment p-value |
| `motif_qvalue` | FDR-보정 q-value |
| `target_pct` / `bg_pct` | target/background 집합에서 모티프가 발견된 비율(%) |

**④ 출력 데이터**

위 표준화 컬럼들로 구성된 DataFrame. HOMER 기준 보통 400~500개 행(참조 라이브러리 크기만큼, **이건 peak 개수와 무관하게 항상 고정된 개수**라는 점을 주의해야 한다).

**⑤ 해석 — 반드시 알아야 할 함정들**

1. **출력 행 개수는 참조 모티프 라이브러리 크기다.** "이번 비교에서 enrichment 된 모티프 개수"가 아니다. 실제 유의성은 `motif_qvalue`/`motif_pvalue`로 판단해야 한다.
2. **최소 peak 개수가 필요하다.** target 서열이 너무 적으면(대략 100~200개 미만) 통계적 검정력이 부족해 q-value가 절대 유의 수준에 도달하지 못한다. 실제로 본 분석 과정에서 target peak이 1~48개인 비교는 q<0.05가 0건이었고, target peak이 600~1000개인 비교에서는 30~50개 이상의 유의미한 모티프가 나왔다 — **임계값을 완화하는 것이 아니라, 표본 자체가 분석 가능한 크기인지를 먼저 판단해야 한다.**
3. **모티프 패밀리 모호성.** 같은 모티프를 공유하는 paralog TF(예: 같은 zinc finger 패밀리)는 motif 분석만으로는 구분되지 않는다.
4. **간접적 증거다.** "이 모티프가 풍부하다"는 "이 TF가 실제로 결합했다"는 직접 증거가 아니라, 결합 가능성에 대한 통계적 추정이다 — A6(footprinting), A7(chromVAR)이 이 한계를 보완한다.

**⑥ CMG-SeqViewer 시각화 연결**

`File → Open TF Motif Results...`로 HOMER/AME 결과를 불러온 뒤, `Visualization → TF Motif Enrichment Plot`. 단일 모드(가로 막대, `-log10(p)` 기준 Top N)와 UP/DOWN 비교 모드(나란히 배치) 지원. Q-value cutoff, Top N, `%` 오버레이를 UI에서 조절.

---

### A6. TF Footprinting (TOBIAS BINDetect)

**① 목적**

A5의 모티프 enrichment는 "이 서열에 모티프가 통계적으로 많다"는 수준이었다면, footprinting은 한 단계 더 나아가 **"그 모티프 자리에 실제로 단백질(TF)이 결합한 물리적 흔적(footprint)이 있는가"**를 확인한다. ATAC-seq 신호에서 TF가 결합한 자리는 Tn5 효소가 그 자리를 자르지 못해 read depth가 국소적으로 살짝 꺼지는(dip) 흔적을 남기는데, 이를 정량화한 것이 footprint score다.

**② 알고리즘 (TOBIAS 3단계 파이프라인)**

1. **ATACorrect**: Tn5 효소의 서열 절단 편향(insertion bias)을 보정 — raw ATAC-seq cut site profile에서 이 편향을 제거해야 진짜 결합 흔적만 남는다.
2. **ScoreBigwig**: 보정된 신호에서 footprint score(국소적 depletion 정도)를 계산.
3. **BINDetect**: 조건 간(cond1 vs cond2) 평균 footprint score 차이를 검정해 **differential binding score**(`change`)와 p-value를 산출하고, 점수 기준으로 각 모티프 자리를 bound/unbound로 분류.

**③ 입력 데이터**

TOBIAS BINDetect의 `bindetect_results.txt`. **핵심 주의점: 조건명이 컬럼명에 직접 포함되어 동적으로 바뀐다**(예: `Acute_1D_mean_score`, `Acute_1D_Control_change`). CMG-SeqViewer는 헤더를 읽어 조건명 2개를 자동 감지한다.

| 원본(동적) 패턴 | 표준화된 컬럼 | 의미 |
|---|---|---|
| `name` | `fp_motif_name` | TF 이름 |
| `{cond1}_mean_score` | `cond1_score` | cond1 평균 footprint 점수 |
| `{cond2}_mean_score` | `cond2_score` | cond2 평균 footprint 점수 |
| `{cond1}_{cond2}_change` | `footprint_change` | 결합 변화량(양수=cond1에서 더 결합) |
| `{cond1}_{cond2}_pvalue` | `footprint_pvalue` | 유의성 |
| `{cond1}_bound`, `{cond2}_bound` | `cond1_bound`, `cond2_bound` | 결합 site 수 |

**④ 출력 데이터**

위 표준화 컬럼 + 조건명 메타데이터(`cond1_name`, `cond2_name`).

**⑤ 해석**

- `footprint_change`가 양수면 **cond1에서 그 TF가 더 활발하게 결합**, 음수면 cond2에서 더 결합.
- A5(모티프 enrichment)와 결과가 일치하면 신뢰도가 높아진다 — "모티프가 풍부하고, 실제로 그 자리에 결합 흔적도 있다"는 이중 증거.
- 일치하지 않을 수도 있다 — 모티프는 있지만 실제로는 다른 보조인자(co-factor) 없이는 결합하지 않는 TF일 수 있음(이게 바로 footprinting이 motif enrichment보다 우월한 이유다).
- BAM 파일(원본 시퀀싱 데이터)이 필요해 motif enrichment보다 준비 난이도가 훨씬 높다.

**⑥ CMG-SeqViewer 시각화 연결**

`File → Open TF Footprint Results...` → `Visualization → TF Activity Plot (Footprint)`. X=cond1 score, Y=cond2 score 산점도, 대각선(y=x) 기준 위/아래로 gain/loss 분류, p-value/변화량 임계값과 Top N 라벨링을 UI에서 조절.

---

### A7. chromVAR Differential TF Activity

**① 목적**

A5·A6이 "어떤 peak 그룹(UP/DOWN)" 단위로 한 번 계산하는 분석이었다면, chromVAR은 **샘플(replicate) 단위로** 각 TF의 추정 활성도를 계산해 그룹 간 비교를 한다. 특히 **DA peak 개수가 너무 적어 A5/A6이 통계적으로 무력할 때**(소규모 효과, 적은 유의 peak) 대안으로 유용하다 — peak 전체 매트릭스를 사용하기 때문에 "유의미한 peak이 충분한가"라는 전제 조건이 필요 없다.

**② 알고리즘**

1. 전체 peak × 샘플 count matrix와 모티프 데이터베이스(보통 JASPAR2020 CORE, 약 700여 개 모티프)를 입력으로 받는다.
2. 각 모티프를 포함하는 peak들의 접근성 총합을 계산하고, **GC-content 등으로 매칭된 background peak 집합**과 비교해 **bias-corrected deviation z-score**를 샘플마다 산출한다 — "이 모티프를 포함한 peak들이 무작위 기대치보다 얼마나 더/덜 열려 있는가"를 표준화한 값.
3. 조건 간 비교는 **Wilcoxon rank-sum test**로 z-score 평균 차이(`delta`)의 유의성을 검정한다.

**③ 입력 데이터**

두 가지 형식 모두 지원:

```
# diff_tf.csv (chromVAR R 패키지 직접 출력)
motif, mean_compare, mean_base, delta, p_value, padj

# seqviewer parquet (파이프라인 변환본)
tf_name, mean_zscore_compare, mean_zscore_base, delta_zscore, p_value, padj
```

추가로 **`tf_variability.csv`**(같은 폴더 또는 상위 3단계 이내 `chromvar/` 하위)가 있으면 JASPAR ID를 실제 TF 이름으로 자동 변환한다. 이 파일이 없으면 `MA0006.1` 같은 ID 그대로 표시된다.

**④ 출력 데이터**

`chromvar_motif_id, chromvar_tf_name, chromvar_mean_compare, chromvar_mean_base, chromvar_delta, chromvar_pvalue, chromvar_padj` (+ 계산 컬럼 `chromvar_neg_log_padj`).

**⑤ 해석 — 반드시 알아야 할 함정들**

- **`chromvar_delta`(compare − base)**: 양수면 비교군에서 그 TF의 타겟 모티프 부위가 더 열림(=활성 가능성), 음수면 더 닫힘.
- **소규모 샘플에서는 raw p-value 자체가 구조적으로 0.05 밑으로 못 내려갈 수 있다.** Wilcoxon test는 표본 수가 적으면(예: 그룹당 2~4개) 검정통계량이 몇 개 값으로만 떨어져(discreteness), 가능한 최소 p-value 자체가 0.05보다 큰 경우가 생긴다. 이 경우 FDR 보정(`padj`)을 완화해도 의미가 없다 — **`padj` 기준 유의성 판정 대신 `chromvar_delta`의 절댓값(효과 크기) 순으로 해석하는 것이 더 현실적**이다.
- A5(motif enrichment)와 마찬가지로 모티프를 공유하는 TF 패밀리는 구분되지 않는다(예: `Ahr::Arnt` heterodimer 표기).
- 이건 결합의 직접 증거가 아니라 **추론(proxy)**이다 — ChIP-seq 등으로 검증이 필요한 가설을 만드는 단계로 이해해야 한다.

**⑥ CMG-SeqViewer 시각화 연결**

`File → Open chromVAR Results...` → `Visualization → chromVAR TF Activity Plot`. 세 가지 모드:
- **Volcano**: X=delta z-score, Y=`-log10(padj)`. RNA-seq volcano와 같은 틀이지만 측정 대상이 "TF 결합 부위의 열림 정도"라는 점이 다르다.
- **Scatter**: X=base 평균 z-score, Y=compare 평균 z-score, 대각선(y=x) 기준 위/아래 분류.
- **Multi-condition Heatmap**: 여러 비교군(CHROMVAR_DIFF_TF 데이터셋)을 동시에 불러오면 TF × 조건 delta 행렬을 한 화면에서 비교(여러 조건에서 일관되게 움직이는 TF를 찾는 데 유용).

마우스 오버 시 TF 이름, motif ID, delta, padj, p-value를 툴팁으로 표시.

---

### A8. Multi-Condition DA Peak Overlap (Venn / UpSet)

**① 목적**

여러 비교 조건(예: Acute_1D vs Control, Acute_3D vs Control, Chronic_100uM vs Control...)에서 나온 DA peak들이 서로 얼마나 겹치는지 확인한다. "이 조건들에서 공통으로 변하는 peak"과 "특정 조건에만 특이적인 peak"을 구분하는 것이 목적이며, RNA-seq에서 여러 비교의 DEG 리스트를 Venn diagram으로 겹쳐보는 것과 같은 개념을 ATAC-seq peak에 적용한 것이다.

**② 알고리즘**

순수 **집합(set) 연산**(교집합/차집합)이다. 단, **비교의 단위가 gene이 아니라 peak_id(좌표)**라는 점이 RNA-seq와의 핵심 차이다 — 이 부분은 ⑤ 해석에서 자세히 설명한다.

**③ 입력 데이터**

이미 로드된 `ATAC_SEQ` 타입 데이터셋 2개 이상(추가 파일 불필요). 단, **전제 조건**: 비교 대상 데이터셋들이 **같은 peak set(consensus/union peak)**에서 나와야 한다 — 모든 조건의 BAM을 합쳐 peak을 한 번만 호출(call)한 경우에 한해 `peak_id`가 조건마다 동일해 직접 비교가 유효하다. 조건별로 독립적으로 peak을 호출했다면 `bedtools intersect`로 좌표를 먼저 맞춰야 한다.

**④ 출력 데이터**

각 데이터셋 조합(intersection)별 peak_id 멤버십 테이블(boolean matrix).

**⑤ 해석 — RNA-seq Venn과 다른 점**

RNA-seq의 두 DEG 리스트를 gene으로 비교하는 것은 둘 다 본질적으로 gene-level 측정값이라 정당하다. 반면 ATAC peak을 **gene으로** 비교하면(예: `nearest_gene` 기준), peak의 다대일 집계로 방향성이 상쇄되거나, "최근접 유전자 ≠ 실제 타겟 유전자"라는 근본적 오차가 생긴다. 그래서 CMG-SeqViewer는 ATAC 데이터셋을 비교할 때 **peak_id(좌표)를 키로 사용**하도록 구현되어 있다 — 이것이 RNA-seq gene 비교와 동등한 엄밀성을 갖는 방식이다.

- 모든 조건에서 공통으로 나타나는 peak → 자극과 무관하게 일관된 핵심 조절 영역일 가능성
- 특정 조건에만 특이적인 peak → 그 조건만의 고유한 반응

**⑥ CMG-SeqViewer 시각화 연결**

`Visualization → 🔗 DA Peak Overlap (ATAC-seq)...` → ATAC 데이터셋 다중 선택. **2~3개는 Venn Diagram**, **4개 이상은 UpSet Plot**(Set size + Intersection size + matrix dot plot)으로 자동 분기. peak_id 교집합 비율이 너무 낮으면("consensus peak set이 아닐 수 있음") 경고가 표시된다. Export로 각 조합의 peak_id 목록을 받을 수 있다.

---

## Part B. RNA + ATAC 통합 분석

### B1. Gene-level Concordance 통합

**① 목적**

"이 유전자의 발현이 변했는데, 그 근처 chromatin도 같은 방향으로 변했는가?"를 확인한다. RNA-seq만으로는 발현 변화의 원인(전사 조절 vs post-transcriptional 조절)을 알 수 없는데, ATAC-seq 결과와 결합하면 그 변화가 **chromatin 열림/닫힘으로 설명되는 변화**인지 아닌지를 가늠할 수 있다. Part A의 모든 분석이 ATAC 단독이었다면, B1은 처음으로 RNA-seq DE 결과를 ATAC-seq DA 결과와 직접 연결한다.

**② 알고리즘**

1. **ATAC peak → gene 집계**: ATAC peak들을 `nearest_gene`(전체 peak 사용) 또는 `promoter_only`(TSS ± window, 기본 2000bp 이내 peak만 사용) 방식으로 유전자별로 그룹화해 `peak_count`, `atac_log2fc_mean`, `atac_log2fc_max`(signed, 방향성 유지), `atac_padj_min`을 계산한다.
2. **RNA-ATAC outer join**: RNA DE 결과(`symbol` 기준)와 위에서 집계한 ATAC 결과를 outer join — 한쪽에만 있는 유전자도 포함된다.
3. **Concordance 7-category 분류** (`rna_sig`, `atac_sig` 각각의 유의성 기준은 사용자가 UI에서 조절):

| 카테고리 | 조건 | 생물학적 해석 |
|---|---|---|
| `Concordant_Both_UP` | RNA↑ & ATAC↑ 둘 다 유의 | chromatin 열림이 발현 증가를 지지 |
| `Concordant_Both_DOWN` | RNA↓ & ATAC↓ 둘 다 유의 | chromatin 닫힘이 발현 감소를 지지 |
| `Discordant_RNA_UP_ATAC_DOWN` | RNA↑인데 ATAC↓ | 발현은 늘었는데 chromatin은 닫힘 — post-transcriptional 조절(mRNA 안정성 등) 의심 |
| `Discordant_RNA_DOWN_ATAC_UP` | RNA↓인데 ATAC↑ | chromatin은 열렸는데 발현은 감소 — 억제성 TF 결합 등 다른 기전 의심 |
| `RNA_only` | RNA만 유의 | 근처 ATAC 변화 없음(또는 peak이 없음) |
| `ATAC_only` | ATAC만 유의 | chromatin은 변했지만 발현엔 아직(또는 끝내) 반영 안 됨 |
| `Not_significant` | 둘 다 비유의 | — |

**③ 입력 데이터**

`RNA-seq DE Dataset`(`symbol, log2fc, adj_pvalue, base_mean`) + `ATAC-seq DA Dataset`(`nearest_gene, log2fc, adj_pvalue, distance_to_tss`). Multi-Omics Panel에서 두 데이터셋을 페어링하고, integration method(`nearest_gene`/`promoter_only`)와 4개의 유의성 cutoff(RNA padj/|log2FC|, ATAC padj/|log2FC|)를 지정한다.

**④ 출력 데이터**

`symbol, rna_log2fc, rna_padj, rna_base_mean, peak_count, atac_log2fc_mean, atac_log2fc_max, atac_padj_min, concordance, regulatory_status`

**⑤ 해석 — 반드시 알아야 할 한계**

이 분석은 "ATAC DA를 gene 단위로 비교"하는 A8과 근본적으로 다른 종류의 비교다. A8은 peak_id로 비교해 RNA-seq gene 비교와 동등한 엄밀성을 가지지만, **B1은 peak을 gene으로 축약하는 과정 자체가 추정을 포함**한다.

1. **다대일 집계의 방향 상쇄**: 한 유전자 주변에 peak이 여러 개 있고 서로 반대 방향으로 움직이면(`atac_log2fc_mean`을 평균 내는 과정에서) 실제로 의미 있는 신호(예: promoter는 닫히고 distal enhancer는 열림)가 사라질 수 있다. `atac_log2fc_max`(signed max)가 이를 일부 보완하지만 "어느 peak이 진짜 신호인지"는 알 수 없다.
2. **"nearest gene" ≠ "실제 타겟 유전자"**: enhancer는 가장 가까운 유전자가 아니라 수십~수백 kb 떨어진 유전자를 조절하는 경우가 흔하다. Hi-C/eQTL로 검증한 연구에서는 "최근접 유전자=실제 타겟"인 비율이 cell type에 따라 40~70%에 불과하다고 보고된다.
3. **`promoter_only` 모드는 부분적 개선이지만 trade-off가 있다**: TSS 근처로 제한하면 "이 peak이 그 유전자를 직접 조절한다"는 가정의 신뢰도는 올라가지만, ATAC-seq의 가장 흥미로운 신호일 수 있는 distal enhancer 변화를 모두 버리게 된다.
4. 따라서 결론적으로, **RNA-RNA 비교나 ATAC-ATAC 비교(A8)는 신뢰도가 높지만, RNA-ATAC gene-level 통합(B1)은 "유전자 단위로 본 근사치"라는 점을 항상 함께 명시해야 한다.**

**⑥ CMG-SeqViewer 시각화 연결**

`Analysis → Integrate RNA + ATAC` 실행 후 4가지 시각화:

- **Quadrant Plot** (`Visualization → Quadrant Plot`): X=ATAC log2FC, Y=RNA log2FC. 4분면(Q1 Both↑, Q2 RNA↑ATAC↓, Q3 Both↓, Q4 RNA↓ATAC↑)으로 직관적 분류. Hover 시 유전자 심볼·RNA/ATAC 값·concordance 카테고리 표시.
- **Concordance Heatmap** (`Visualization → Concordance Heatmap`): 유의한 유전자만 골라 concordance 카테고리 순으로 정렬, `[RNA log2FC | ATAC log2FC]` 2열 히트맵 + 우측에 카테고리 색상 사이드바.
- **Integrated Volcano** (`Visualization → Integrated Volcano`): 기존 RNA volcano plot에서 점 색상을 concordance 카테고리로, 점 크기를 ATAC peak count(`log1p` 스케일)로 표현 — "발현 변화가 크고 ATAC 지지 증거도 많은" 유전자를 한 번에 찾을 수 있다.
- **Concordance Summary** (`Visualization → Concordance Summary`): 7개 카테고리별 유전자 수·비율 막대 차트 + 집계 테이블. 전체적으로 "이번 실험에서 RNA와 ATAC 변화가 얼마나 일치하는가"를 한 장으로 요약.

Export: 다중 시트 Excel(`Integrated_Summary`, `Concordant_UP`, `Concordant_DOWN`, `Discordant`, `RNA_only`, `ATAC_only`, `Peak_Details`).

---

## 부록 1. 어떤 질문에 어떤 분석을 써야 하는가

| 연구 질문 | 추천 분석 |
|---|---|
| "이 조건에서 chromatin이 어디서 변했나?" | A1 (DA) |
| "그 변화가 promoter 쪼 아니면 distal enhancer 쪼?" | A2, A3 |
| "유의미한 peak이 너무 적어서 motif 분석이 안 될 것 같다" | A7 (chromVAR) — peak 개수가 충분하면 A5(motif)도 같이 |
| "어떤 TF가 이 변화를 일으켰을까?" | A5 → A6 (가능하면) → A7 순으로 증거를 쌓기 |
| "이 TF가 실제로 결합했다는 더 직접적인 증거가 필요하다" | A6 (footprinting, BAM 필요) |
| "여러 시점/용량 조건에서 공통/특이적 변화를 구분하고 싶다" | A8 (peak overlap) |
| "발현 변화가 chromatin으로 설명되는지 알고 싶다" | B1 (RNA+ATAC 통합) — 단, gene-level 근사치라는 한계를 같이 보고 |

## 부록 2. 공통 주의사항

1. **표본 크기가 모든 통계 검정의 검정력을 결정한다.** ATAC-seq는 보통 RNA-seq보다 샘플 수가 적은 경우가 많고(비용/실험 난이도), 이는 A5(motif), A7(chromVAR) 모두에서 "임계값을 완화"가 아니라 "분석이 가능한 표본인지"를 먼저 판단해야 하는 이유다.
2. **multiple testing burden**: ATAC peak 수(수십만 개)가 유전자 수(2만 개대)보다 훨씬 많아 FDR 보정이 더 엄격하게 작동한다.
3. **"peak이 gene 근처에 있다" ≠ "그 유전자를 조절한다"**: 이 문서에서 반복적으로 등장하는 핵심 주의사항이다. Hi-C, eQTL, CRISPRi 스크리닝 같은 직접적 기능 검증이 없는 한, nearest-gene 기반 해석은 항상 가설(hypothesis)로 취급해야 한다.
4. **모티프 기반 분석(A5, A7)은 TF 패밀리를 구분하지 못한다.** 결과에 나온 TF 이름은 "이 모티프와 가장 흔히 연관되는 TF" 정도로 해석하고, 실제 후보는 RNA-seq 발현 데이터(그 TF 패밀리 중 어떤 멤버가 실제로 발현되는지)와 교차 확인하는 것이 좋다.
