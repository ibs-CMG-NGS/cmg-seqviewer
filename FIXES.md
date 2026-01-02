# 수정 사항

## 문제 2: gene_id와 symbol 중복 문제

**원인**: 원본 Excel 파일에 'gene_id' 헤더가 없고 첫 번째 열이 바로 ENSMUSG... 형식의 ID로 시작
- 프로그램이 이를 'symbol' 컬럼으로 매핑
- comparison 로직에서 symbol을 gene_id로도 복사하여 중복 발생

**해결 방법**:
1. Excel 파일 첫 번째 열의 헤더를 'gene_id'로 명시 (권장)
2. 또는 프로그램에서 ENSMUSG 패턴을 감지하여 자동으로 gene_id로 인식

## 문제 3: Filtering 결과 탭 이름

**현재**: 새로운 탭 이름이 "Dataset1_filtered" 형식
**요청**: "Filtered: Dataset1" 형식으로 변경

## 문제 4: statistics comparison시 nan 값

**원인**: 컬럼 이름 불일치
- Excel: 'log2FoldChange' 
- Comparison 탭 검색: 'log2FC'

**해결**: 컬럼 이름 매핑 로직 수정
