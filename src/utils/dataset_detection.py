"""
파일 -> Dataset 자동 판별/로딩.

GUI(MainPresenter.load_dataset)와 CLI가 공유하는 단일 진실원천 — "어떤 파일을
어떤 전용 로더로 읽을지" 판별 로직은 여기 한 곳에만 있고, 호출자(presenter 또는
CLI)는 반환된 Dataset으로 각자 필요한 후처리(GUI 탭 갱신, 또는 파일 export)만
한다. 반입 경로가 GUI와 CLI에서 따로 구현되어 드리프트하는 걸 막기 위한 설계 —
GO/KEGG·ATAC 컬럼 매핑이 경로마다 다르게 구현돼 있던 문제(§반입 일반성 감사)와
같은 클래스의 버그를 애초에 만들지 않는 게 목적이다.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from models.data_models import Dataset, DatasetType


def looks_like_go_frame(df: pd.DataFrame) -> bool:
    """GO/KEGG 표준(또는 R clusterProfiler 어휘) 프레임 감지 (plan P3-7 복원 경로)."""
    cols = {str(c).lower() for c in df.columns}
    idish = bool(cols & {"term_id", "go id", "kegg id", "id", "go.id", "kegg.id"})
    descish = bool(cols & {"description", "go term", "kegg pathway", "term",
                           "go.term", "kegg.pathway"})
    ontish = bool(cols & {"ontology", "direction", "gene_set"})
    return (idish and descish) or (ontish and descish)


def _load_with_type_hint(file_path: Path, final_name: str, dataset_type: DatasetType,
                         data_loader, column_mapper_callback, logger) -> Dataset:
    """명시 타입으로 로드 — 자동 감지 없이 해당 타입 로더로 직행한다.

    ATAC/GO/MULTI_GROUP/DE 네 타입을 지원한다. GO는 Excel이면 다중 시트 병합이
    필요한 GOKEGGLoader를, 그 외 포맷이면 표준화 파이프라인을 쓴다.
    """
    if dataset_type == DatasetType.ATAC_SEQ:
        from utils.atac_seq_loader import ATACSeqLoader
        return ATACSeqLoader().load(file_path, final_name, column_mapper_callback)

    if dataset_type == DatasetType.MULTI_GROUP:
        from utils.multi_group_loader import MultiGroupLoader
        if file_path.suffix.lower() in ('.csv', '.parquet'):
            return MultiGroupLoader().load(file_path, final_name)
        return MultiGroupLoader().load_from_dataframe(
            data_loader._read_table(file_path), file_path, final_name)

    if dataset_type == DatasetType.COMPOSITION:
        from utils.composition_loader import CompositionLoader
        return CompositionLoader().load(file_path, final_name)

    if dataset_type == DatasetType.EXPRESSION_SUMMARY:
        from utils.expression_summary_loader import ExpressionSummaryLoader
        return ExpressionSummaryLoader().load(file_path, final_name)

    if dataset_type == DatasetType.EXPRESSION_DISTRIBUTION:
        from utils.expression_distribution_loader import ExpressionDistributionLoader
        return ExpressionDistributionLoader().load(file_path, final_name)

    if dataset_type == DatasetType.GO_ANALYSIS:
        if file_path.suffix.lower() in ('.xlsx', '.xls', '.xlsm'):
            from utils.go_kegg_loader import GOKEGGLoader
            return GOKEGGLoader().load_from_excel(
                file_path, final_name, column_mapper_callback=column_mapper_callback)
        from utils.go_kegg_loader import ensure_go_required_columns, standardize_go_dataframe
        std = standardize_go_dataframe(data_loader._read_table(file_path), logger)
        std = ensure_go_required_columns(std, column_mapper_callback, logger)
        return Dataset(name=final_name, dataset_type=DatasetType.GO_ANALYSIS,
                       file_path=file_path, dataframe=std)

    return data_loader.load_from_file(
        file_path, final_name, dataset_type=dataset_type,
        column_mapper_callback=column_mapper_callback)


def load_any_dataset(
    file_path: Path,
    data_loader,
    name: Optional[str] = None,
    dataset_type_hint: Optional[DatasetType] = None,
    column_mapper_callback: Optional[Callable] = None,
    logger: Optional[logging.Logger] = None,
) -> Dataset:
    """파일 확장자/내용으로 적절한 전용 로더를 선택해 Dataset으로 로드한다.

    Args:
        file_path: Excel / CSV / Parquet / TXT / TSV 파일 경로
        data_loader: DataLoader 인스턴스 (DE/GO Excel 폴백 + 자동 타입 감지에 사용 —
                    호출자가 들고 있는 걸 재사용해 custom_mapping 캐시를 공유한다)
        name: 데이터셋 이름 (None이면 파일명)
        dataset_type_hint: 지정하면 자동 감지(스니핑) 체인을 전부 건너뛰고 해당
                          타입 로더로 직행한다 — 파일의 컬럼명이 인식 패턴과 안 맞아
                          감지 휴리스틱이 실패해도 사용자가 명시한 타입으로 강제하고,
                          필수 컬럼이 없으면 (감지가 아니라) column_mapper_callback으로
                          수동 매핑하게 한다. 현재 DatasetType.ATAC_SEQ만 지원.
        column_mapper_callback: 필수 컬럼이 자동 인식 안 될 때 호출되는 콜백 —
                               (df, dataset_type, auto_mapping) -> {표준: 원본} 매핑.
                               None이면 (대화형 UI가 없는 CLI 등) 인식 실패 시
                               곧바로 ValueError.
        logger: 로그 출력 대상 (None이면 모듈 로거)

    Returns:
        로드된 Dataset 객체

    Raises:
        ValueError / FileNotFoundError 등 — 각 전용 로더가 던지는 에러를 그대로 전파
    """
    logger = logger or logging.getLogger(__name__)
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()
    final_name = name or file_path.stem

    # ── 명시적 타입 힌트: 자동 감지 체인을 건너뛰고 직행 ──
    if dataset_type_hint is not None:
        return _load_with_type_hint(
            file_path, final_name, dataset_type_hint, data_loader,
            column_mapper_callback, logger)

    # ── CSV / Parquet: chromVAR diff TF 감지 ─────────────────────────
    if suffix in ('.csv', '.parquet'):
        from utils.chromvar_loader import ChromVARLoader
        if ChromVARLoader.is_chromvar_file(file_path):
            return ChromVARLoader().load(file_path, final_name)

    # ── TXT / TSV: Motif enrichment 또는 TF Footprint 파일 감지 ────────
    if suffix in ('.txt', '.tsv'):
        from utils.footprint_loader import FootprintLoader
        if FootprintLoader.is_footprint_file(file_path):
            return FootprintLoader().load(file_path, final_name)
        from utils.motif_loader import MotifLoader
        if MotifLoader.is_motif_file(file_path):
            return MotifLoader().load(file_path, final_name)

    # ── CSV / Parquet: ATAC / MultiGroup 빠른 감지 ───────────────────
    if suffix in ('.csv', '.parquet'):
        try:
            peek = pd.read_csv(file_path, nrows=5) if suffix == '.csv' \
                   else pd.read_parquet(file_path)

            from utils.atac_seq_loader import ATACSeqLoader
            if ATACSeqLoader.is_atac_dataframe(peek):
                return ATACSeqLoader().load(file_path, final_name, column_mapper_callback)

            # GO 프레임은 MultiGroup 감지(pvalue/fdr 등 통계 컬럼 보유)와 충돌하므로 우선 판별
            if looks_like_go_frame(peek):
                from utils.go_kegg_loader import standardize_go_dataframe
                df = (pd.read_csv(file_path) if suffix == '.csv'
                      else pd.read_parquet(file_path))
                std = standardize_go_dataframe(df)
                return Dataset(name=final_name, dataset_type=DatasetType.GO_ANALYSIS,
                               dataframe=std)

            # 세포타입 조성(propeller/limma)은 PropMean 컬럼/FDR 패턴으로 판별.
            # Multi-Group(padj + 숫자형 샘플 3개↑)보다 먼저 확인해야 PropMean 컬럼이
            # 샘플로 오인되는 것을 막을 수 있다.
            from utils.composition_loader import CompositionLoader
            if CompositionLoader.is_composition_dataframe(peek):
                return CompositionLoader().load(file_path, final_name)

            # pseudobulk/quantile long-format. expression_summary long과 구분하기
            # 위해 sample 또는 quantile 통계 컬럼이 함께 있어야 한다.
            from utils.expression_distribution_loader import ExpressionDistributionLoader
            if ExpressionDistributionLoader.is_distribution_dataframe(peek):
                return ExpressionDistributionLoader().load(file_path, final_name)

            from utils.multi_group_loader import MultiGroupLoader
            if MultiGroupLoader.is_multi_group_dataframe(peek):
                return MultiGroupLoader().load(file_path, final_name)
        except Exception as e:
            logger.warning(f"Quick detection failed: {e}, falling through")

    # ── Excel: GO/KEGG 또는 DE 감지 ──────────────────────────────────
    if suffix in ('.xlsx', '.xls', '.xlsm'):
        try:
            test_df = pd.read_excel(file_path, nrows=10)
            detected_type = data_loader._detect_dataset_type(test_df)
            logger.debug(f"Quick type detection: {detected_type.value}")

            if detected_type == DatasetType.GO_ANALYSIS:
                from utils.go_kegg_loader import GOKEGGLoader
                return GOKEGGLoader().load_from_excel(
                    file_path, final_name, column_mapper_callback=column_mapper_callback)
        except Exception as e:
            logger.warning(f"Quick type detection failed: {e}, using standard loader")

    # ── 기본: DE 데이터셋 로더 (CSV/TSV/Parquet 포함) ────────────────
    return data_loader.load_from_file(
        file_path, final_name, column_mapper_callback=column_mapper_callback)
