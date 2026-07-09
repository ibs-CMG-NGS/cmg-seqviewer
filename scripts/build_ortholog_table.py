#!/usr/bin/env python
"""
build_ortholog_table.py — human 중심 1:1 ortholog long-format CSV 생성 (M2 데이터 조달).

CMG-SeqViewer의 cross-species 메타 분석(M2)은 비인간 데이터셋의 유전자를 human 심볼 공간으로
통일한 뒤 결합한다. 그 매핑 테이블을 Ensembl BioMart에서 한 번 생성해 리포에 번들한다.

인터넷 되는 환경에서 1회 실행:
    pip install pybiomart pandas
    python scripts/build_ortholog_table.py
    # 특정 종만:      python scripts/build_ortholog_table.py --species mouse macaque
    # 미러 호스트:    python scripts/build_ortholog_table.py --host http://useast.ensembl.org

출력: data/orthologs/ortholog_map.csv  (human 중심 long-format)
    species, source_ensembl, source_symbol, human_ensembl, human_symbol

설계 원칙 (META_ANALYSIS_PLAN.md M2):
  - long-format이라 종 추가 = SPECIES 딕셔너리에 한 줄(코드 무변경, 데이터만 확장).
  - 1:1 orthologs(ortholog_one2one)만 → 다대다 aggregation 회피, 노이즈 최소.
  - 영장류(macaque/marmoset)는 심볼 신뢰도가 낮아 매핑은 Ensembl ID(source_ensembl) 1순위.
    marmoset은 annotation이 약해 매핑 수가 상대적으로 적을 수 있음.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 종 라벨 → Ensembl BioMart homolog attribute prefix
# (종 추가 시 여기에 한 줄. prefix는 Ensembl 종 약어)
SPECIES = {
    'mouse':    'mmusculus',
    'rat':      'rnorvegicus',
    'macaque':  'mmulatta',    # Macaca mulatta (rhesus)
    'marmoset': 'cjacchus',    # Callithrix jacchus
}

DEFAULT_HOST = 'http://www.ensembl.org'
DEFAULT_OUT = 'data/orthologs/ortholog_map.csv'

_COLS = ['species', 'source_ensembl', 'source_symbol', 'human_ensembl', 'human_symbol']


def build(species: dict, out_path: Path, host: str, one2one_only: bool = True) -> None:
    import pandas as pd
    try:
        from pybiomart import Server
    except ImportError:
        sys.exit("pybiomart가 필요합니다.  pip install pybiomart pandas")

    print(f"Connecting to BioMart: {host}", flush=True)
    server = Server(host=host)
    human = server['ENSEMBL_MART_ENSEMBL']['hsapiens_gene_ensembl']

    frames = []
    for label, prefix in species.items():
        # human dataset에서 각 종의 homolog attribute를 조회 (biomaRt 표준 쿼리)
        attrs = [
            'ensembl_gene_id', 'external_gene_name',
            f'{prefix}_homolog_ensembl_gene',
            f'{prefix}_homolog_associated_gene_name',
            f'{prefix}_homolog_orthology_type',
        ]
        print(f"[{label}] querying orthologs ...", flush=True)
        df = human.query(attributes=attrs, use_attr_names=True)
        # 요청한 attribute 순서대로 컬럼이 반환됨 → 위치 기반 리네임
        df.columns = ['human_ensembl', 'human_symbol',
                      'source_ensembl', 'source_symbol', 'otype']

        df = df[df['source_ensembl'].notna() & (df['source_ensembl'].astype(str) != '')]
        if one2one_only:
            df = df[df['otype'] == 'ortholog_one2one']
        df = df[df['human_symbol'].notna() & (df['human_symbol'].astype(str) != '')]
        df['species'] = label

        frames.append(df[_COLS].copy())
        print(f"   {label}: {len(df):,} {'1:1 ' if one2one_only else ''}orthologs")

    if not frames:
        sys.exit("생성된 데이터가 없습니다. --species 인자를 확인하세요.")

    out = pd.concat(frames, ignore_index=True).drop_duplicates()
    out = out.sort_values(['species', 'human_symbol']).reset_index(drop=True)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)

    print(f"\nWrote {len(out):,} rows → {out_path}")
    print("species별 개수:")
    print(out.groupby('species').size().to_string())


def main():
    ap = argparse.ArgumentParser(
        description="Build human-centric 1:1 ortholog map (long-format) for cross-species meta (M2).")
    ap.add_argument('-o', '--out', default=DEFAULT_OUT, help=f"출력 CSV (기본: {DEFAULT_OUT})")
    ap.add_argument('--species', nargs='*',
                    help="대상 종 부분집합 (기본: 전체). 선택지: " + ', '.join(SPECIES))
    ap.add_argument('--host', default=DEFAULT_HOST,
                    help="BioMart 호스트 (느리면 http://useast.ensembl.org 등 미러)")
    ap.add_argument('--all-types', action='store_true',
                    help="1:1 외 ortholog(1:다/다:다)도 포함")
    args = ap.parse_args()

    if args.species:
        unknown = [s for s in args.species if s not in SPECIES]
        if unknown:
            sys.exit(f"알 수 없는 종: {unknown}. 선택지: {', '.join(SPECIES)}")
        species = {k: SPECIES[k] for k in args.species}
    else:
        species = SPECIES

    build(species, Path(args.out), args.host, one2one_only=not args.all_types)


if __name__ == '__main__':
    main()
