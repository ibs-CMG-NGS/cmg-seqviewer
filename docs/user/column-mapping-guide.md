# 📋 Column Mapping Guide

## 개요

RNA-Seq Analyzer는 다양한 형식의 Excel 데이터를 처리할 수 있도록 **컬럼 매핑** 기능을 제공합니다.

### 왜 필요한가요?

서로 다른 분석 도구나 파이프라인에서 생성된 데이터는 헤더 이름이 다를 수 있습니다:

```
# DESeq2 결과
Gene, log2FoldChange, pvalue, padj, baseMean

# edgeR 결과  
GeneID, logFC, PValue, FDR, logCPM

# 사용자 정의 파이프라인
symbol, fold_change, p.value, adj.p.value, avg_expr
```

이 프로그램은 이러한 다양한 형식을 **자동으로 감지**하고, 필요시 **사용자가 직접 매핑**할 수 있게 합니다.

---

## 🔄 작동 방식

### 1단계: 자동 감지

Excel 파일을 불러오면 프로그램이 자동으로 컬럼을 분석합니다:

**Differential Expression (DE) 데이터 인식 패턴:**
- `gene_id`: gene, gene_id, geneid, id, symbol, gene_symbol
- `log2fc`: log2fc, log2foldchange, logfc, fold_change, fc
- `pvalue`: pvalue, p.value, p_value, pval
- `adj_pvalue`: padj, adj.p.value, adj_p_value, fdr, q_value, qvalue
- `base_mean`: basemean, base_mean, mean, avg_expression

**GO Analysis 데이터 인식 패턴:**
- `term`: term, go_term, pathway, description, term_name
- `term_id`: term_id, go_id, pathway_id, id
- `gene_count`: gene_count, count, size, n_genes
- `pvalue`: pvalue, p.value, p_value, pval
- `fdr`: fdr, padj, adj.p.value, q_value, qvalue
- `genes`: genes, gene_list, geneid, gene_symbols

### 2단계: 필수 컬럼 확인

자동 감지 후 **필수 컬럼**이 모두 매핑되었는지 확인합니다:

**DE 데이터 필수 컬럼:**
- ✅ Gene ID (gene_id)
- ✅ log2 Fold Change (log2fc)
- ✅ Adjusted p-value (adj_pvalue)

**GO 데이터 필수 컬럼:**
- ✅ Term (term)
- ✅ Gene Count (gene_count)
- ✅ FDR (fdr)

### 3단계: 사용자 매핑 (필요 시)

필수 컬럼이 누락되었거나 자동 감지가 정확하지 않을 경우, **Column Mapping Dialog**가 열립니다.

---

## 🎨 Column Mapping Dialog 사용법

### 화면 구성

```
┌─────────────────────────────────────────────────────┐
│  📋 컬럼 매핑 설정                                   │
│  Excel 파일의 컬럼을 표준 컬럼명으로 매핑하세요.     │
├─────────────────────────────────────────────────────┤
│  데이터셋 타입: differential_expression              │
├─────────────────────────────────────────────────────┤
│  데이터 미리보기 (처음 5행)                          │
│  ┌────────┬──────────┬────────┬────────┐           │
│  │ Gene   │ logFC    │ PValue │ FDR    │           │
│  ├────────┼──────────┼────────┼────────┤           │
│  │ BRCA1  │ 2.5      │ 0.001  │ 0.01   │           │
│  │ TP53   │ -1.8     │ 0.005  │ 0.02   │           │
│  └────────┴──────────┴────────┴────────┘           │
├─────────────────────────────────────────────────────┤
│  컬럼 매핑                                          │
│  ┌──────────────┬──────────────┬──────────────┐   │
│  │ 표준 컬럼     │ Excel 컬럼   │ 미리보기      │   │
│  ├──────────────┼──────────────┼──────────────┤   │
│  │ 유전자 ID    │ [Gene ▼]     │ 예: BRCA1    │   │
│  │ log2FC       │ [logFC ▼]    │ 예: 2.5      │   │
│  │ adj.p-value  │ [FDR ▼]      │ 예: 0.01     │   │
│  └──────────────┴──────────────┴──────────────┘   │
│                                                     │
│  ☑ 이 매핑을 기본값으로 저장                        │
│                                                     │
│  [🔄 초기화]              [취소]  [✅ 확인]         │
└─────────────────────────────────────────────────────┘
```

### 사용 단계

#### 1️⃣ 데이터 미리보기
- 상단에서 실제 Excel 데이터의 처음 5행을 확인
- 어떤 컬럼이 어떤 데이터를 담고 있는지 파악

#### 2️⃣ 컬럼 매핑
각 표준 컬럼에 대해 Excel 컬럼을 선택합니다:

```
표준 컬럼: "유전자 ID (필수)"
  ↓ 선택
Excel 컬럼: "Gene" 또는 "GeneID" 등
  ↓ 미리보기
예: BRCA1
```

**Tip:**
- 자동 감지된 매핑이 있으면 이미 선택되어 있습니다
- 드롭다운에서 다른 컬럼으로 변경 가능
- 선택 시 오른쪽에 실제 데이터 미리보기가 표시됩니다

#### 3️⃣ 필수 필드 확인
필수 필드가 누락되면 경고가 표시됩니다:

```
⚠️ 필수 필드 누락

다음 필수 필드를 매핑해야 합니다:

• 유전자 ID (필수)
• log2 Fold Change (필수)

[확인]
```

#### 4️⃣ 매핑 저장 옵션
☑ **"이 매핑을 기본값으로 저장"** 체크 시:
- 이후 같은 형식의 파일은 자동으로 매핑됩니다
- 매핑은 `~/.rna_seq_analyzer/column_mappings.json`에 저장
- 다른 그룹의 데이터를 자주 사용한다면 유용합니다

---

## 💾 저장된 매핑 관리

### 저장 위치
```
Windows: C:\Users\{사용자}\.rna_seq_analyzer\column_mappings.json
```

### 파일 형식
```json
{
  "differential_expression": {
    "gene_id": "Gene",
    "log2fc": "logFC",
    "adj_pvalue": "FDR",
    "pvalue": "PValue",
    "base_mean": "AveExpr"
  },
  "go_analysis": {
    "term": "GO_Term",
    "fdr": "FDR",
    "gene_count": "Count"
  }
}
```

### 매핑 수정/삭제
저장된 매핑을 수정하려면:

1. **방법 1: 파일 직접 수정**
   ```
   column_mappings.json 파일을 텍스트 에디터로 열어서 수정
   ```

2. **방법 2: 파일 삭제 후 재생성**
   ```
   column_mappings.json 파일 삭제
   → 다음 데이터 로드 시 매핑 다이얼로그 다시 표시
   ```

---

## 📝 실전 예제

### 예제 1: DESeq2 결과 불러오기

**Excel 파일 구조:**
```
| Gene    | baseMean | log2FoldChange | lfcSE | stat  | pvalue  | padj    |
|---------|----------|----------------|-------|-------|---------|---------|
| BRCA1   | 1500.2   | 2.5            | 0.3   | 8.3   | 0.0001  | 0.001   |
| TP53    | 2300.5   | -1.8           | 0.2   | -9.0  | 0.00001 | 0.0001  |
```

**자동 매핑 결과:**
```
✅ gene_id      ← Gene
✅ log2fc       ← log2FoldChange  
✅ adj_pvalue   ← padj
✅ pvalue       ← pvalue
✅ base_mean    ← baseMean
```

→ 모든 필수 컬럼 매핑됨! 바로 사용 가능 ✅

---

### 예제 2: 다른 그룹의 분석 결과

**Excel 파일 구조:**
```
| symbol | FC   | p_val  | fdr    | expression |
|--------|------|--------|--------|------------|
| BRCA1  | 5.66 | 0.0001 | 0.001  | 1500.2     |
| TP53   | 0.29 | 0.0002 | 0.002  | 2300.5     |
```

**문제:** log2FC가 아닌 FC (Fold Change) 값!

**수동 매핑 필요:**

Column Mapping Dialog에서:
```
유전자 ID (필수)     → [symbol ▼]
log2 Fold Change     → [FC ▼]          ⚠️ 주의: log2 변환 필요!
Adjusted p-value     → [fdr ▼]
```

⚠️ **주의사항:**
- FC 값이 log2 변환되지 않은 경우 (예: 5.66), 직접 변환 필요
- 또는 Excel에서 `=LOG(FC, 2)` 계산 후 불러오기

---

### 예제 3: GO Enrichment 결과

**Excel 파일 구조:**
```
| GO_ID       | Description              | Count | PValue  | FDR     | Genes            |
|-------------|--------------------------|-------|---------|---------|------------------|
| GO:0008150  | biological_process       | 50    | 0.0001  | 0.001   | BRCA1,TP53,EGFR  |
| GO:0005575  | cellular_component       | 30    | 0.001   | 0.01    | MYC,KRAS         |
```

**자동 매핑 결과:**
```
✅ term_id      ← GO_ID
✅ term         ← Description
✅ gene_count   ← Count
✅ fdr          ← FDR
✅ pvalue       ← PValue
✅ genes        ← Genes
```

→ 자동 매핑 완료! ✅

---

## 🔍 필터링 모드

데이터 로드 후 두 가지 **독립적인** 필터링 방식을 사용할 수 있습니다:

### 1. 🧬 Gene List Filter

**사용 시나리오:**
- 특정 유전자 목록을 미리 알고 있을 때
- 다른 분석에서 얻은 유전자를 확인하고 싶을 때
- 문헌에서 찾은 유전자 세트를 검증하고 싶을 때

**작동 방식:**
```
입력된 유전자 리스트 ← (수동 입력 또는 파일 불러오기)
         ↓
Whole Dataset에서 검색
         ↓
매칭된 유전자만 새 시트에 표시
```

**예제:**
```
입력:
BRCA1
TP53
EGFR

결과:
┌──────┬────────┬────────┬────────┐
│ Gene │ log2FC │ pvalue │ padj   │
├──────┼────────┼────────┼────────┤
│ BRCA1│ 2.5    │ 0.001  │ 0.01   │
│ TP53 │ -1.8   │ 0.005  │ 0.02   │
│ EGFR │ 1.2    │ 0.01   │ 0.05   │
└──────┴────────┴────────┴────────┘
```

---

### 2. 📊 Statistical Filter

**사용 시나리오:**
- 통계적으로 유의한 유전자만 보고 싶을 때
- adj.p-value와 FC 기준으로 필터링하고 싶을 때
- Volcano plot 영역에 해당하는 유전자를 추출하고 싶을 때

**작동 방식:**
```
필터 조건:
- Adj. p-value ≤ 0.05
- |log₂FC| ≥ 1.0
         ↓
조건 만족 유전자만 새 시트에 표시
```

**예제:**
```
조건: padj ≤ 0.05, |log2FC| ≥ 1.0

결과:
┌──────┬────────┬────────┬────────┐
│ Gene │ log2FC │ pvalue │ padj   │
├──────┼────────┼────────┼────────┤
│ BRCA1│ 2.5    │ 0.001  │ 0.01   │  ✅ |2.5| ≥ 1.0 & 0.01 ≤ 0.05
│ TP53 │ -1.8   │ 0.005  │ 0.02   │  ✅ |-1.8| ≥ 1.0 & 0.02 ≤ 0.05
│ MYC  │ 0.5    │ 0.001  │ 0.001  │  ❌ |0.5| < 1.0
│ KRAS │ 3.0    │ 0.1    │ 0.2    │  ❌ 0.2 > 0.05
└──────┴────────┴────────┴────────┘
```

---

### 🔀 독립적(Exclusive) 작동

**중요:** 두 모드는 **동시에 사용되지 않습니다**!

UI에서 라디오 버튼으로 선택:
```
( ) 🧬 Gene List Filter
(●) 📊 Statistical Filter (p-value & FC)

→ 한 번에 하나만 활성화됩니다
```

**이유:**
- Gene List: "이 유전자들이 있는가?"
- Statistical: "어떤 유전자가 유의한가?"
- 목적이 다르므로 동시 적용은 의미 없음

---

## 💡 Best Practices

### ✅ DO

1. **첫 로드 시 미리보기 확인**
   ```
   데이터 미리보기를 보고 자동 매핑이 맞는지 확인
   ```

2. **매핑 저장 활용**
   ```
   같은 파이프라인의 결과를 자주 사용한다면
   "이 매핑을 기본값으로 저장" 체크
   ```

3. **필수 컬럼 확인**
   ```
   DE 분석: gene_id, log2fc, adj_pvalue
   GO 분석: term, gene_count, fdr
   ```

4. **로그 변환 주의**
   ```
   FC 값이 log2 변환되지 않았다면 Excel에서 미리 변환
   =LOG(FC값, 2)
   ```

### ❌ DON'T

1. **빈 컬럼 매핑하지 않기**
   ```
   데이터가 없는 컬럼을 억지로 매핑하지 마세요
   선택 안함(None)으로 두세요
   ```

2. **잘못된 컬럼 매핑**
   ```
   ❌ gene_id ← log2FC (데이터 타입 불일치)
   ✅ gene_id ← Gene
   ```

3. **두 필터 모드 동시 사용 시도**
   ```
   프로그램에서 방지하지만, 의도적으로 회피하지 마세요
   ```

---

## 🔧 문제 해결

### Q: "필수 필드를 매핑해야 합니다" 오류

**원인:** 필수 컬럼이 매핑되지 않음

**해결:**
```
1. Column Mapping Dialog에서 필수 필드 확인
2. Excel 파일에 해당 컬럼이 있는지 확인
3. 없다면: 데이터가 올바른 형식인지 확인
```

### Q: 자동 감지가 잘못된 컬럼을 선택함

**원인:** 비슷한 이름의 컬럼이 여러 개 있을 때

**해결:**
```
1. Column Mapping Dialog에서 수동으로 올바른 컬럼 선택
2. "이 매핑을 기본값으로 저장" 체크
```

### Q: 저장된 매핑을 초기화하고 싶음

**해결:**
```powershell
# Windows
del C:\Users\{사용자}\.rna_seq_analyzer\column_mappings.json
```

### Q: Gene List 필터가 작동하지 않음

**원인:** 대소문자 또는 공백 문제

**해결:**
```
1. 유전자 이름 양쪽 공백 제거
2. 프로그램은 대소문자 무시하므로 신경 쓰지 않아도 됨
3. 로그 패널에서 "matched" 개수 확인
```

### Q: Statistical 필터 결과가 없음

**원인:** 기준이 너무 엄격하거나 컬럼 매핑 오류

**해결:**
```
1. 필터 기준 완화 (예: padj ≤ 0.1, |FC| ≥ 0.5)
2. 로그 패널에서 "adj_pvalue", "log2fc" 컬럼 확인
3. 데이터 미리보기에서 실제 값 범위 확인
```

---

## 📚 관련 문서

- [README.md](../README.md) - 프로젝트 전체 설명
- [QUICK_START.md](QUICK_START.md) - 빠른 시작 가이드
- [DEVELOPMENT.md](DEVELOPMENT.md) - 개발 가이드

---

**Happy Analyzing!** 🧬✨
