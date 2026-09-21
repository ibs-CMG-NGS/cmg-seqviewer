"""
Background Workers for GO/KEGG Analysis

- EnrichmentWorker : GO/KEGG enrichment 실행 (plan G12/G14 — EnrichmentRequest → EnrichmentResult)
- GOClusteringWorker: 유지 (기존 클러스터링 백그라운드 작업)
"""

from dataclasses import dataclass, field
from typing import List, Optional

import logging

import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal

from models.enrichment_models import EnrichmentResult, EnrichmentRequest, ErrorKind
from utils.enrichment_analyzer import EnrichmentError
from utils.go_clustering import GOClustering


# --------------------------------------------------------------------------
# GO/KEGG enrichment worker (plan §8 G12 — GOEnrichmentWorker 대체)
# --------------------------------------------------------------------------

@dataclass
class ErrorPayload:
    """worker 실패 페이로드 (dialog가 ErrorKind별 UX 분기 — G14)."""

    kind: ErrorKind
    message: str
    warnings: List[str] = field(default_factory=list)


class EnrichmentWorker(QThread):
    """enrichment 분석 백그라운드 실행.

    진입: EnrichmentRequest (source=dataset → dataframe 필요, paste → gene_list,
          meta → meta dataframe). 결과: EnrichmentResult (표준 병합 DataFrame +
          §6.9 metadata + enrichment_recipe).
    """

    progress = pyqtSignal(int)
    result_ready = pyqtSignal(object)   # EnrichmentResult
    failed = pyqtSignal(object)          # ErrorPayload

    def __init__(self, request: EnrichmentRequest,
                 analyzer=None,
                 dataframe: Optional[pd.DataFrame] = None,
                 parent=None):
        """
        Args:
            request: 분석 요청 (source ①/②/③, 임계값, 종, 라이브러리, 모드, background)
            analyzer: EnrichmentAnalyzer (테스트 주입용; None이면 기본 생성)
            dataframe: source=dataset/meta용 데이터프레임 (dialog가 전달)
        """
        super().__init__(parent)
        self.request = request
        self._analyzer = analyzer
        self.passed_dataframe = dataframe
        self._cancelled = False
        self.logger = logging.getLogger(__name__)

    def cancel(self):
        """취소 플래그 (다음 단계 경계에서 검사, P2-4)."""
        self._cancelled = True

    # ------------------------------------------------------------------ run

    def run(self):
        try:
            problems = self.request.validate()
            if problems:
                self._fail(ErrorKind.UNKNOWN, "Request validation failed: " + "; ".join(problems))
                return

            if self._cancelled:
                return
            self.progress.emit(5)
            from utils.enrichment_analyzer import EnrichmentAnalyzer
            from models.enrichment_models import DIRECTION_ALL
            analyzer = self._analyzer or EnrichmentAnalyzer()

            combined = (self.request.source == "dataset"
                        and self.request.direction == DIRECTION_ALL)

            if combined:
                deg, raw_results, warnings, background = self._run_combined_directions(analyzer)
                if deg is None:  # _fail() 이미 호출됨
                    return
                if self._cancelled:
                    return
            else:
                # ---- DEG 입력 추출 (§6.1 — G3) ----
                deg = self._extract_deg()
                if self._cancelled:
                    return
                self.progress.emit(20)
                if not deg.symbols:
                    self._fail(ErrorKind.NO_INPUT_GENES,
                               "Extracted DEG genes: 0 (adjust thresholds/filters).")
                    return

                # ---- 배경 결정 (G8/ADR-2 2A) ----
                # custom background → 2A 로컬 강제. DE 전체 population은 별도
                # population_symbols로 전달 (2A 트리거 없음 — auto→local/mouse 포함, architect P2-1).
                background = self.request.background
                population_symbols = None
                if background is None and self.request.source == "dataset":
                    population_symbols = self._dataset_symbols() or None

                # ---- 엔진 실행 ----
                libraries = list(self.request.libraries or ["BP", "CC", "MF", "KEGG"])
                if self.request.extra.get("prerank") and self.request.source == "meta":
                    # Phase 4 M4b: meta 랭킹(meta_z 또는 -log10(p)xsign) → gseapy.prerank (캐시 GMT)
                    from utils.deg_input import extract_ranked
                    ranked = extract_ranked(self.passed_dataframe,
                                            self.request.meta_cutoff or 0.05)
                    if not ranked:
                        self._fail(ErrorKind.NO_INPUT_GENES,
                                   "Meta ranking extraction returned 0 results (adjust the cutoff).")
                        return
                    raw_results, warnings = analyzer.enrich_prerank(
                        ranked, organism=deg.species, libraries=libraries,
                        direction=deg.direction)
                else:
                    raw_results, warnings = analyzer.enrich_ora(
                        deg.symbols,
                        background=background,
                        organism=deg.species,
                        libraries=libraries,
                        engine=self.request.engine,
                        direction=deg.direction,
                        population_symbols=population_symbols,
                        one_sided=bool(self.request.extra.get("one_sided")),
                    )
            if self._cancelled:
                return
            self.progress.emit(60)

            # ---- 표준 변환 (§6.3~6.6) ----
            df, conv_warnings = analyzer.to_standard(raw_results, organism=deg.species)
            warnings = warnings + conv_warnings
            if self._cancelled:
                return
            self.progress.emit(85)

            # ---- 결과 패키징 (G15 metadata + recipe) ----
            metadata = analyzer.build_metadata(
                self.request, raw_results, warnings,
                n_deg=len(deg.symbols),
                n_bg=len(background) if background else None,
                organism=deg.species,
            )
            result = EnrichmentResult(
                dataframe=df,
                request=self.request,
                metadata=metadata,
                warnings=warnings,
                engine_used=metadata.get("engine_effective") or self.request.engine,
                dataset_name=f"Enrichment: {self._input_label()}",
            )
            self.progress.emit(100)
            self.result_ready.emit(result)
        except EnrichmentError as exc:
            self._fail(exc.kind, exc.message, exc.warnings)
        except Exception as exc:  # noqa: BLE001 — worker 경계에서 모든 예외를 페이로드로
            self.logger.exception("Enrichment worker failed")
            self._fail(ErrorKind.UNKNOWN, f"Analysis failed: {exc}")

    # ------------------------------------------------------------ internals

    def _extract_deg(self, direction_override: Optional[str] = None):
        from utils import deg_input
        src = self.request.source
        if src == "dataset":
            df = self.passed_dataframe
            if df is None:
                raise EnrichmentError(ErrorKind.UNKNOWN,
                                      "source=dataset: no dataframe was provided.")
            return deg_input.extract_deg_from_dataset(
                df, self.request.fc_min or 0.0, self.request.fdr_max or 1.0,
                direction_override or self.request.direction, self.request.organism,
            )
        if src == "meta":
            df = self.passed_dataframe
            if df is None:
                raise EnrichmentError(ErrorKind.UNKNOWN,
                                      "source=meta: no meta dataframe was provided.")
            return deg_input.extract_meta_signature(
                df, self.request.meta_cutoff or 0.05,
                require_direction_concordant=self.request.meta_direction_required,
                species=self.request.organism,
            )
        # paste
        from utils.deg_input import DegInput
        return DegInput(symbols=[s for s in self.request.gene_list if s],
                        direction="TOTAL", species=self.request.organism, meta={})

    def _run_combined_directions(self, analyzer):
        """UP/DOWN/TOTAL을 각각 추출·실행 후 raw_results를 하나로 합친다.

        파이프라인 반입 결과(final_go_result.xlsx)는 UP/DOWN/TOTAL 시트가 모두
        한 데이터셋에 들어있다 — to_standard()는 raw_results 목록의 direction이
        섞여 있어도 그대로 병합하므로, 이 세 번의 enrich_ora 결과를 합쳐서 한 번만
        to_standard()에 넘기면 동일한 형태가 된다.

        Returns:
            (deg_for_metadata, raw_results, warnings, background) —
            실패 시 (None, [], [], None) + self._fail() 이미 호출됨.
        """
        degs = {}
        for d in ("UP", "DOWN", "TOTAL"):
            degs[d] = self._extract_deg(direction_override=d)
        if self._cancelled:
            return None, [], [], None
        self.progress.emit(20)

        if all(not deg_d.symbols for deg_d in degs.values()):
            self._fail(ErrorKind.NO_INPUT_GENES,
                       "Extracted DEG genes: 0 for UP/DOWN/TOTAL (adjust thresholds/filters).")
            return None, [], [], None

        background = self.request.background
        population_symbols = None if background is not None else (self._dataset_symbols() or None)
        libraries = list(self.request.libraries or ["BP", "CC", "MF", "KEGG"])

        all_raw_results = []
        warnings: List[str] = []
        runnable = [d for d, deg_d in degs.items() if deg_d.symbols]
        for i, d in enumerate(("UP", "DOWN", "TOTAL")):
            deg_d = degs[d]
            if not deg_d.symbols:
                warnings.append(f"W1 direction={d}: 0 DEG genes — skipped in the combined run.")
                continue
            raw_results, w = analyzer.enrich_ora(
                deg_d.symbols,
                background=background,
                organism=deg_d.species,
                libraries=libraries,
                engine=self.request.engine,
                direction=d,
                population_symbols=population_symbols,
                one_sided=bool(self.request.extra.get("one_sided")),
            )
            all_raw_results.extend(raw_results)
            warnings.extend(w)
            if self._cancelled:
                return None, [], [], None
            self.progress.emit(20 + int(40 * (runnable.index(d) + 1) / len(runnable)))

        # 메타데이터용 대표 DegInput: TOTAL(전체 DEG 상위집합) 우선, 없으면 실행된 것 중 하나.
        deg_for_metadata = degs["TOTAL"] if degs["TOTAL"].symbols else degs[runnable[0]]
        return deg_for_metadata, all_raw_results, warnings, background

    def _dataset_symbols(self) -> List[str]:
        df = self.passed_dataframe
        if df is None:
            return []
        col = "symbol" if "symbol" in df.columns else \
            ("gene_id" if "gene_id" in df.columns else None)
        if col is None:
            return []
        return [str(s) for s in df[col].dropna().unique() if str(s)]

    def _input_label(self) -> str:
        req = self.request
        if req.source == "dataset" and req.dataset_name:
            return req.dataset_name
        if req.source == "meta":
            return "Meta Comparison"
        return "Gene List"

    def _fail(self, kind: ErrorKind, message: str,
              warnings: Optional[List[str]] = None):
        self.logger.error("Enrichment worker failed [%s]: %s", kind.value, message)
        self.failed.emit(ErrorPayload(kind=kind, message=message,
                                      warnings=list(warnings or [])))


# --------------------------------------------------------------------------
# GO clustering worker (유지 — plan §8 "GOClusteringWorker 유지")
# --------------------------------------------------------------------------

class GOClusteringWorker(QThread):
    """
    GO Term 클러스터링 백그라운드 작업

    Signals:
        progress: 진행률 (0-100)
        finished: 작업 완료 (clustered_df, clusters_dict)
        error: 오류 발생 (error_message)
    """

    progress = pyqtSignal(int)
    finished = pyqtSignal(pd.DataFrame, dict)
    error = pyqtSignal(str)

    def __init__(self, df: pd.DataFrame,
                 kappa_threshold: float = 0.4,
                 total_genes: Optional[int] = None):
        super().__init__()
        self.df = df
        self.kappa_threshold = kappa_threshold
        self.total_genes = total_genes
        self.logger = logging.getLogger(__name__)

    def run(self):
        """클러스터링 실행"""
        try:
            self.progress.emit(10)
            clusterer = GOClustering(kappa_threshold=self.kappa_threshold)
            self.progress.emit(30)
            clustered_df, clusters = clusterer.cluster_terms(
                self.df, total_genes=self.total_genes)
            self.progress.emit(80)
            cluster_stats = clusterer.calculate_cluster_statistics(clustered_df, clusters)
            self.progress.emit(100)
            self.finished.emit(clustered_df, clusters)
        except Exception as e:
            self.logger.error(f"Clustering failed: {e}", exc_info=True)
            self.error.emit(str(e))