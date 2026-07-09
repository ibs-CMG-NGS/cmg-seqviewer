# Ortholog mapping data (cross-species meta-analysis, M2)

`ortholog_map.csv.gz` — human 중심 1:1 ortholog long-format 매핑 테이블(gzip). CMG-SeqViewer의
cross-species 메타 분석(M2)이 비인간 데이터셋의 유전자를 human 심볼 공간으로 통일하는 데 쓴다.
(pandas `read_csv`가 `.gz`를 투명하게 읽음. 71,614행 / 4종, 압축 ~0.9 MB.)

## 포맷 (long)

```
species,   source_ensembl,      source_symbol, human_ensembl,   human_symbol
mouse,     ENSMUSG00000059552,  Trp53,         ENSG00000141510, TP53
macaque,   ENSMMUG00000...,     TP53,          ENSG00000141510, TP53
```

- `species` — 원본 종 라벨 (mouse / rat / macaque / marmoset / …)
- `source_ensembl`, `source_symbol` — 그 종의 Ensembl gene ID / 심볼
- `human_ensembl`, `human_symbol` — 대응 human ortholog (1:1)

long-format이라 **종 추가 = 데이터 행만 추가**(앱 코드 무변경).

## 생성 / 갱신

인터넷 되는 환경에서 1회:

```bash
pip install pybiomart pandas
python scripts/build_ortholog_table.py                 # 전체 종
python scripts/build_ortholog_table.py --species mouse macaque
python scripts/build_ortholog_table.py --host http://useast.ensembl.org   # 미러
```

출처: Ensembl BioMart (`hsapiens_gene_ensembl`의 종별 homolog attribute, `ortholog_one2one` 필터).

## 주의

- **영장류(macaque/marmoset)**: 심볼 신뢰도가 낮아 앱의 매핑은 `source_ensembl`(Ensembl ID) 1순위.
  marmoset은 annotation이 약해 1:1 매핑 수가 상대적으로 적을 수 있다.
- 이 CSV는 앱 배포물(PyInstaller)에 번들되어야 frozen 빌드에서 로드된다 (`*.spec`의 `datas`).
