CMG-SeqViewer External Data Folder
================================================================================

이 폴더는 CMG-SeqViewer에서 사용할 pre-loaded dataset을 저장하는 곳입니다.

사용 방법:
-----------
1. Parquet 파일(.parquet)을 datasets/ 폴더에 복사합니다.
2. 앱을 재시작하거나 Database Browser에서 "Refresh" 버튼을 클릭합니다.
3. Database Browser에서 자동으로 인식되어 사용할 수 있습니다.

폴더 구조:
-----------
data/
├── README.txt          (이 파일)
├── datasets/           (Parquet 파일을 여기에 추가)
│   ├── example1.parquet
│   ├── example2.parquet
│   └── ...
└── metadata.json       (자동 생성됨)

주의사항:
-----------
- 파일명은 영문/숫자 권장 (한글 가능하나 호환성 고려)
- Parquet 파일만 인식됩니다 (.parquet 확장자)
- 메타데이터(dataset 이름, 설명)는 자동으로 생성됩니다
- metadata.json은 수동으로 편집 가능합니다

파일 형식:
-----------
- Differential Expression (DE) 분석 결과
- GO/KEGG Enrichment 분석 결과
→ 자동으로 타입이 감지됩니다

문제 해결:
-----------
- 파일이 인식되지 않으면: Refresh 버튼 클릭
- 메타데이터가 잘못되었으면: metadata.json 삭제 후 재시작
- 더 많은 정보: https://github.com/ibs-CMG-NGS/cmg-seqviewer

================================================================================
