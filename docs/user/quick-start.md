# CMG-SeqViewer 빠른 시작 가이드 (Quick Start)

> ⚡ 5분 만에 첫 RNA-seq 분석 완료하기

## 📋 이 가이드의 목표

이 가이드를 마치면:
- ✅ CMG-SeqViewer 실행 방법 이해
- ✅ 첫 데이터셋 로드 완료
- ✅ Volcano Plot 생성 경험
- ✅ 필터링 및 Export 기능 사용

**소요 시간**: 약 5분

---

## 1단계: 프로그램 실행 (30초)

### Windows

```powershell
# 방법 1: 실행 파일 더블클릭
# CMG-SeqViewer.exe 찾아서 더블클릭

# 방법 2: 바탕화면 바로가기 (만들었다면)
# 바로가기 더블클릭

# 방법 3: 개발 모드
cd C:\path\to\cmg-seqviewer
.\venv\Scripts\python.exe src\main.py
```

### macOS

```bash
# 방법 1: Finder에서 실행
# Applications → CMG-SeqViewer 더블클릭

# 방법 2: 터미널
open /Applications/CMG-SeqViewer.app

# 방법 3: 개발 모드
cd /path/to/cmg-seqviewer
./venv/bin/python src/main.py
```

**확인**: 메인 윈도우가 열리면 성공!

---

## 2단계: 샘플 데이터 준비 (1분)

### 옵션 A: 자신의 데이터 사용

**필요한 Excel 파일 형식**:
- **필수 컬럼**: 
  - 유전자 ID (gene_id, gene_name, symbol 등)
  - Log2 Fold Change (log2FC, logFC 등)
  - 조정 p-value (adj.p.value, padj, FDR 등)

**예시**:
| gene_id | log2FC | adj.p.value |
|---------|--------|-------------|
| GAPDH   | 2.5    | 0.001       |
| TP53    | -1.8   | 0.01        |
| ACTB    | 0.5    | 0.8         |

### 옵션 B: 테스트 데이터 생성

간단한 테스트 데이터를 Excel로 만들어보세요:

```
gene_id    log2FC    adj.p.value
Gene1      2.1       0.001
Gene2      -1.5      0.01
Gene3      3.2       0.0001
Gene4      0.3       0.5
Gene5      -2.8      0.005
```

Excel에 복사 → `test_data.xlsx`로 저장

---

## 3단계: 데이터 로드 (1분)

### 파일 열기

**방법 1: 메뉴 사용**
1. 상단 메뉴 → **File** → **Import Dataset**
2. Excel 파일 선택 (`*.xlsx`, `*.xls`)
3. **OK** 클릭

**방법 2: 드래그 앤 드롭**
1. Excel 파일을 CMG-SeqViewer 창으로 드래그
2. 자동으로 Import 다이얼로그 열림

### Import 다이얼로그

**설정 항목**:
1. **Dataset Name**: 데이터셋 이름 입력 (예: "Test_DE")
2. **Data Type**: "Differential Expression" 선택
3. **Sheet**: Excel 시트 선택 (보통 첫 번째)
4. **Column Mapping**: 자동 감지 확인
   - Gene ID → gene_id 컬럼
   - Log2FC → log2FC 컬럼
   - Adj.P-Value → adj.p.value 컬럼

**확인**: Preview 섹션에서 데이터 확인 → **Import** 클릭

### 결과

- 새 탭 생성: "Test_DE"
- 데이터 테이블 표시
- 하단 로그: "Dataset loaded successfully"

---

## 4단계: 필터링 (1분)

### 기본 필터 적용

왼쪽 **Filter Panel**에서:

1. **Adj.P-Value Threshold**
   - 슬라이더를 0.05로 설정
   - 또는 텍스트 박스에 "0.05" 입력

2. **Log2FC Threshold**
   - 슬라이더를 1.0으로 설정
   - 또는 텍스트 박스에 "1.0" 입력

3. **Regulation Direction**
   - "Both" 선택 (Up + Down)
   - 또는 "Up-regulated only" (증가만)
   - 또는 "Down-regulated only" (감소만)

4. **Apply Filter** 버튼 클릭

### 결과 확인

- 새 탭 생성: "Test_DE:Filtered"
- 필터링된 유전자만 표시
- 상단 상태바: "Showing X of Y genes"

**팁**: 
- Filter Panel은 언제든지 토글 가능 (View → Toggle Filter Panel)
- 필터는 원본 데이터를 변경하지 않음

---

## 5단계: Volcano Plot 생성 (1분)

### Plot 생성

1. 상단 메뉴 → **Visualization** → **Volcano Plot**
2. Volcano Plot 다이얼로그 열림

### 설정 확인

**기본 설정** (그대로 사용):
- **X-axis**: log2FC
- **Y-axis**: -log10(adj.p.value)
- **Point size**: 50
- **Alpha**: 0.6
- **Thresholds**:
  - Adj.P < 0.05 (빨간 수평선)
  - |log2FC| > 1 (파란 수직선)

### Plot 표시

1. **Generate** 버튼 클릭
2. 새 창에 Volcano Plot 표시

### Plot 해석

**색상 의미**:
- 🔴 **빨간색**: 유의미하게 증가 (adj.p < 0.05, log2FC > 1)
- 🔵 **파란색**: 유의미하게 감소 (adj.p < 0.05, log2FC < -1)
- ⚫ **회색**: 유의미하지 않음

**상호작용**:
- **마우스 오버**: 유전자 이름 표시
- **확대/축소**: 마우스 휠 또는 툴바
- **이동**: 클릭 후 드래그
- **저장**: 툴바의 💾 아이콘

---

## 6단계: 결과 Export (30초)

### 필터링된 데이터 내보내기

1. "Test_DE:Filtered" 탭 선택
2. 상단 메뉴 → **File** → **Export Current Tab**
3. 저장 위치 선택
4. 파일 형식 선택:
   - **Excel** (.xlsx) - 권장
   - **CSV** (.csv)
   - **TSV** (.tsv)
5. **Save** 클릭

### 확인

- 저장된 파일 열어보기
- 필터링된 유전자만 포함
- 원본 데이터와 비교

---

## 🎉 완료!

축하합니다! 첫 RNA-seq 분석을 완료했습니다.

### 배운 내용 요약

✅ **데이터 로드**: Excel → Import Dataset  
✅ **필터링**: adj.p < 0.05, |log2FC| > 1  
✅ **시각화**: Volcano Plot 생성  
✅ **Export**: 결과를 Excel로 저장

---

## 🚀 다음 단계

### 추가 기능 탐색

**시각화**:
- **Heatmap**: Visualization → Heatmap (클러스터링 포함)
- **P-adj Histogram**: 분포 확인
- **Venn Diagram**: 여러 데이터셋 비교

**필터링**:
- **Gene List**: 특정 유전자만 필터링
- **Re-filtering**: 필터링된 데이터를 다시 필터링
- **Filter Presets**: 자주 사용하는 필터 저장 (작성 예정)

**비교 분석**:
- **Multi-dataset Comparison**: Analysis → Compare Datasets
- 2-5개 데이터셋 동시 비교
- Venn Diagram으로 교집합 확인

**GO/KEGG 분석**:
- GO/KEGG 결과 Excel 로드 (Data Type: GO/KEGG)
- GO/KEGG → Clustering (Jaccard, Kappa)
- GO/KEGG → Network Visualization

**통계 분석**:
- **Fisher's Exact Test**: Analysis → Fisher's Exact Test
- **GSEA Lite**: Gene set enrichment
- Custom gene sets (.gmt 파일)

### 튜토리얼 (상세)

1. [Heatmap 생성 튜토리얼](user-guide.md#heatmap) (작성 예정)
2. [GO Clustering 튜토리얼](user-guide.md#go-clustering) (작성 예정)
3. [Multi-dataset 비교](user-guide.md#comparison) (작성 예정)

---

## 💡 팁과 트릭

### 효율적인 워크플로우

**바로가기 키**:
- `Ctrl+O`: Import Dataset
- `Ctrl+S`: Export Current Tab
- `Ctrl+W`: 탭 닫기
- `F1`: 도움말

**데이터셋 관리**:
- Dataset Manager (우측 패널)에서 데이터셋 전환
- 더블클릭으로 데이터셋 이름 변경
- 우클릭으로 삭제

**필터 재사용**:
- 같은 필터를 여러 데이터셋에 적용
- Filter Panel 설정은 유지됨
- 다른 탭으로 전환 후 "Apply Filter" 다시 클릭

### 일반적인 워크플로우

```
1. Import Dataset (Ctrl+O)
   ↓
2. Apply Filter (adj.p < 0.05, |log2FC| > 1)
   ↓
3. Generate Volcano Plot
   ↓
4. Identify interesting genes
   ↓
5. Re-filter with gene list
   ↓
6. Generate Heatmap
   ↓
7. Export results (Ctrl+S)
```

---

## ❓ 자주 묻는 질문

### Q1: 컬럼이 자동 매핑 안 돼요

**A**: Column Mapping 다이얼로그에서 수동 선택
- Gene ID 드롭다운 → 유전자 컬럼 선택
- Log2FC 드롭다운 → fold change 컬럼 선택
- Adj.P-Value 드롭다운 → p-value 컬럼 선택

자세한 내용: [컬럼 매핑 가이드](COLUMN_MAPPING_GUIDE.md)

### Q2: Volcano Plot에 점이 너무 많아요

**A**: 필터링 먼저 적용
1. Filter Panel에서 adj.p < 0.05 설정
2. "Apply Filter" 클릭
3. Filtered 탭에서 Volcano Plot 생성

### Q3: 여러 데이터셋 비교는?

**A**: Multi-dataset Comparison 사용
1. 2개 이상 데이터셋 로드
2. Analysis → Compare Datasets
3. 비교할 데이터셋 선택 (최대 5개)
4. Venn Diagram 또는 Upset Plot 생성

### Q4: 내 컴퓨터에서만 실행 가능한가요?

**A**: USB나 네트워크에서도 실행 가능 (Portable 버전)
- 폴더 전체를 USB에 복사
- 어디서나 실행 가능
- 설치 불필요

---

## 🔗 관련 문서

### 초보자용
- [설치 가이드](installation.md) - 프로그램 설치
- [사용자 매뉴얼](user-guide.md) - 전체 기능 설명 (작성 예정)
- [컬럼 매핑 가이드](COLUMN_MAPPING_GUIDE.md) - 데이터 임포트

### 고급 사용자용
- [GO/KEGG 분석](user-guide.md#go-kegg) (작성 예정)
- [통계 분석](user-guide.md#statistics) (작성 예정)
- [커스터마이징](user-guide.md#customization) (작성 예정)

### 문제 해결
- [FAQ](faq.md) - 자주 묻는 질문 (작성 예정)
- [문제 해결](troubleshooting.md) - 일반적인 문제 (작성 예정)
- [GitHub Issues](https://github.com/ibs-CMG-NGS/cmg-seqviewer/issues)

---

## 📞 도움말

### 프로그램 내 도움말

- **F1** 키 → 종합 도움말 다이얼로그
- **Help** → **Documentation** → 전체 기능 설명
- **Help** → **About** → 버전 정보

### 커뮤니티 지원

- [GitHub Discussions](https://github.com/ibs-CMG-NGS/cmg-seqviewer/discussions)
- [GitHub Issues](https://github.com/ibs-CMG-NGS/cmg-seqviewer/issues)

---

**다음**: [사용자 매뉴얼](user-guide.md)로 더 많은 기능 배우기 (작성 예정)

**마지막 업데이트**: 2026-03-01  
**버전**: v1.2.0
