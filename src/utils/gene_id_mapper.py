"""
SymbolMapper — 심볼 → Entrez Gene ID 매핑 (plan §6.7, G9).

오프라인 약속(plan §2 원칙 2 / G9): 1차는 NCBI gene_info 로컬 캐시
(`CacheManager.ensure_gene_info(organism)` → taxid 필터된 gzipped TSV:
`tax_id, GeneID, Symbol, Synonyms, ...`)에서 매핑하고, 로컬에서 못 찾은
심볼만 mygene 온라인 fallback으로 조회한다. mygene 실패는 절대 크래시/가짜
성공으로 이어지지 않고 경고 후 None 처리한다(G13).

- 종별 casing(A6): human=UPPER, mouse=Title(`str.title()`). 입력과 gene_info
  양쪽에 같은 함수를 적용하므로 대소문자 변형이 서로 매칭된다.
- gene_info의 `Symbol` 컬럼과 `Synonyms` 컬럼(파이프 구분 별칭) 둘 다
  정규화하여 GeneID에 매핑(mouse alias 예: Tp73 → Trp73, P0-7 발견).
- 빌드된 로컬 맵은 `cache_dir/mapping/<taxid>.pickle`로 저장하고, 옆에
  `<taxid>.pickle.sha256` 사이드카(원본 gene_info의 sha256)를 기록한다.
  사이드카 sha256이 원본과 일치할 때만 pickle을 재사용하고, 불일치 시 재빌드.
- 매핑 0건은 여기서 raise하지 않는다(분석기에서 ErrorKind.MAPPING 처리, G14).
"""
from pathlib import Path
from typing import Dict, List, Optional
import logging
import os
import pickle

import pandas as pd

# species → NCBI taxid (plan §6.7: human|mouse만 지원)
_ORGANISM_TAXID = {
    "human": 9606,
    "mouse": 10090,
}


class SymbolMapper:
    """symbol → Entrez 로컬(gene_info) + mygene fallback 매퍼 (plan §6.7, G9)."""

    def __init__(self, cache_manager, organism: str = "human", logger=None):
        if organism not in _ORGANISM_TAXID:
            raise ValueError(
                f"unsupported organism: {organism!r} (supported: {sorted(_ORGANISM_TAXID)})"
            )
        self._cache = cache_manager
        self.organism = organism
        self.taxid = _ORGANISM_TAXID[organism]
        self._logger = logger or logging.getLogger(__name__)
        self._map: Optional[Dict[str, int]] = None
        self._loaded_sha: Optional[str] = None
        self._reverse: Optional[Dict[int, str]] = None  # lazy: Entrez -> primary normalized symbol
        self._mygene = None  # lazy: mygene.MyGeneInfo

    # ------------------------------------------------------------------ API

    def normalize_symbol(self, symbol: str) -> str:
        """종별 casing(A6): human → UPPER, mouse → Title (str.title())."""
        s = symbol.strip()
        if self.taxid == 10090:
            return s.title()
        return s.upper()

    def cache_file(self) -> Path:
        """로컬 매핑 pickle 경로: cache_dir/mapping/<taxid>.pickle."""
        return self._cache.cache_dir / "mapping" / f"{self.taxid}.pickle"

    def map_symbols(self, symbols: List[str]) -> Dict[str, Optional[int]]:
        """정규화 심볼 → Entrez Gene ID(int) 또는 None.

        결과 키는 정규화된 입력 심볼이며, 정규화 심볼 기준으로 dedupe한다.
        로컬(gene_info)에서 못 찾은 심볼만 mygene fallback으로 조회한다.
        """
        if not symbols:
            return {}
        normalized = []
        seen = set()
        for symbol in symbols:
            norm = self.normalize_symbol(symbol)
            if norm and norm not in seen:
                seen.add(norm)
                normalized.append(norm)

        mapping = self._load_map()
        result: Dict[str, Optional[int]] = {norm: mapping.get(norm) for norm in normalized}
        missing = [norm for norm, gid in result.items() if gid is None]
        if missing:
            for norm, gid in self._query_mygene(missing).items():
                if norm in result:
                    result[norm] = gid
        return result

    def mapped_entrez(self, symbols: List[str]) -> List[int]:
        """편의 API: 매핑된 Entrez id 목록(입력 순서, 값 기준 dedupe)."""
        seen: set = set()
        out: List[int] = []
        for gid in self.map_symbols(symbols).values():
            if gid is not None and gid not in seen:
                seen.add(gid)
                out.append(gid)
        return out

    def mapped_count(self, symbols: List[str]) -> int:
        """매핑된 유니크 정규화 심볼 수 (매핑 0건 판단용, G14)."""
        return sum(1 for gid in self.map_symbols(symbols).values() if gid is not None)

    def reverse_map(self) -> Dict[int, str]:
        """Entrez → primary normalized symbol 역매핑 (plan §6.4 _gene_set 복원).

        GOATOOLS study_items(Entrez)를 심볼로 되돌릴 때 사용한다.
        gene_info의 primary Symbol 기준이며, 세션 내 1회 lazy 빌드 후 메모리 캐시.
        """
        if self._reverse is not None:
            return self._reverse
        gene_info = self._cache.ensure_gene_info(self.organism)
        df = self._read_gene_info(gene_info, include_synonyms=False)
        rows = df[
            (df["tax_id"] == str(self.taxid))
            & df["GeneID"].notna()
            & df["Symbol"].notna()
        ]
        rev: Dict[int, str] = {}
        for gene_id, symbol in zip(rows["GeneID"].astype(str), rows["Symbol"].astype(str)):
            symbol = symbol.strip()
            if symbol in ("", "nan"):
                continue
            try:
                gid = int(gene_id)
            except (TypeError, ValueError):
                continue
            rev.setdefault(gid, self.normalize_symbol(symbol))
        self._reverse = rev
        return rev

    def reverse_name(self, entrez: int) -> Optional[str]:
        """Entrez → primary normalized symbol (없으면 None)."""
        return self.reverse_map().get(entrez)

    # ------------------------------------------------------------- internals

    @staticmethod
    def _sidecar_path(pickle_path: Path) -> Path:
        return pickle_path.with_name(pickle_path.name + ".sha256")

    def _load_map(self) -> Dict[str, int]:
        """로컬 맵 로드: 메모리 → pickle(sha 검증) → gene_info 재빌드 순."""
        gene_info = self._cache.ensure_gene_info(self.organism)
        src_sha = self._gene_info_sha(gene_info)

        if self._map is not None and self._loaded_sha == src_sha:
            return self._map  # 메모리 캐시가 현재 gene_info와 일치

        pickle_path = self.cache_file()
        if src_sha is not None and self._pickle_valid(pickle_path, src_sha):
            with open(pickle_path, "rb") as fh:
                self._map = pickle.load(fh)
            self._loaded_sha = src_sha
            self._logger.debug("SymbolMapper: pickle cache hit %s", pickle_path)
            return self._map

        mapping = self._build_map_from_gene_info(gene_info)
        self._write_pickle_atomic(mapping, pickle_path, src_sha)
        self._map = mapping
        self._loaded_sha = src_sha
        return mapping

    def _gene_info_sha(self, gene_info: Path) -> Optional[str]:
        """CacheManager.sidecar(path)['sha256'] — 없으면 None(검증 불가 → 재빌드)."""
        try:
            sidecar = self._cache.sidecar(gene_info)
        except Exception:
            return None
        if isinstance(sidecar, dict):
            return sidecar.get("sha256") or None
        return None

    def _pickle_valid(self, pickle_path: Path, src_sha: str) -> bool:
        sidecar_path = self._sidecar_path(pickle_path)
        if not pickle_path.exists() or not sidecar_path.exists():
            return False
        try:
            return sidecar_path.read_text().strip() == src_sha
        except OSError:
            return False

    @staticmethod
    def _read_gene_info(gene_info: Path, include_synonyms: bool) -> pd.DataFrame:
        """gene_info(종별 필터 파일)를 NCBI 레이아웃(인덱스 고정)으로 읽는다.

        NCBI gene_info는 `#Format:`/`#tax_id` 주석 행이 있으므로 comment='#' + header=None로
        읽고 컬럼을 위치로 선택한다(tax_id=0, GeneID=1, Symbol=2, Synonyms=4).
        컬럼 수(Feature_type 추가 등) 변화와 테스트 픽스처(4컬럼) 모두에 강건.
        """
        df = pd.read_csv(gene_info, sep="\t", compression="infer",
                         comment="#", header=None, dtype=str)
        if df.shape[1] < 3:
            raise ValueError(f"gene_info shape {df.shape}: 최소 3컬럼 필요 (tax_id, GeneID, Symbol)")
        cols = {"tax_id": 0, "GeneID": 1, "Symbol": 2}
        if include_synonyms:
            cols["Synonyms"] = 4 if df.shape[1] > 4 else 3
        out = pd.DataFrame({name: df.iloc[:, idx].astype(str) for name, idx in cols.items()})
        return out

    def _build_map_from_gene_info(self, gene_info: Path) -> Dict[str, int]:
        """gene_info TSV(taxid 필터)에서 정규화 심볼 → Entrez 매핑 구축.

        Symbol 컬럼과 Synonyms 컬럼(파이프 구분)을 모두 매핑하며, 같은
        정규화 심볼은 첫 번째 행(GeneID 오름차순 파일 순서)을 우선한다.
        """
        df = self._read_gene_info(gene_info, include_synonyms=True)
        rows = df[
            (df["tax_id"] == str(self.taxid))
            & df["GeneID"].notna()
            & df["Symbol"].notna()
        ]
        mapping: Dict[str, int] = {}
        for gene_id, symbol, synonyms in zip(
            rows["GeneID"].astype(str),
            rows["Symbol"].astype(str),
            rows["Synonyms"].fillna("").astype(str),
        ):
            symbol = symbol.strip()
            if symbol in ("", "nan"):          # astype(str) NaN 보호 (architect P3)
                continue
            try:
                gid = int(gene_id)
            except (TypeError, ValueError):
                continue
            mapping.setdefault(self.normalize_symbol(symbol), gid)
            # NCBI gene_info는 별칭 없음 표시로 '-'를 쓴다.
            if synonyms and synonyms.strip() not in ("-", "nan"):
                for alias in synonyms.split("|"):
                    alias = self.normalize_symbol(alias)
                    if alias and alias not in ("NAN", "Nan", "nan"):
                        mapping.setdefault(alias, gid)
        return mapping

    def _write_pickle_atomic(self, mapping: Dict[str, int], pickle_path: Path,
                             src_sha: Optional[str]) -> None:
        """원자적 pickle 쓰기(.tmp → os.replace). 사이드카를 먼저 기록한다.

        어느 시점에 크래시해도 pickle/사이드카 sha 불일치가 되어 다음 호출이
        안전하게 재빌드한다(부분 쓰기 상태로 재사용되지 않음).
        """
        pickle_path.parent.mkdir(parents=True, exist_ok=True)
        sidecar_path = self._sidecar_path(pickle_path)
        tmp_sidecar = sidecar_path.with_name(sidecar_path.name + ".tmp")
        tmp_pickle = pickle_path.with_name(pickle_path.name + ".tmp")
        tmp_sidecar.write_text(src_sha or "")
        os.replace(tmp_sidecar, sidecar_path)
        with open(tmp_pickle, "wb") as fh:
            pickle.dump(mapping, fh, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp_pickle, pickle_path)

    def _query_mygene(self, symbols: List[str]) -> Dict[str, int]:
        """mygene 온라인 fallback(plan §6.7): querymany(scopes='symbol', ...).

        실패(예외)는 경고 후 빈 결과로 처리 — 크래시·가짜 성공 금지(G13).
        응답은 list(일반) 또는 단일 dict를 모두 처리한다.
        """
        if not symbols:
            return {}
        try:
            if self._mygene is None:
                from mygene import MyGeneInfo
                self._mygene = MyGeneInfo()
            reply = self._mygene.querymany(
                symbols,
                scopes="symbol",
                fields="entrezgene",
                species=self.taxid,
            )
        except Exception as exc:
            self._logger.warning(
                "SymbolMapper: mygene query failed (%s); %d symbol(s) remain unmapped",
                exc, len(symbols),
            )
            return {}
        hits = reply if isinstance(reply, list) else [reply]
        out: Dict[str, int] = {}
        for row in hits:
            if not isinstance(row, dict):
                continue
            query = row.get("query")
            if query is None or row.get("notfound"):
                continue
            gid = self._coerce_entrez(row.get("entrezgene"))
            if gid is not None:
                out[query] = gid
        return out

    @staticmethod
    def _coerce_entrez(value) -> Optional[int]:
        """mygene 응답의 entrezgene 값을 int로 정규화(mygene은 str/list 반환 가능)."""
        if isinstance(value, (list, tuple)):
            value = value[0] if value else None
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
