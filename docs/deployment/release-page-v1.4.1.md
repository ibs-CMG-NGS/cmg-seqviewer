## CMG-SeqViewer v1.4.1

단일세포 발현 **분포(violin/box)** 뷰와 scRNA-seq 파이프라인의
`expression_distribution` 번들 지원을 추가한 패치 릴리스입니다.

### 주요 추가

- **Gene Expression Distribution 뷰**
  - 메뉴: `Visualization → Single-cell RNA-seq → Gene Expression Distribution`
  - pseudobulk의 sample/replicate 값으로 **Violin / Box / Strip / Box + points**
  - **Condition / Dataset / Sample** 기준 그룹 표시
  - gene 검색 및 다중 gene 패널
  - cell type은 기본 **Top 10 by mean**, Top 10 / Select all / Clear 제공
  - **Min n_cells**, **Min % expressing**, log-scale y축
  - **Export Data / Save Figure / Export Bundle / Pin to Tab**

- **`expression_distribution` 데이터 타입**
  - per-sample **pseudobulk** 및 **quantile summary** long-format 지원
  - `distribution_schema`에 layout, sample/condition 컬럼, `sample_unit`,
    `pct_scale`, value definition, companion 파일 정의
  - `sample_count`, `gene_index`, `cell_type_summary` 메타데이터 저장
  - `*_pseudobulk.parquet` + companion 세트는 manifest 없이도 자동 감지

- **CLI 지원**
  - `cmg-seqviewer-cli load <pseudobulk.parquet> --type expression_distribution --json`
  - `cell_type` + `mean_expression` + `sample`/quantile 컬럼 기반 자동 감지

- **문서**
  - F1 도움말 **21. Expression Distribution (Violin/Box)** 추가
  - 이후 섹션 재번호: Expression Summary 22, Tips 23, FAQ 24
  - `docs/developer/pipeline-integration.md` §9.9에 parquet/manifest 규격 추가

### 변경 및 수정

- `*_pseudobulk.parquet` 자동 감지 시 `gene_id`, `cell_type`, `sample`,
  `mean_expression` 필수 컬럼을 검증하도록 수정
- distribution companion 파일을 import 시 함께 복사하고, manifest의 파일명을
  실제 저장 파일명으로 갱신
- full bundle에서 distribution companion이 별도 데이터셋으로 중복 등록되지
  않도록 companion claim 처리 통합
- Expression Distribution 다이얼로그에서 gene/cell type을 모두 해제하면
  빈 플롯 대신 안내 문구 표시
- 여러 gene을 선택한 경우 마지막 패널에만 cell-type x축 라벨 표시

### 데이터/번들 호환성

- 분석팀 pilot bundle 기준:
  - distribution 단독 번들: **1/1 import**
  - 전체 번들: analysis 69 + distribution 1 = **70/70 import**
- **v1.4.0 이하** viewer는 `expression_distribution` entry를 건너뜁니다.
  새 번들을 사용하려면 **v1.4.1 이상**이 필요합니다.
- `layout: "quantile"` 입력은 cell-level 값이 없으므로 violin 대신 box/range로
  표시됩니다.
- v1은 dataset 단위 로드(최대 5,000,000행)입니다. 전체 atlas는 dataset별 분할
  또는 선택 gene panel export를 권장합니다.

### 업그레이드

1. 아래 설치 파일을 내려받아 기존 설치를 교체합니다.
   - `CMG-SeqViewer-Windows.zip`
   - `CMG-SeqViewer-macOS.dmg`
2. 기존 데이터베이스는 그대로 사용할 수 있습니다. 새 distribution 번들은
   **Import Folder**로 추가하거나 `data/datasets/`에 넣은 뒤 **Refresh**합니다.
3. v1.4.0에서 만든 기존 `expression_summary`/`composition` 번들은 변경 없이
   사용할 수 있습니다.

### 검증

- 테스트: **354 passed, 4 deselected** (4개는 live-network 테스트)
- `mkdocs build --strict` 성공
- pilot bundle SHA256 checksum 검증 완료
- distribution dataset 로드 시 `gene_index`, `cell_type_summary` companion 확인
- offscreen 다이얼로그 smoke test 및 figure export 확인

### 알려진 제한

- 조건 간 통계 검정은 포함하지 않습니다. pseudobulk DE 결과를 별도로 사용하세요.
- cell-level on-demand 분포 데이터는 포함되지 않습니다.
- 전체 atlas용 lazy DuckDB query는 v2 계획입니다.
- quantile 입력은 violin을 지원하지 않습니다.

### 관련 문서

- [Expression Distribution 도움말](https://github.com/ibs-CMG-NGS/cmg-seqviewer/blob/master/docs/user/help/21-expression-distribution.md)
- [Pipeline integration §9.9](https://github.com/ibs-CMG-NGS/cmg-seqviewer/blob/master/docs/developer/pipeline-integration.md#99-expression-distribution-parquet-%EA%B7%9C%EA%B2%A9-expression_distribution)
- [v1.4.1 릴리스 노트](https://github.com/ibs-CMG-NGS/cmg-seqviewer/blob/master/docs/deployment/release-notes-v1.4.1.md)

### 전체 변경

- PR: https://github.com/ibs-CMG-NGS/cmg-seqviewer/pull/10
- Compare: https://github.com/ibs-CMG-NGS/cmg-seqviewer/compare/v1.4.0...v1.4.1
