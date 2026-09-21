"""
EnrichmentAnalyzer — GO/KEGG enrichment 엔진 API (plan §6.2~6.9, G3/G8/G12/G16).

- `enrich_ora`        : ORA 실행 (online=Enrichr / local=GOATOOLS / KEGG GMT) → 라벨별 raw 결과
- `enrich_prerank`    : Phase 4 인터페이스 (구현은 §10-4 — G16)
- `to_standard`       : raw 결과 → §6.3~6.6 표준 병합 DataFrame (단일 진실원천
                        `go_kegg_loader.standardize_go_dataframe` 재사용)
- `libraries_for`     : 종별 온라인/로컬 라이브러리 테이블 (A3/A4)

라우팅/정책 (PoC 확정 2026-09-02):
- ADR-2 2A: background 지정 시 온라인(Enrichr/Speedrichr) 호출 금지 → 로컬 강제 (G8).
- ADR-1 Option 1: 로컬 GO=GOATOOLS; KEGG 오프라인(v1) 비활성 → ErrorKind.OFFLINE_KEGG (F3).
- A3: mouse GO는 온라인 라이브러리 부재(P0-7) → 로컬 전용; mouse KEGG(2021/2019)는 온라인 허용.
- A4: Auto = background 미지정 && detect_online() → Enrichr / 그 외 → 로컬.
- G14: 매핑 0건·입력 0개·전체 실패 → EnrichmentError(kind, msg) — 조용한 fallback 금지.
"""

import io
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd

from models.enrichment_models import EnrichmentRequest, ErrorKind, VALID_ONTOLOGIES
from models.standard_columns import StandardColumns
from utils.enrichment_cache import CacheManager, GENE2GO_KEY, GENE_INFO_KEY
from utils.gene_id_mapper import SymbolMapper
from utils.go_kegg_loader import compute_fold_enrichment, parse_gene_symbols, reorder_standard_go_frame

# --------------------------------------------------------------------------
# 종별 라이브러리 테이블 (P0-2/P0-7 실측값 기준)
# --------------------------------------------------------------------------
TAXID = {"human": 9606, "mouse": 10090}

# 온라인(Enrichr) 라이브러리명 — GO 2023(Human), KEGG 2021(Human)/2019(Mouse)
ONLINE_LIBRARY_NAMES = {
    "human": {
        "BP": "GO_Biological_Process_2023",
        "CC": "GO_Cellular_Component_2023",
        "MF": "GO_Molecular_Function_2023",
        "KEGG": "KEGG_2021_Human",
    },
    # P0-7: mouse GO 라이브러리 부재(0건) → GO는 로컬 전용(A3). KEGG 2019 Mouse는 온라인 존재.
    "mouse": {
        "KEGG": "KEGG_2019_Mouse",
    },
}

# GMT 텍스트 더미 URL (bg_ratio 분자 M 산출용 — §6.5/G6)
ENRICHR_LIBRARY_URL = (
    "https://maayanlab.cloud/Enrichr/geneSetLibrary?mode=text&libraryName={name}"
)

# prerank GMT 캐시 키 (온라인 라이브러리명과 동일 스냅샷 — GO 2023/KEGG 2021 또는 종별)
_GO_LIBNAME = {"BP": "GO_Biological_Process_2023",
               "CC": "GO_Cellular_Component_2023",
               "MF": "GO_Molecular_Function_2023"}
_GMT_RESOLVE = {
    "human": {"BP": "GO_Biological_Process_2023", "CC": "GO_Cellular_Component_2023",
               "MF": "GO_Molecular_Function_2023", "KEGG": "KEGG_2021_Human"},
    "mouse": {"KEGG": "KEGG_2019_Mouse"},
}

_GO_ID_RE = re.compile(r"\bGO:\d{7}\b")
_GENE_SPLIT_RE = re.compile(r"[;/,]")
_KEGG_NAME_SUFFIX_RE = re.compile(r"\s*-\s*(homo sapiens|mus musculus)\b.*$")


class EnrichmentError(Exception):
    """엔진 실패 (G14 — 명시적 UX용 ErrorKind 포함)."""

    def __init__(self, kind: ErrorKind, message: str, warnings: Optional[List[str]] = None):
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.warnings = warnings or []


@dataclass
class RawResult:
    """enrich_ora의 단위 결과 — (gene_set 라벨 × 엔진)별 raw 데이터."""

    label: str                       # e.g. "UP_BP", "TOTAL_KEGG" (§6.3)
    engine: str                      # "enrichr" | "goatools" | "gmt"
    data: Union[pd.DataFrame, list]  # enrichr→DataFrame / goatools→GOEnrichmentRecord list
    meta: Dict = None


@dataclass
class _GmtInfo:
    """캐시 GMT 스냅샷 (bg_ratio 분자 M 산출용 — §6.5/G6).

    - by_id  : GO id → gene count (GO 라이브러리: col1에 `(GO:xxxxxxx)` 포함)
    - by_name: col1 전체 문자열 → gene count (KEGG 및 GO 이름 폴백)
    - names  : GO id → GMT 이름(col1, 괄호 제거) — A4 canonical fallback
    - universe: 라이브러리 고유 유전자 수 (분모 N — §6.5)
    """

    by_id: Dict[str, int]
    by_name: Dict[str, int]
    names: Dict[str, str]
    universe: int


class EnrichmentAnalyzer:
    """GO/KEGG enrichment 엔진 (plan §6.2)."""

    def __init__(self, cache: Optional[CacheManager] = None, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.cache = cache or CacheManager(_default_cache_dir())
        # 세션 캐시: obo 이름 맵/GODag, GMT 파싱 (plan §6.8 프로세스 내 1회 로드)
        self._obo_names: Optional[Dict[str, str]] = None          # {GO id: name}
        self._obo_mtime: Optional[float] = None
        self._godag = None
        self._godag_mtime: Optional[float] = None
        self._gmt_cache: Dict[str, _GmtInfo] = {}   # lib -> GMT 스냅샷 (성공만 캐시)
        self._assoc_cache: Dict[str, Dict[str, int]] = {}  # 'assoc:<org>' -> {GO id: size}
        self._kegg_pathway_cache: Dict[str, Dict[str, str]] = {}  # organism -> {normalized name: pathway id}
        self._mapper: Optional[SymbolMapper] = None
        self._current_organism: Optional[str] = None

    # ------------------------------------------------------------- engine API

    @staticmethod
    def libraries_for(organism: str) -> Dict[str, Dict[str, str]]:
        """종별 라이브러리 테이블: {'online': {...}, 'local': {...}} (A3/A4)."""
        if organism not in TAXID:
            raise ValueError(f"unsupported organism: {organism!r}")
        online = dict(ONLINE_LIBRARY_NAMES.get(organism, {}))
        local = {"BP": "GOATOOLS", "CC": "GOATOOLS", "MF": "GOATOOLS"}
        return {"online": online, "local": local}

    def enrich_ora(
        self,
        genes: List[str],
        background: Optional[List[str]] = None,
        organism: str = "human",
        libraries: Optional[List[str]] = None,
        engine: str = "auto",
        direction: str = "TOTAL",
        population_symbols: Optional[List[str]] = None,
        one_sided: bool = False,
    ) -> Tuple[List[RawResult], List[str]]:
        """ORA 실행 → (raw 결과 목록, 경고 목록).

        - 라이브러리 목록: ["BP","CC","MF","KEGG"] (F10: 동일 ontology 1개 전제).
        - engine: auto|online|local|offline (A4). background 지정 시 온라인 금지(2A).
        - population_symbols: 로컬(GOATOOLS) population 후보 (DE 테이블 전체 유전자).
          **2A를 트리거하지 않음** — custom background와 분리 (architect P2-1).
        """
        if organism not in TAXID:
            raise ValueError(f"unsupported organism: {organism!r}")
        if libraries is None:
            libraries = ["BP", "CC", "MF", "KEGG"]
        bad = [lib for lib in libraries if lib not in VALID_ONTOLOGIES]
        if bad:
            raise ValueError(f"invalid libraries: {bad}")
        if direction not in ("UP", "DOWN", "TOTAL"):
            raise ValueError(f"invalid direction: {direction!r}")

        warnings: List[str] = []
        mapper = self._mapper_for(organism)
        # A6: 공개 API 경계에서 종별 casing 재적용 (호출자가 deg_input 우회 시 안전)
        gene_list = [mapper.normalize_symbol(g) for g in (genes or []) if g and g.strip()]
        if not gene_list:
            raise EnrichmentError(ErrorKind.NO_INPUT_GENES,
                                  "No input DEG genes (thresholds produced 0 results).")

        # ---- 엔진 결정 (A4 라우팅 + ADR-2 2A 가드) ----
        online_available = engine == "online" or (
            engine == "auto" and self.cache.detect_online()
        )
        engine_effective = engine
        if background is not None and engine in ("auto", "online"):
            # 2A: 커스텀 background는 온라인(Enrichr/Speedrichr) 불가 → 로컬 강제 (G8)
            warnings.append(
                "W2 custom background set — online path unused, local engine forced (ADR-2 2A)."
            )
            engine_effective = "local"
        if engine_effective == "offline":
            online_available = False
            engine_effective = "local"

        # ---- 심볼 매핑 (G9) — 매핑 캐시 접근 실패는 DOWNLOAD로 분류 (P2-3 첫 실행 UX)
        self._one_sided = one_sided   # 로컬 GOATOOLS p 재계산용 (단측 Fisher)
        try:
            mapped = mapper.map_symbols(gene_list)
        except Exception as exc:
            raise EnrichmentError(ErrorKind.DOWNLOAD,
                                  f"Symbol mapping cache (gene_info) access failed: {exc}",
                                  warnings=warnings) from exc
        if not any(gid is not None for gid in mapped.values()):
            raise EnrichmentError(
                ErrorKind.MAPPING,
                "Gene mapping returned 0 hits — analysis cannot proceed (see the gene_info local cache download guide, G9/G14).",
            )

        # 배경 population (GOATOOLS): custom background > population_symbols(DE 전체) > self
        population_entrez: Optional[List[int]] = None
        def _map_population(symbols: List[str], kind: str) -> Optional[List[int]]:
            try:
                mapped_bg = mapper.map_symbols(symbols)
            except Exception as exc:
                raise EnrichmentError(ErrorKind.DOWNLOAD,
                                      f"{kind} mapping cache (gene_info) access failed: {exc}",
                                      warnings=warnings) from exc
            entrez = [g for g in mapped_bg.values() if g is not None]
            if not entrez:
                warnings.append(f"W1 {kind} mapping 0 hits — using DEG self-background.")
            return entrez or None

        if background:
            population_entrez = _map_population(background, "custom background")
        elif population_symbols:
            population_entrez = _map_population(population_symbols, "population_symbols")
        study_entrez = [g for g in mapped.values() if g is not None]

        results: List[RawResult] = []
        for lib in libraries:
            # 라벨 관례: GO={direction}_{ontology}, KEGG=KEGG_{direction}
            # (파이프라인 final_go_result.xlsx 시트명과 정합 — KEGG_DOWN/KEGG_TOTAL)
            label = f"KEGG_{direction}" if lib == "KEGG" else f"{direction}_{lib}"
            if lib == "KEGG":
                if engine_effective == "local":
                    # ADR-1 Option 1: KEGG 오프라인 v1 비활성 (F3)
                    warnings.append(
                        "W1 KEGG offline is not supported (v1, ADR-1 Option 1) — KEGG is analyzed online only."
                    )
                    continue
                name = ONLINE_LIBRARY_NAMES[organism].get("KEGG")
                if name is None:
                    warnings.append(f"W1 no online KEGG library for {organism}.")
                    continue
                try:
                    results.append(
                        RawResult(label, "enrichr", self._enrichr_call(name, gene_list, organism),
                                  meta={"engine_effective": "online"})
                    )
                except EnrichmentError:
                    raise
                except Exception as exc:  # 네트워크 실패 (G13 — 조용한 성공 금지)
                    raise EnrichmentError(ErrorKind.NETWORK, f"Enrichr KEGG failed: {exc}",
                                          warnings=warnings) from exc
                continue

            # ---- GO: BP/CC/MF ----
            if online_available and engine_effective in ("auto", "online"):
                if organism == "mouse":
                    # A3: mouse GO 온라인 라이브러리 없음 → 로컬 전용
                    warnings.append("W1 mouse GO: no online library — using local (GOATOOLS) (A3).")
                    try:
                        results.append(
                            RawResult(label, "goatools",
                                      self._goatools_call(study_entrez, population_entrez, organism,
                                  one_sided=one_sided),
                                      meta={"population": population_entrez or list(study_entrez),
                                            "engine_effective": engine_effective})
                        )
                    except EnrichmentError:
                        raise
                    except Exception as exc:
                        # 캐시 부재/다운로드 실패 등 로컬 경로 실패 (P2-3 첫 실행 UX 분류용)
                        raise EnrichmentError(ErrorKind.DOWNLOAD,
                                              f"Local GOATOOLS run failed (cache download/parse): {exc}",
                                              warnings=warnings) from exc
                    continue
                name = ONLINE_LIBRARY_NAMES[organism].get(lib)
                if name is None:
                    raise EnrichmentError(ErrorKind.UNKNOWN,
                                          f"no online {lib} library for {organism}")
                try:
                    results.append(RawResult(label, "enrichr", self._enrichr_call(name, gene_list, organism),
                                             meta={"engine_effective": "online"}))
                except EnrichmentError:
                    raise
                except Exception as exc:
                    raise EnrichmentError(ErrorKind.NETWORK,
                                          f"Enrichr {lib} failed: {exc}", warnings=warnings) from exc
            else:
                try:
                    results.append(
                        RawResult(label, "goatools",
                                  self._goatools_call(study_entrez, population_entrez, organism,
                                  one_sided=one_sided),
                                  meta={"population": population_entrez or list(study_entrez),
                                        "engine_effective": engine_effective})
                    )
                except EnrichmentError:
                    raise
                except Exception as exc:
                    raise EnrichmentError(ErrorKind.DOWNLOAD,
                                          f"Local GOATOOLS run failed (cache download/parse): {exc}",
                                          warnings=warnings) from exc

        if not results:
            raise EnrichmentError(
                ErrorKind.EMPTY_RESULT,
                "No libraries were executed (offline KEGG inactive, etc. — see warnings).",
                warnings=warnings,
            )
        return results, warnings

    def enrich_prerank(self, ranked, organism: str = "human",
                        libraries: Optional[List[str]] = None,
                        permutation_num: int = 100,
                        min_size: int = 15, max_size: int = 1000,
                        direction: str = "TOTAL") -> Tuple[List[RawResult], List[str]]:
        """GSEA prerank (gseapy.prerank — Phase 4 §10-4, M4b/G16).

        ranked: [(symbol, score)] — meta 랭킹(meta_z 또는 -log10(p)xsign, META_ANALYSIS_PLAN M4b).
        gene_sets: 캐시 GMT (GO/KEGG 모두 로컬 스냅샷 — 기본 ORA의 KEGG-오프라인 제약(F3)과
        별개로 prerank는 캐시 GMT 기반 오프라인 지원).
        """
        if organism not in TAXID:
            raise ValueError(f"unsupported organism: {organism!r}")
        if libraries is None:
            libraries = ["BP", "CC", "MF", "KEGG"]
        bad = [lib for lib in libraries if lib not in VALID_ONTOLOGIES]
        if bad:
            raise ValueError(f"invalid libraries: {bad}")
        if not ranked:
            raise EnrichmentError(ErrorKind.NO_INPUT_GENES,
                                  "Ranked list is empty (meta ranking extraction returned 0).")

        warnings: List[str] = []
        results: List[RawResult] = []
        for lib in libraries:
            label = f"KEGG_{direction}" if lib == "KEGG" else f"{direction}_{lib}"
            lib_map = _GMT_RESOLVE.get(organism, {})
            if lib not in lib_map:
                # A3: mouse GO prerank GMT 없음 → 스킵 + 경고 (ORA와 동일 정책)
                warnings.append(f"W1 no prerank GMT snapshot for {organism} {lib} — skipped (A3).")
                continue
            gmt_key = lib_map[lib]
            try:
                gmt_path = self.cache.ensure_gmt(gmt_key)
            except Exception as exc:
                raise EnrichmentError(ErrorKind.DOWNLOAD,
                                      f"prerank GMT cache failed ({lib}): {exc}",
                                      warnings=warnings) from exc
            import gseapy
            rnk_df = pd.DataFrame(ranked, columns=["gene", "score"])
            try:
                out = gseapy.prerank(
                    rnk=rnk_df, gene_sets=[str(gmt_path)],
                    outdir=None, permutation_num=permutation_num,
                    min_size=min_size, max_size=max_size,
                    no_plot=True, seed=42, threads=1)
            except Exception as exc:
                raise EnrichmentError(ErrorKind.UNKNOWN,
                                      f"gseapy.prerank failed ({lib}): {exc}",
                                      warnings=warnings) from exc
            df = out.res2d if hasattr(out, "res2d") else out
            results.append(RawResult(label, "prerank", df,
                                     meta={"engine_effective": "local",
                                           "gmt_path": str(gmt_path),
                                           "population": [sym for sym, _ in ranked]}))
        if not results:
            raise EnrichmentError(ErrorKind.EMPTY_RESULT,
                                  "실행된 prerank 라이브러리가 없습니다.", warnings=warnings)
        return results, warnings

    # ------------------------------------------------------------- converter

    def to_standard(
        self,
        raw_results: List[RawResult],
        organism: str = "human",
        genes: Optional[List[str]] = None,
        background: Optional[List[str]] = None,
    ) -> Tuple[pd.DataFrame, List[str]]:
        """§6.3~6.6 표준 병합 DataFrame 변환 → (df, 경고). (G4/G5/G6/G7/A4/A5)

        라벨 → direction/ontology 파싱은 기존 `standardize_go_dataframe`를
        다시 사용하므로 다운스트림 GO 필터/시각화와 완전 호환된다.
        """
        warnings: List[str] = []
        rows: List[pd.DataFrame] = []
        n_bg_db = len(background) if background else None

        for raw in raw_results:
            direction, ontology = _parse_label(raw.label)
            if raw.engine == "enrichr":
                rows.append(self._convert_enrichr(raw, direction, ontology, organism, warnings, n_bg_db))
            elif raw.engine == "goatools":
                rows.append(self._convert_goatools(raw, direction, ontology, organism, warnings, n_bg_db))
            elif raw.engine == "prerank":
                rows.append(self._convert_prerank(raw, direction, ontology, organism, warnings, n_bg_db))
            else:
                warnings.append(f"W1 unsupported raw engine: {raw.engine!r} — rows skipped.")

        if not rows:
            raise EnrichmentError(ErrorKind.EMPTY_RESULT, "No rows to convert.")

        merged = pd.concat(rows, ignore_index=True)

        # fold_enrichment (G6 — 기존 로더 수식 재사용)
        merged = compute_fold_enrichment(merged, self.logger)

        # _gene_set (A5 — [;/,] 다구분자 정규화, 기존 클러스터링과 호환)
        merged = parse_gene_symbols(merged, self.logger)
        # 헤더 순서 정합 (파이프라인 반입 결과와 동일 표준 순서 — 사용자 요구)
        merged = reorder_standard_go_frame(merged)

        # 빈 _gene_set 감지 지표 (W1 — 클러스터링 무력화 조기 탐지, §6.4)
        if "_gene_set" in merged.columns and len(merged) > 0:
            n_empty = int((merged["_gene_set"].map(len) == 0).sum())
            if n_empty == len(merged):
                warnings.append("W1 all rows have empty _gene_set — clustering/network may be disabled.")
        return merged, warnings

    # ------------------------------------------------------------- internals

    def _mapper_for(self, organism: str) -> SymbolMapper:
        if self._mapper is None or self._current_organism != organism:
            self._mapper = SymbolMapper(self.cache, organism=organism, logger=self.logger)
            self._current_organism = organism
        return self._mapper

    def _enrichr_call(self, library_name: str, gene_list: List[str],
                      organism: str) -> pd.DataFrame:
        """Enrichr 실호출 (심볼만 전송 — background 금지, 2A 가드)."""
        import gseapy
        self.logger.info("Enrichr online: %s (%d genes)", library_name, len(gene_list))
        out = gseapy.enrichr(
            gene_list=gene_list,
            gene_sets=[library_name],
            organism=organism,
            outdir=None,
            no_plot=True,
        )
        # gseapy 1.3.x: enrichr()는 Enrichr 객체(.results) 반환 (PoC 실측)
        if hasattr(out, "results"):
            out = out.results
        if isinstance(out, dict):
            out = out.get(library_name, pd.DataFrame())
        return out

    def _goatools_call(self, study_entrez: List[int], population_entrez: Optional[List[int]],
                       organism: str, one_sided: bool = False):
        """GOATOOLS 로컬 GO (plan §6.2 — taxid별 gene2go, fisher+fdr_bh, propagate)."""
        from goatools.anno.genetogo_reader import Gene2GoReader
        from goatools.goea.go_enrichment_ns import GOEnrichmentStudyNS

        taxid = TAXID[organism]
        obo_path = self.cache.ensure_obo(organism)
        g2g_path = self._plain_gene2go(organism)   # 실측: Gene2GoReader는 .gz 비지원 (PoC도 tsv 사용)
        dag = self._get_godag(obo_path)

        reader = Gene2GoReader(filename=str(g2g_path), taxids=[taxid], prt=io.StringIO())
        ns2assoc = reader.get_ns2assc()

        population = population_entrez or list(study_entrez)  # v1 self-background (Phase 2가 DE 전체 전달)
        goea = GOEnrichmentStudyNS(
            population, ns2assoc, dag,
            propagate_counts=True, alpha=0.05, methods=["fdr_bh"],
            logger=self.logger,
        )
        self.logger.info("GOATOOLS local: %d study / %d population (taxid %d)",
                         len(study_entrez), len(population), taxid)
        results = goea.run_study(study_entrez)
        if one_sided:
            # 파이프라인(clusterProfiler)과 동일 단측(enrichment) Fisher + BH —
            # GOATOOLS 기본은 양측(보수적; 동일-주석 재검증에서 ~0.82배 p)이므로 재계산.
            results = _apply_one_sided_fisher(results)
        return results

    def _plain_gene2go(self, organism: str) -> Path:
        """gene2go_<taxid>.gz → plain tsv (Gene2GoReader은 gzip 미지원).

        캐시는 gzip으로 저장하고(디스크 효율), 소비자(goatools)가 필요할 때
        mtime 기반 1회 압축 해제해 세션 캐시한다.
        """
        import gzip
        import os
        import shutil
        gz = self.cache.ensure_gene2go(organism)
        plain = gz.with_suffix(".tsv")
        need_rebuild = (not plain.exists()) or (gz.stat().st_mtime > plain.stat().st_mtime)
        if need_rebuild:
            # 원자적 쓰기 (.tmp → os.replace) — 크래시 시 부분 tsv 재사용 방지 (architect P3)
            tmp = plain.with_name(plain.name + ".tmp")
            with gzip.open(gz, "rb") as fin, open(tmp, "wb") as fout:
                shutil.copyfileobj(fin, fout)
            os.replace(tmp, plain)
        return plain

    def _get_godag(self, obo_path: Path):
        from goatools.obo_parser import GODag
        mtime = obo_path.stat().st_mtime
        if self._godag is None or self._godag_mtime != mtime:
            self._godag = GODag(str(obo_path), prt=io.StringIO())
            self._godag_mtime = mtime
        return self._godag

    # -- 컨버터 헬퍼 -----------------------------------------------------

    def _convert_enrichr(self, raw: RawResult, direction: str, ontology: str,
                         organism: str, warnings: List[str],
                         n_bg_db: Optional[int]) -> pd.DataFrame:
        df = raw.data
        lib_name = ONLINE_LIBRARY_NAMES.get(organism, {}).get(ontology) or df["Gene_set"].iloc[0]
        gmt = self._gmt_for(lib_name, warnings)   # _GmtInfo | None on failure
        kegg_map = self._kegg_pathway_map(organism, warnings) if ontology == "KEGG" else None

        out_rows = []
        for _, r in df.iterrows():
            term_raw = str(r["Term"])
            if ontology != "KEGG":
                m = _GO_ID_RE.search(term_raw)
                term_id = m.group(0) if m else ""
            else:
                # Enrichr KEGG Term text has no embedded ID (e.g. "Phagosome") —
                # look up the pathway ID by name in the cached KEGG pathway list.
                term_id = (kegg_map or {}).get(_normalize_kegg_name(term_raw), "")
                if not term_id:
                    warnings.append(f"W1 KEGG pathway ID not found for term: {term_raw!r}")
            overlap = str(r["Overlap"])                    # 'k/n'
            k, n = _parse_overlap(overlap)
            m_size = None
            n_bg = None
            if gmt is not None:
                if ontology != "KEGG" and term_id:
                    m_size = gmt.by_id.get(term_id)
                if m_size is None:
                    m_size = gmt.by_name.get(term_raw)
                if m_size is not None:
                    n_bg = gmt.universe
                else:
                    warnings.append(
                        f"W1 term missing from GMT snapshot — bg_ratio M approximated by hit count: "
                        f"{term_raw} ({lib_name})")
                    m_size = k
            else:
                warnings.append(f"W1 GMT unavailable — bg_ratio M approximated by hit count ({lib_name}).")
                m_size = k
            if n_bg is None:
                n_bg = n_bg_db if n_bg_db is not None else n
            description = self._canonical_description(
                term_id, term_raw, gmt, warnings) if term_id else _strip_go_suffix(term_raw)
            out_rows.append({
                StandardColumns.TERM_ID: term_id,
                StandardColumns.DESCRIPTION: description,
                StandardColumns.GENE_COUNT: k,
                StandardColumns.GENE_SYMBOLS: _genes_to_slash(r["Genes"]),
                StandardColumns.PVALUE_GO: _num(r["P-value"]),
                StandardColumns.FDR: _num(r["Adjusted P-value"]),
                StandardColumns.GENE_RATIO: f"{k}/{n}",
                StandardColumns.BG_RATIO: f"{m_size}/{n_bg}",
                "bg_count": m_size,
                "odds_ratio": _num(r.get("Odds Ratio")),
                "combined_score": _num(r.get("Combined Score")),
                StandardColumns.GENE_SET: direction,
                StandardColumns.DIRECTION: direction,
                StandardColumns.ONTOLOGY: ontology,
                "_engine": "enrichr",
            })
        return pd.DataFrame(out_rows)

    def _convert_goatools(self, raw: RawResult, direction: str, ontology: str,
                          organism: str, warnings: List[str],
                          n_bg_db: Optional[int]) -> pd.DataFrame:
        mapper = self._mapper_for(organism)
        assoc_sizes = self._assoc_term_sizes(organism, warnings)
        raw_meta = raw.meta or {}
        population_n = n_bg_db if n_bg_db is not None else len(raw_meta.get("population", [])) \
            if raw_meta else None
        out_rows = []
        for rec in raw.data:
            term_id = getattr(rec, "GO", "")
            study_count = int(getattr(rec, "study_count", 0) or 0)
            study_n = int(getattr(rec, "study_n", 0) or 0) or None
            p_fdr = getattr(rec, "p_fdr_bh", None)
            p_raw = getattr(rec, "p_uncorrected", getattr(rec, "pvalue", None))
            m_size = assoc_sizes.get(term_id, study_count)
            genes = "/".join(
                mapper.reverse_name(gid) for gid in getattr(rec, "study_items", [])
                if mapper.reverse_name(gid)
            )
            out_rows.append({
                StandardColumns.TERM_ID: term_id,
                StandardColumns.DESCRIPTION: getattr(rec, "name", ""),
                StandardColumns.GENE_COUNT: study_count,
                StandardColumns.GENE_SYMBOLS: genes,
                StandardColumns.PVALUE_GO: _num(p_raw),
                StandardColumns.FDR: _num(p_fdr),
                StandardColumns.GENE_RATIO: f"{study_count}/{study_n or study_count}",
                StandardColumns.BG_RATIO: f"{m_size}/{population_n or study_n or study_count}",
                "bg_count": m_size,
                "odds_ratio": None,
                "combined_score": None,
                StandardColumns.GENE_SET: direction,
                StandardColumns.DIRECTION: direction,
                StandardColumns.ONTOLOGY: ontology,
                "_engine": "goatools",
            })
        return pd.DataFrame(out_rows)

    def _convert_prerank(self, raw: RawResult, direction: str, ontology: str,
                           organism: str, warnings: List[str],
                           n_bg_db: Optional[int]) -> pd.DataFrame:
        """GSEA prerank raw → 표준 행 (NES/FWER 보존 — plan P4-1/M4b).

        ratio 규칙: gene_ratio = leading-edge 길이 k / ranked 유전자 수 n;
        bg_ratio = 캐시 GMT term 크기 M / GMT universe N (§6.5와 동일 프레임).
        """
        df = raw.data
        gmt_key = _GMT_RESOLVE.get(organism, {}).get(ontology)
        if not gmt_key and "Gene_set" in df.columns:
            gmt_key = str(df["Gene_set"].iloc[0])
        gmt = self._gmt_for(gmt_key or ontology, warnings)
        kegg_map = self._kegg_pathway_map(organism, warnings) if ontology == "KEGG" else None
        n_all = len(raw.meta.get("population", [])) if raw.meta else len(df)

        term_col = _col(df, ["Term", "term"])
        nes_col = _col(df, ["NES", "nes"])
        fdr_col = _col(df, ["FDR q-val", "FDR q-value", "fdr", "FDR"])
        pval_col = _col(df, ["NOM p-val", "pval", "p-value", "pvalue"])
        fwer_col = _col(df, ["FWER p-val", "FWER p-value"])
        genes_col = _col(df, ["Lead_genes", "Lead genes", "Leading Edge", "leading edge",
                              "Genes", "gene_symbols"])

        out_rows = []
        if term_col is None:
            warnings.append("W1 prerank result has no Term column — rows skipped.")
            return pd.DataFrame()
        for _, r in df.iterrows():
            term_raw = _strip_gmt_prefix(str(r[term_col]))
            if ontology != "KEGG":
                m = _GO_ID_RE.search(term_raw)
                term_id = m.group(0) if m else ""
            else:
                term_id = (kegg_map or {}).get(_normalize_kegg_name(term_raw), "")
                if not term_id:
                    warnings.append(f"W1 KEGG pathway ID not found for term: {term_raw!r}")
            k = 0
            if genes_col is not None and pd.notna(r[genes_col]):
                k = len([g for g in _GENE_SPLIT_RE.split(str(r[genes_col])) if g.strip()])
            m_size = None                       # by_id → by_name → k 폴백 (QA 발견: 데드 브랜치)
            n_bg = len(raw.meta.get("population", [])) if raw.meta else 0
            if gmt is not None:
                if ontology != "KEGG" and term_id:
                    m_size = gmt.by_id.get(term_id)
                if m_size is None:
                    m_size = gmt.by_name.get(term_raw)
                if m_size is not None:
                    n_bg = gmt.universe
            if m_size is None:
                m_size = k
            description = self._canonical_description(
                term_id, term_raw, gmt, warnings) if term_id else _strip_go_suffix(term_raw)
            out_rows.append({
                StandardColumns.TERM_ID: term_id,
                StandardColumns.DESCRIPTION: description,
                StandardColumns.GENE_COUNT: k,
                StandardColumns.GENE_SYMBOLS: (_genes_to_slash(r[genes_col])
                                               if genes_col is not None else ""),
                StandardColumns.PVALUE_GO: _num(r[pval_col]) if pval_col else None,
                StandardColumns.FDR: _num(r[fdr_col]) if fdr_col else None,
                StandardColumns.GENE_RATIO: f"{k}/{n_all or 1}",
                StandardColumns.BG_RATIO: f"{m_size}/{n_bg or 1}",
                "bg_count": m_size,
                "nes": _num(r[nes_col]) if nes_col else None,
                "fwer_pvalue": _num(r[fwer_col]) if fwer_col else None,
                StandardColumns.GENE_SET: direction,
                StandardColumns.DIRECTION: direction,
                StandardColumns.ONTOLOGY: ontology,
                "_engine": "prerank",
            })
        return pd.DataFrame(out_rows)

    def _assoc_term_sizes(self, organism: str, warnings: List[str]) -> Dict[str, int]:
        """GOATOOLS assoc term 크기 (M — §6.5). 세션 캐시."""
        key = f"assoc:{organism}"
        if key in self._assoc_cache:
            return self._assoc_cache[key]
        try:
            from goatools.anno.genetogo_reader import Gene2GoReader
            g2g = self._plain_gene2go(organism)   # Gene2GoReader는 gzip 미지원
            reader = Gene2GoReader(filename=str(g2g), taxids=[TAXID[organism]], prt=io.StringIO())
            sizes: Dict[str, int] = {}
            for ns_assoc in reader.get_assoc_nss(TAXID[organism]).values():
                for gid, go_ids in ns_assoc.items():
                    for go_id in go_ids:
                        sizes[go_id] = sizes.get(go_id, 0) + 1
            self._assoc_cache[key] = sizes
            return sizes
        except Exception as exc:
            warnings.append(f"W1 GOATOOLS assoc term-size computation failed — M approximated by hit count: {exc}")
            self._assoc_cache[key] = {}
            return {}

    def _kegg_pathway_map(self, organism: str, warnings: List[str]) -> Dict[str, str]:
        """KEGG pathway 이름(정규화) → ID (hsa#####/mmu#####). 세션 캐시.

        Enrichr KEGG Term 텍스트엔 ID가 없으므로(4A), KEGG 공식 pathway 목록
        (rest.kegg.jp/list/pathway/<org>)을 캐싱해 이름으로 역매핑한다 (G4).
        """
        if organism in self._kegg_pathway_cache:
            return self._kegg_pathway_cache[organism]
        try:
            path = self.cache.ensure_kegg_pathway_list(organism)
            mapping: Dict[str, str] = {}
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 2:
                    continue
                pathway_id = parts[0].split(":", 1)[-1].strip()  # 'path:hsa04110' -> 'hsa04110'
                name = _normalize_kegg_name(parts[1])
                if pathway_id and name:
                    mapping[name] = pathway_id
            self._kegg_pathway_cache[organism] = mapping
            return mapping
        except Exception as exc:
            warnings.append(f"W1 KEGG pathway list load failed — term_id left empty: {exc}")
            self._kegg_pathway_cache[organism] = {}
            return {}

    def _gmt_for(self, library_name: str,
                 warnings: List[str]) -> Optional[_GmtInfo]:
        """캐시 GMT 스냅샷 파싱 → _GmtInfo. 실패 시 None (+ W1).

        GO 라이브러리 col1은 `Name (GO:xxxxxxx)`, KEGG는 순수 이름.
        파싱 성공만 캐시하고 실패는 재시도한다(네트워크 복구 유연성).
        """
        if library_name in self._gmt_cache:
            return self._gmt_cache[library_name]
        try:
            path = self.cache.ensure_gmt(library_name)
            by_id: Dict[str, int] = {}
            by_name: Dict[str, int] = {}
            names: Dict[str, str] = {}
            universe = set()
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 3:
                    continue
                term = parts[0]
                genes = [p.strip() for p in parts[2:] if p.strip()]
                size = len(genes)
                by_name[term] = size
                universe.update(genes)
                m = _GO_ID_RE.search(term)
                if m:
                    go_id = m.group(0)
                    by_id[go_id] = size
                    names[go_id] = _strip_go_suffix(term)
            info = _GmtInfo(by_id=by_id, by_name=by_name, names=names, universe=len(universe))
            self._gmt_cache[library_name] = info
            return info
        except Exception as exc:
            warnings.append(f"W1 GMT parse failed — bg_ratio M approximated ({library_name}): {exc}")
            return None

    def _canonical_description(self, term_id: str, enrichr_term: str,
                               gmt: Optional[_GmtInfo],
                               warnings: List[str]) -> str:
        """A4: obo name > GMT name > Enrichr Term (괄호 제거)."""
        obo = self._obo_names_lazy(warnings)
        if term_id:
            if obo and term_id in obo:
                return obo[term_id]
            if gmt and term_id in gmt.names:
                return gmt.names[term_id]
        return _strip_go_suffix(enrichr_term)

    def _obo_names_lazy(self, warnings: List[str]) -> Dict[str, str]:
        """obo [Term] 블록 경량 파싱 (전체 GODag 로드 없이 이름만 — A4)."""
        try:
            obo_path = self.cache.ensure_obo("human")  # 종 중립 1개 파일
        except Exception as exc:
            warnings.append(f"W1 obo name load failed — keeping Enrichr Term: {exc}")
            return {}
        mtime = obo_path.stat().st_mtime
        if self._obo_names is not None and self._obo_mtime == mtime:
            return self._obo_names
        names: Dict[str, str] = {}
        cur_id, cur_name, in_term = None, None, False
        for line in obo_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line == "[Term]":
                if in_term and cur_id and cur_name:
                    names[cur_id] = cur_name
                cur_id, cur_name, in_term = None, None, True
            elif in_term:
                if line.startswith("id: GO:"):
                    cur_id = line[4:].strip()
                elif line.startswith("name:"):
                    cur_name = line[6:].strip()
        if in_term and cur_id and cur_name:
            names[cur_id] = cur_name
        self._obo_names, self._obo_mtime = names, mtime
        return names

    @staticmethod
    def _effective_engine(raw_results: List[RawResult]) -> Optional[str]:
        """raw 결과의 engine_effective 스탬프에서 실제 사용 엔진 유도 (architect P3)."""
        eff = [r.meta.get("engine_effective") for r in raw_results if r.meta]
        if not eff:
            return None
        return "online" if set(eff) == {"online"} else "local" if set(eff) == {"local"} \
            else "+".join(sorted(set(eff)))

    def _snapshot_provenance(self, organism: str, libraries: List[str]) -> Dict[str, Any]:
        """캐시에 존재하는 주석 스냅샷의 증명(read-only) — {종류: {file, sha256, fetched_at, ...}}.

        obo/gene2go/gene_info는 존재 여부 기준, prerank GMT는 라이브러리 해석.
        """
        rels = [("obo", "go-basic.obo")]
        taxid = TAXID.get(organism)
        if taxid:
            rels += [
                ("gene2go", GENE2GO_KEY % taxid),
                ("gene_info", GENE_INFO_KEY % taxid),
            ]
        for lib in libraries:
            name = _GMT_RESOLVE.get(organism, {}).get(lib)
            if name:
                rels.append((f"gmt_{lib}", f"{name}.gmt"))
        prov_fn = getattr(self.cache, "snapshot_provenance", None)
        if prov_fn is None:
            return {}
        out: Dict[str, Any] = {}
        for key, rel in rels:
            prov = prov_fn(rel)
            if prov:
                out[key] = prov
        return out

    def build_metadata(
        self,
        request: EnrichmentRequest,
        raw_results: List[RawResult],
        warnings: List[str],
        n_deg: int,
        n_bg: Optional[int],
        organism: str,
    ) -> Dict:
        """§6.9 재현성 메타데이터 (G15/A2 — enrichment_recipe 포함)."""
        meta: Dict = {
            "engine_versions": {
                name: _version(name)
                for name in ("gseapy", "goatools", "mygene", "statsmodels", "requests")
                if _version(name)
            },
            "engines_used": sorted({r.engine for r in raw_results}),
            "libraries_requested": request.libraries,
            "species": organism,
            "thresholds": {
                "fc_min": request.fc_min,
                "fdr_max": request.fdr_max,
                "direction": request.direction,
                "meta_cutoff": request.meta_cutoff,
            },
            "n_deg": n_deg,
            "n_background": n_bg,
            "background_mode": "custom" if request.background else
                               ("self" if n_bg is None else "dataset"),
            "engine_mode": request.engine,
            "engine_effective": self._effective_engine(raw_results),
            "stat_test": ("fisher_one_sided" if request.extra.get("one_sided")
                          else "fisher_two_sided"),
            "timestamps": {"run_at": _utc_now_iso()},
            "warnings": list(warnings),
            "enrichment_recipe": request.to_recipe_dict(),   # A2/F6 재실행 경로
        }
        if request.source == "meta" and request.extra.get("combined_datasets"):
            meta["meta_combined_datasets"] = list(request.extra["combined_datasets"])
        if request.extra.get("prerank"):
            meta["gsea_method"] = "prerank_gseapy"           # A7/G16 명칭 구분
        # 사용 주석 스냅샷 증명 (G15/재현성): 읽기 전용 — 다운로드 유발 없음.
        # 핀 모드(CacheManager(pin_snapshots=True))에서는 동일 sha256 스냅샷이
        # 계속 재사용되어 파이프라인과 유의성 정합에 필요한 버전 고정이 가능하다.
        snap = self._snapshot_provenance(organism, request.libraries)
        if snap:
            meta["annotation_snapshots"] = snap
        return meta


# --------------------------------------------------------------------------
# 헬퍼 (모듈 레벨 — 단위 테스트 대상 포함)
# --------------------------------------------------------------------------

def _apply_one_sided_fisher(records: List[Any]) -> List[Any]:
    """GOATOOLS 양측 p → 단측(enrichment) Fisher p + NS별 BH 재계산.

    파이프라인(clusterProfiler)은 enrichment 단측 Fisher를 사용하므로(동일-주석
    재검증에서 ρ=1.000/100% 일치 확인), 로컬 GO 경로의 one_sided=True 시
    (k=study_count, M=pop_count, n=study_n, N=pop_n)로 scipy fisher_exact
    alternative='greater' + fdr_bh를 재계산해 레코드 p_uncorrected/p_fdr_bh를 교체한다.
    기록의 카운트(propagate 적용)가 없으면 원래 p 유지.
    """
    from collections import defaultdict
    from scipy.stats import fisher_exact
    from statsmodels.stats.multitest import multipletests

    by_ns: Dict[str, List[float]] = defaultdict(list)
    for rec in records:
        try:
            k = int(getattr(rec, "study_count", 0)); n = int(getattr(rec, "study_n", 0))
            M = int(getattr(rec, "pop_count", 0)); N = int(getattr(rec, "pop_n", 0))
            table = [[k, M - k], [n - k, (N - M) - (n - k)]]
            if min(table[0] + table[1]) < 0:
                p = float(getattr(rec, "p_uncorrected", 1.0))
            else:
                _, p = fisher_exact(table, alternative="greater")
        except Exception:
            p = float(getattr(rec, "p_uncorrected", 1.0))
        by_ns[getattr(rec, "NS", "UNKNOWN")].append(p)
        setattr(rec, "_p_one_sided", p)
    for ns, ps in by_ns.items():
        if len(ps) >= 2:
            try:
                fdr = list(multipletests(ps, method="fdr_bh")[1])
            except Exception:
                fdr = list(ps)
        else:
            fdr = list(ps)
        i = 0
        for rec in records:
            if getattr(rec, "NS", "UNKNOWN") == ns:
                setattr(rec, "p_uncorrected", getattr(rec, "_p_one_sided"))
                setattr(rec, "p_fdr_bh", float(fdr[i]))
                i += 1
    return records


def _parse_label(label: str) -> Tuple[str, str]:
    """gene_set 라벨 → (direction, ontology) (§6.3)."""
    parts = label.upper().split("_")
    if "KEGG" in parts:
        ontology = "KEGG"
        rest = [p for p in parts if p != "KEGG"]
        direction = rest[0] if rest and rest[0] in ("UP", "DOWN", "TOTAL") else "TOTAL"
        return direction, ontology
    direction = parts[0] if parts and parts[0] in ("UP", "DOWN", "TOTAL") else "TOTAL"
    ontology = parts[1] if len(parts) > 1 and parts[1] in VALID_ONTOLOGIES else "UNKNOWN"
    return direction, ontology


def _parse_overlap(overlap: str) -> Tuple[int, int]:
    """'k/n' → (k, n). 파싱 불가 시 (0, 0)."""
    try:
        k, n = str(overlap).split("/")
        return int(k), int(n)
    except Exception:
        return 0, 0


def _genes_to_slash(genes) -> str:
    """[;/,] 다구분자 → '/' 재조인 (A5)."""
    if genes is None or (isinstance(genes, float) and pd.isna(genes)):
        return ""
    tokens = [t.strip() for t in _GENE_SPLIT_RE.split(str(genes))]
    return "/".join(t for t in tokens if t)


def _strip_go_suffix(term: str) -> str:
    """'Name (GO:0000000)' → 'Name' (표시 description용)."""
    return re.sub(r"\s*\(GO:\d{7}\)\s*$", "", str(term)).strip()


def _normalize_kegg_name(term: str) -> str:
    """KEGG pathway 이름 정규화 (대소문자/organism 접미사 제거) — Enrichr Term ↔
    KEGG list/pathway 이름 매칭용 (둘 다 organism 접미사 표기가 다를 수 있음:
    'Phagosome' vs 'Phagosome - Homo sapiens (human)')."""
    return _KEGG_NAME_SUFFIX_RE.sub("", str(term).strip().lower()).strip()


def _num(val):
    if val is None:
        return None
    try:
        f = float(val)
        return f
    except Exception:
        return None


def _version(pkg: str) -> Optional[str]:
    try:
        from importlib import metadata
        return metadata.version(pkg)
    except Exception:
        return None


def _utc_now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _default_cache_dir() -> Path:
    from utils.data_path_config import DataPathConfig
    return DataPathConfig.get_enrichment_cache_dir()


def _strip_gmt_prefix(term: str) -> str:
    """gseapy.prerank Term 접두어('gmt_<lib>.gmt__') 제거 (실데이터 실측)."""
    return re.sub(r"^.*\.gmt__", "", term)


def _col(df: pd.DataFrame, candidates) -> Optional[str]:
    """DataFrame에서 후보 컬럼 중 존재하는 첫 컬럼 (대소문자 상관)."""
    lower = {str(c).lower(): c for c in df.columns}
    for cand in candidates:
        if str(cand).lower() in lower:
            return lower[str(cand).lower()]
    return None
