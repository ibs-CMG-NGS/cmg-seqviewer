CMG-SeqViewer External Data Folder
================================================================================

이 폴더는 CMG-SeqViewer에서 사용할 pre-loaded dataset을 저장하는 곳입니다.

사용 방법:
-----------
**중요: Parquet 파일과 metadata.json을 함께 복사해야 합니다!**

1. 소스 데이터베이스 폴더에서:
   - `datasets/*.parquet` 파일들을 이 폴더의 `datasets/`로 복사
   - `metadata.json` 파일을 이 폴더로 복사 (기존 파일과 병합 필요 시 수동 편집)

2. 앱을 재시작하거나 Database Browser에서 "Refresh" 버튼을 클릭합니다.

3. Database Browser에서 자동으로 인식되어 사용할 수 있습니다.

예시:
-----------
소스 database 폴더:
  database/
  ├── datasets/
  │   ├── dataset1.parquet
  │   ├── dataset2.parquet
  │   └── dataset3.parquet
  └── metadata.json

복사 후 data 폴더:
  data/
  ├── datasets/
  │   ├── dataset1.parquet  ← 복사됨
  │   ├── dataset2.parquet  ← 복사됨
  │   └── dataset3.parquet  ← 복사됨
  ├── metadata.json         ← 복사됨 (해당 dataset 정보 포함)
  └── README.txt

폴더 구조:
-----------
data/
├── README.txt          (이 파일)
├── datasets/           (Parquet 파일을 여기에 추가)
│   ├── *.parquet
│   └── ...
└── metadata.json       (필수! 데이터셋 정보 포함)

주의사항:
-----------
- **Parquet 파일만 복사하면 인식되지 않습니다!**
- metadata.json에 해당 파일의 정보가 있어야 합니다
- 파일명은 영문/숫자 권장 (한글 가능하나 호환성 고려)
- 중복된 dataset_id가 있으면 하나만 로드됩니다 (우선순위: data > database)

metadata.json 병합 방법:
-----------
1. 기존 data/metadata.json 열기
2. 소스 database/metadata.json에서 필요한 dataset 항목 복사
3. data/metadata.json의 "datasets" 배열에 추가
4. JSON 형식이 올바른지 확인 (중괄호, 쉼표 등)

또는:
-----------
소스 database/metadata.json을 그대로 data/metadata.json으로 복사
(기존 파일이 덮어씌워지므로 주의!)

문제 해결:
-----------
- 파일이 인식되지 않으면: metadata.json 확인
- Parquet 파일만 있고 metadata가 없으면: 경고 메시지 출력됨
- 중복 데이터셋이 있으면: 하나만 로드됨 (data 폴더 우선)
- 더 많은 정보: https://github.com/ibs-CMG-NGS/cmg-seqviewer

================================================================================
