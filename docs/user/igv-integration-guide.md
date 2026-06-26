# IGV 연동 가이드

CMG-SeqViewer와 IGV(Integrative Genomics Viewer)를 연결하여  
ATAC-seq peak를 게놈 브라우저에서 직접 확인하는 방법을 설명합니다.

---

## 목차

1. [개요 및 왜 필요한가](#1-개요-및-왜-필요한가)
2. [사전 준비: IGV 설치 및 포트 활성화](#2-사전-준비-igv-설치-및-포트-활성화)
3. [사전 준비: BigWig 파일 생성](#3-사전-준비-bigwig-파일-생성)
4. [사전 준비: 참조 게놈 및 염색체 명명 규칙](#4-사전-준비-참조-게놈-및-염색체-명명-규칙)
5. [CMG-SeqViewer 설정](#5-cmg-seqviewer-설정)
6. [사용 방법](#6-사용-방법)
7. [ATAC-seq Annotation 이해와 IGV 검증](#7-atac-seq-annotation-이해와-igv-검증)
8. [IGV Session 파일로 작업 환경 저장](#8-igv-session-파일로-작업-환경-저장)
9. [문제 해결](#9-문제-해결)

---

## 1. 개요 및 왜 필요한가

CMG-SeqViewer의 ATAC-seq 테이블에는 각 peak에 대해 다음 정보가 표시됩니다.

| 컬럼 | 예시 | 의미 |
|------|------|------|
| `chromosome` | chr3 | 염색체 |
| `peak_start` / `peak_end` | 1,045,230 / 1,045,780 | peak 좌표 |
| `annotation` | intron (ENSMUSG00000092329, intron 1 of 15) | 물리적으로 겹치는 유전자 구조 |
| `nearest_gene` | Actb | TSS가 가장 가까운 유전자 |
| `distance_to_tss` | 8,091 | nearest_gene TSS까지 거리 (bp) |

이 숫자만으로는 해당 peak가 **실제로 어느 유전자의 어떤 구조에 위치하는지**, 
BAM/BigWig 신호가 조건 간에 어떻게 달라지는지 직관적으로 파악하기 어렵습니다.

**IGV 연동을 통해 가능한 것:**

```
CMG-SeqViewer 테이블에서 peak 행 우클릭
        ↓
"Send to IGV" 클릭
        ↓
IGV가 해당 좌표(± padding)로 자동 이동
        ↓
Control BigWig / Treatment BigWig pileup 비교
참조 유전자 구조(GTF)와 함께 확인
```

---

## 2. 사전 준비: IGV 설치 및 포트 활성화

### 2.1 IGV 다운로드

[https://igv.org/doc/desktop/](https://igv.org/doc/desktop/) 에서  
Windows 또는 macOS 버전을 다운로드합니다.  
버전 2.8 이상을 권장합니다 (HTTP 포트 기능 안정화).

### 2.2 포트 활성화 (필수)

IGV를 실행한 후:

```
Tools → Preferences → Advanced 탭
  ☑ Enable port: 60151
  → OK → IGV 재시작
```

> **이 설정 없이는 CMG-SeqViewer에서 IGV로 명령을 보낼 수 없습니다.**

포트가 활성화되면 IGV는 `http://127.0.0.1:60151` 에서 HTTP 명령을 수신합니다.  
브라우저에서 `http://127.0.0.1:60151/status` 를 열어 응답이 오면 정상입니다.

### 2.3 IGV HTTP Remote Control 명령 (참고)

CMG-SeqViewer 내부적으로 사용하는 명령들입니다.

| 명령 | URL 예시 | 동작 |
|------|----------|------|
| 연결 확인 | `GET /status` | IGV 상태 반환 |
| 좌표 이동 | `GET /goto?locus=chr3:1045000-1046000` | 해당 locus로 이동 |
| 트랙 로드 | `GET /load?file=/data/ctrl.bw&name=Control` | BigWig/BAM 로드 |
| 게놈 전환 | `GET /genome?genome=mm10` | 참조 게놈 변경 |

---

## 3. 사전 준비: BigWig 파일 생성

BigWig(`.bw`)는 ATAC-seq 신호를 게놈 브라우저에서 시각화하기 위한 파일입니다.  
BAM 파일로부터 생성하며, 일반적으로 deepTools를 사용합니다.

### 3.1 deepTools 설치

```bash
pip install deeptools
# 또는
conda install -c bioconda deeptools
```

### 3.2 BAM → BigWig 변환

#### 단일 샘플

```bash
bamCoverage \
    --bam sample.bam \
    --outFileName sample.bw \
    --normalizeUsing RPKM \
    --binSize 10 \
    --extendReads 200 \
    --numberOfProcessors 4
```

**주요 파라미터 설명:**

| 파라미터 | 권장값 | 설명 |
|----------|--------|------|
| `--normalizeUsing` | `RPKM` | 시퀀싱 깊이 정규화 (CPM도 가능) |
| `--binSize` | `10` | 해상도 (bp); 작을수록 파일 크고 세밀함 |
| `--extendReads` | `200` | ATAC-seq fragment 복원을 위한 read extension |
| `--effectiveGenomeSize` | `2652783500` (mm10) | 정규화 시 사용 (선택) |

#### 여러 샘플 일괄 처리

```bash
for bam in *.bam; do
    name=$(basename "$bam" .bam)
    bamCoverage \
        --bam "$bam" \
        --outFileName "${name}.bw" \
        --normalizeUsing RPKM \
        --binSize 10 \
        --extendReads 200 \
        --numberOfProcessors 4
    echo "Done: ${name}.bw"
done
```

### 3.3 MACS2 bdg → BigWig (대안)

MACS2의 `-B` 옵션으로 생성한 `.bdg` 파일을 변환하는 방법:

```bash
# bedGraph → BigWig
# chrom.sizes 파일 필요 (fetchChromSizes mm10 > mm10.chrom.sizes)
bedGraphToBigWig treatment_pileup.bdg mm10.chrom.sizes treatment.bw
```

### 3.4 권장 파일 구성 예시

```
igv_tracks/
├── Control_rep1.bw
├── Control_rep2.bw
├── Treatment_rep1.bw
├── Treatment_rep2.bw
└── merged_Control.bw      ← bamMerge 후 생성 권장
    merged_Treatment.bw
```

---

## 4. 사전 준비: 참조 게놈 및 염색체 명명 규칙

### 4.1 참조 게놈 일치

ATAC-seq 데이터를 정렬한 참조 게놈과 IGV에서 로드하는 게놈이 **반드시 일치**해야 합니다.

| 마우스 | 인간 |
|--------|------|
| mm10 (GRCm38) | hg38 (GRCh38) |
| mm39 (GRCm39) | hg19 (GRCh37) |

IGV에서 게놈 전환: **상단 드롭다운 메뉴 또는 `Genomes → Load Genome from Server`**

### 4.2 염색체 명명 규칙 (중요)

ATAC 데이터와 BigWig 파일이 **같은 chr 표기 방식**을 사용해야 합니다.

| 스타일 | 예시 | 출처 |
|--------|------|------|
| UCSC | `chr1`, `chr2`, `chrX` | UCSC, GENCODE |
| Ensembl | `1`, `2`, `X` | Ensembl GTF |

> **대부분의 ATAC-seq 파이프라인(HOMER 포함)은 `chr` prefix를 사용합니다.**  
> DESeq2 DA 결과 파일이 `chr3` 형식이면 BigWig도 동일하게 생성해야 합니다.

확인 방법:
```bash
# BAM 헤더에서 염색체 명 확인
samtools view -H sample.bam | grep "^@SQ" | head -5
# chr1 또는 1 형식인지 확인

# BigWig 헤더 확인
bigWigInfo sample.bw | head -10
```

---

## 5. CMG-SeqViewer 설정

### 5.1 IGV Settings 열기

```
메뉴: View → IGV Settings...
```

### 5.2 설정 항목

#### Connection
| 항목 | 기본값 | 설명 |
|------|--------|------|
| Port | 60151 | IGV가 수신하는 포트 번호 |
| Test Connection | — | 버튼 클릭 시 IGV 연결 상태 확인 |

#### Navigation
| 항목 | 기본값 | 설명 |
|------|--------|------|
| Context padding | 500 bp | peak 양 옆에 추가되는 시야 범위 |
| Auto-set genome | ☑ 활성 | peak 전송 시 데이터의 genome_build로 IGV 자동 전환 |

> **Padding 설정 가이드:**  
> - Promoter peak 확인: 500–1,000 bp  
> - Enhancer / Intergenic peak 확인: 2,000–5,000 bp  
> - 전체 유전자 구조 확인: 10,000 bp 이상

#### Signal Tracks
BigWig 파일을 목록에 등록합니다.

1. **[+ Add Track]** → 파일 탐색기에서 `.bw` 또는 `.bam` 선택
2. Display Name, Genome 입력 (예: `Control_ATAC`, `mm10`)
3. 여러 파일 등록 후 **[Load All Tracks in IGV Now]** → IGV에 일괄 로드

등록된 트랙 정보는 앱 재시작 후에도 유지됩니다.

### 5.3 초기 설정 체크리스트

```
[ ] IGV 실행 확인
[ ] IGV 포트 60151 활성화 확인 (브라우저로 /status 테스트)
[ ] BigWig 파일 생성 완료 (Control / Treatment)
[ ] CMG-SeqViewer → View → IGV Settings
[ ] Port: 60151, Padding: 500 bp 입력
[ ] BigWig 파일 경로 등록
[ ] Test Connection → ● Connected 확인
[ ] Load All Tracks in IGV Now
[ ] IGV에서 mm10 (또는 hg38) genome 로드 확인
```

---

## 6. 사용 방법

### 6.1 Peak를 IGV로 전송

1. ATAC-seq 탭(Whole Dataset 또는 Filtered)에서 관심 peak 행을 찾습니다
2. **행에서 우클릭**
3. 컨텍스트 메뉴에서 **"🔬 Send to IGV"** 클릭
4. IGV가 `chromosome:peak_start-peak_end (± padding)` 좌표로 자동 이동합니다

### 6.2 Locus 복사 (IGV 미연결 시 대안)

우클릭 메뉴에서 **"📋 Copy Locus"** 클릭  
→ `chr3:1045230-1045780` 형식으로 클립보드에 복사  
→ IGV 상단 위치 입력창에 붙여넣기(Ctrl+V)

### 6.3 키보드 단축키

| 단축키 | 동작 |
|--------|------|
| (행 선택 후) `G` | Send to IGV |
| (행 선택 후) `L` | Copy Locus |

### 6.4 실제 워크플로우 예시

```
1. ATAC-seq 데이터 로드 → Statistical filter (padj ≤ 0.05, |log2FC| ≥ 1)
2. Filtered 탭에서 significant DA peaks 목록 확인
3. annotation: "Promoter-TSS" 필터 적용
4. 관심 peak (예: nearest_gene = Gata1) 우클릭 → Send to IGV
5. IGV에서 확인:
   - Control BigWig vs Treatment BigWig 신호 차이
   - 해당 위치가 실제로 Gata1 프로모터 영역인지
   - 인근 유전자 구조
6. log2FC가 높은 순서대로 순차 확인
```

---

## 7. ATAC-seq Annotation 이해와 IGV 검증

이 섹션은 CMG-SeqViewer의 `annotation` 컬럼과 `nearest_gene` 컬럼의 관계를  
IGV로 시각적으로 확인하는 방법을 설명합니다.

### 7.1 두 컬럼의 차이

#### `annotation` 컬럼: "peak이 물리적으로 겹치는 구조"

```
annotation: intron (ENSMUSG00000097836, intron 2 of 4)
```

이 peak의 좌표(chr:start–end)가 ENSMUSG00000097836 유전자의 **두 번째 intron 구조 안에 위치**한다는 의미입니다.
HOMER가 유전자 모델(GTF)을 기준으로 peak와 exon/intron/UTR 구조의 물리적 겹침을 계산합니다.

#### `nearest_gene` + `gene_id`: "TSS가 가장 가까운 유전자"

```
nearest_gene: Actb
gene_id: ENSMUSG00000029580
distance_to_tss: 8091
```

Peak 중심 좌표에서 거리를 측정했을 때, **TSS가 가장 가까운 유전자**가 Actb라는 의미입니다.

### 7.2 두 컬럼이 다를 수 있는 이유

```
게놈 좌표 ─────────────────────────────────────────────────────▶

[──────── Gene A (ENSMUSG00000097836) — 매우 큰 유전자 ──────────]
              exon1    [intron 2]    exon2 ...
                           ↑
                       [ATAC peak]
                           ↑
              annotation: intron (ENSMUSG00000097836, intron 2)

                  [Gene B (Actb) TSS►──── Gene B ────────]
                        ↑
                  nearest_gene: Actb
                  distance_to_tss: 8,091 bp
```

- Peak가 **Gene A의 intron에 물리적으로 걸쳐** 있지만
- TSS 기준으로는 **Gene B(Actb)가 더 가까운** 경우

이런 경우 peak가 **Gene A의 intron에 위치한 Gene B의 enhancer**일 가능성이 있습니다.

### 7.3 IGV로 검증하는 방법

```
1. CMG-SeqViewer에서 annotation ≠ nearest_gene인 peak 행 선택
2. Send to IGV
3. IGV에서 확인:
   a. Gene track (GTF): peak 아래에 어떤 유전자 구조가 있는가?
   b. BigWig signal: Control vs Treatment 신호 차이가 명확한가?
   c. 좌우 유전자 TSS 위치: 어느 유전자가 더 가까운가?
```

**IGV에서 확인할 트랙 권장 구성:**

```
┌─────────────────────────────────────────────────────────────┐
│ [참조 게놈: mm10]                                            │
│ ─────────────────────────────────────────────────────────── │
│ Control_ATAC.bw   ████████                    (회색/파랑)    │
│ Treatment_ATAC.bw ████████████████████        (빨강/주황)    │
│ ─────────────────────────────────────────────────────────── │
│ RefSeq Genes      [Gene A ────────────────]                  │
│                            [Gene B ►──]                      │
│ ─────────────────────────────────────────────────────────── │
│ ATAC peaks (BED) ─────[peak]───────────────                  │
└─────────────────────────────────────────────────────────────┘
```

### 7.4 생물학적 해석 가이드

| annotation vs nearest_gene | 해석 |
|---------------------------|------|
| 동일 유전자 | Peak가 해당 유전자의 프로모터/바디에 있고 TSS도 가장 가까움 → 직접적 조절 요소 가능성 ↑ |
| 다른 유전자 | Peak가 큰 유전자의 intron에 물리적으로 걸쳐 있지만 다른 유전자를 조절하는 **enhancer** 가능성 ↑ |
| annotation: Intergenic | 유전자 바디와 겹치지 않는 원거리 조절 요소 |
| distance_to_tss < 2,000 bp | 프로모터 근접 접근성 변화 → 전사 직접 조절 가능성 |

> **downstream 분석**: annotation이 "Intergenic" 또는 "Intron"이면서 DA가 유의미한 경우,
> IGV에서 H3K27ac ChIP-seq 신호(있을 경우)와 비교하여 active enhancer 여부 확인을 권장합니다.

---

## 8. IGV Session 파일로 작업 환경 저장

자주 사용하는 트랙 구성(게놈 + BigWig 세트)을 IGV Session으로 저장하면  
매 실행 시 재설정 없이 복원할 수 있습니다.

### 8.1 Session 저장

```
IGV에서 모든 트랙 로드 완료 후:
File → Save Session → atac_analysis.xml
```

### 8.2 Session 로드

```
IGV 실행 후:
File → Load Session → atac_analysis.xml
```

또는 CMG-SeqViewer IGV Settings에서  
**Session File** 경로를 등록하면 "Load Session in IGV" 버튼으로 자동 복원 가능합니다.

### 8.3 권장 Session 구성

```xml
<!-- atac_analysis.xml (IGV가 자동 생성) -->
<Session genome="mm10">
    <Resources>
        <Resource path="/data/tracks/Control_rep1.bw" name="Control_rep1" color="68,114,196"/>
        <Resource path="/data/tracks/Control_rep2.bw" name="Control_rep2" color="68,114,196"/>
        <Resource path="/data/tracks/Treatment_rep1.bw" name="Treatment_rep1" color="255,0,0"/>
        <Resource path="/data/tracks/Treatment_rep2.bw" name="Treatment_rep2" color="255,0,0"/>
        <Resource path="/data/peaks/all_peaks.bed" name="All Peaks"/>
    </Resources>
</Session>
```

---

## 9. 문제 해결

### Q1. "IGV에 연결할 수 없습니다" 메시지가 뜹니다

**확인 순서:**

1. IGV가 실행 중인지 확인
2. `Tools → Preferences → Advanced → ☑ Enable port: 60151` 확인 후 IGV 재시작
3. 방화벽에서 localhost 60151 포트가 차단되어 있는지 확인
4. 브라우저에서 `http://127.0.0.1:60151/status` 접속 테스트
5. CMG-SeqViewer IGV Settings → Port 번호가 60151인지 확인

### Q2. IGV가 이동하지만 아무 신호가 안 보입니다

- BigWig 파일이 로드되어 있는지 확인 (`Load All Tracks in IGV Now`)
- IGV의 track height가 너무 작지 않은지 확인 (트랙 우클릭 → `Set Track Height`)
- 해당 영역의 reads depth가 낮은 실제 데이터 문제일 수 있음

### Q3. 염색체를 찾을 수 없다는 오류

- ATAC 데이터의 `chromosome` 컬럼 값 확인: `chr3` vs `3`
- BigWig 파일의 염색체 명명 방식 확인:  
  ```bash
  bigWigInfo sample.bw | grep "chromCount" -A 5
  ```
- IGV의 현재 게놈과 명명 방식이 다를 경우, `chr prefix` 토글 옵션 사용

### Q4. BigWig 트랙이 로드는 되지만 신호가 이상합니다

- 정규화 방법 확인: RPKM, CPM 등 샘플 간 일관성 있게 사용
- `extendReads` 값이 실제 library fragment 크기와 크게 다른지 확인  
  (ATAC-seq nucleosome-free region: 보통 150–200 bp)
- 샘플 간 시퀀싱 깊이 차이가 너무 크면 `--normalizeUsing RPKM` 대신 `--normalizeUsing CPM` 시도

### Q5. 데이터가 DE(RNA-seq)인데 Send to IGV가 메뉴에 없습니다

- IGV 연동은 **좌표 정보(chromosome, peak_start, peak_end)가 있는 ATAC-seq 데이터**에서만 활성화됩니다
- RNA-seq DE 데이터는 유전자 단위이며 좌표가 없어 해당 메뉴가 표시되지 않습니다

---

## 참고 자료

- [IGV Desktop Documentation](https://igv.org/doc/desktop/)
- [IGV HTTP Remote Control API](https://github.com/igvteam/igv/wiki/Controlling-IGV-through-a-Port)
- [deepTools bamCoverage](https://deeptools.readthedocs.io/en/develop/content/tools/bamCoverage.html)
- [HOMER Peak Annotation](http://homer.ucsd.edu/homer/ngs/annotation.html)

---

*최종 업데이트: 2026-04-30*
