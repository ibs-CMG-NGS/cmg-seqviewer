"""
Cross-species ortholog mapper (M2).

비인간 데이터셋의 유전자(gene_id/symbol)를 human 심볼 공간으로 통일해, 종이 다른 DE 결과를
하나의 메타 분석으로 합칠 수 있게 한다. 매핑은 번들 테이블
`data/orthologs/ortholog_map.csv.gz`(human 중심 1:1 ortholog, long-format)를 사용한다.

파이프라인 상 위치(META_ANALYSIS_PLAN.md M2): DE 결합(M1/M5) **직전의 선행 정렬(late mapping)**.
매핑이 곧 종간 JOIN 키를 정의하므로, 매핑 후에는 기존 결합 로직이 그대로 동작한다.

매핑 원칙:
  - Ensembl gene_id 기반이 1순위(특히 영장류는 심볼 신뢰도 낮음), 실패 시 symbol 폴백.
  - 1:1 ortholog만(테이블 자체가 1:1). 매핑 실패 유전자는 제외하고 개수를 보고한다.
"""
import sys
from pathlib import Path

import pandas as pd

# gene_id 접두사 → 종 (exact prefix; 종 추가 시 여기에 한 줄)
_PREFIX_ORG = [
    ('ENSMUSG', 'mouse'),
    ('ENSRNOG', 'rat'),
    ('ENSMMUG', 'macaque'),
    ('ENSCJAG', 'marmoset'),
    ('ENSG',    'human'),
]

# metadata['organism'] 문자열 매칭
_ORG_KEYWORDS = {
    'homo': 'human', 'sapiens': 'human', 'human': 'human',
    'musculus': 'mouse', 'mouse': 'mouse', 'mus ': 'mouse',
    'norvegicus': 'rat', 'rattus': 'rat', 'rat': 'rat',
    'mulatta': 'macaque', 'macaca': 'macaque', 'rhesus': 'macaque', 'macaque': 'macaque',
    'jacchus': 'marmoset', 'callithrix': 'marmoset', 'marmoset': 'marmoset',
}


def _default_map_path() -> Path:
    """번들 ortholog 테이블 경로 (frozen=_MEIPASS, dev=repo/data)."""
    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent.parent
    return base / 'data' / 'orthologs' / 'ortholog_map.csv.gz'


class OrthologMapper:
    """long-format ortholog 테이블 기반 종간 → human 매퍼 (지연 로드)."""

    def __init__(self, path=None):
        self._path = Path(path) if path else _default_map_path()
        self._table = None
        self._by_ens = {}   # species → DataFrame(index=source_ensembl)[human_ensembl, human_symbol]
        self._by_sym = {}   # species → DataFrame(index=source_symbol)[human_ensembl, human_symbol]

    def available(self) -> bool:
        return self._path.exists()

    def _load(self):
        if self._table is not None:
            return
        if not self._path.exists():
            raise FileNotFoundError(f"ortholog map not found: {self._path}")
        t = pd.read_csv(self._path)   # pandas가 .gz 자동 해제
        self._table = t
        for sp, g in t.groupby('species'):
            self._by_ens[sp] = (g.dropna(subset=['source_ensembl'])
                                .drop_duplicates('source_ensembl')
                                .set_index('source_ensembl')[['human_ensembl', 'human_symbol']])
            gs = g.dropna(subset=['source_symbol'])
            self._by_sym[sp] = (gs.drop_duplicates('source_symbol')
                                .set_index('source_symbol')[['human_ensembl', 'human_symbol']])

    def species(self) -> list:
        self._load()
        return sorted(self._table['species'].unique())

    @staticmethod
    def detect_organism(df, metadata=None):
        """데이터셋의 종을 추정. metadata['organism'] 우선, 없으면 gene_id 접두사."""
        if metadata:
            org = str(metadata.get('organism', '')).lower()
            for kw, o in _ORG_KEYWORDS.items():
                if kw in org:
                    return o
        if df is not None and 'gene_id' in df.columns:
            s = df['gene_id'].astype(str).head(300)
            if len(s):
                for pfx, o in _PREFIX_ORG:
                    if s.str.startswith(pfx).mean() > 0.3:
                        return o
        return None

    def map_to_human(self, df, species):
        """비인간 df의 gene_id/symbol을 human ortholog로 치환.

        Returns:
            (mapped_df, stats). stats: species, n_in, mapped, unmapped[, no_table].
            human이거나 매핑 불가면 원본 그대로/일부 반환.
        """
        if df is None or df.empty:
            return df, {'species': species, 'n_in': 0, 'mapped': 0, 'unmapped': 0}
        if species == 'human':
            n = len(df)
            return df, {'species': 'human', 'n_in': n, 'mapped': n, 'unmapped': 0}
        self._load()
        if species not in self._by_ens:
            return df, {'species': species, 'n_in': len(df), 'mapped': 0,
                        'unmapped': len(df), 'no_table': True}

        res = df.copy()
        hs = pd.Series(pd.NA, index=res.index, dtype=object)   # human_symbol
        he = pd.Series(pd.NA, index=res.index, dtype=object)   # human_ensembl

        # 1순위: gene_id(Ensembl) 매핑
        ens = self._by_ens[species]
        if 'gene_id' in res.columns:
            gid = res['gene_id'].astype(str)
            hs = gid.map(ens['human_symbol'])
            he = gid.map(ens['human_ensembl'])

        # 폴백: 남은 것은 symbol로 매핑
        sym = self._by_sym.get(species)
        if sym is not None and 'symbol' in res.columns:
            miss = hs.isna()
            if miss.any():
                sm = res.loc[miss, 'symbol'].astype(str)
                hs.loc[miss] = sm.map(sym['human_symbol'])
                he.loc[miss] = sm.map(sym['human_ensembl'])

        mapped = hs.notna()
        n_in, n_map = len(res), int(mapped.sum())
        res = res[mapped].copy()
        res['symbol'] = hs[mapped].to_numpy()
        res['gene_id'] = he[mapped].to_numpy()
        return res, {'species': species, 'n_in': n_in, 'mapped': n_map,
                     'unmapped': n_in - n_map}
