"""
DA Peak Overlap 유틸리티

여러 ATAC-seq DA(Differential Accessibility) 데이터셋을 peak_id(또는 좌표) 기준으로
비교하기 위한 set 연산 헬퍼.

전제: 비교 대상 데이터셋들이 같은 peak set(consensus/union peak)에서 나와야
peak_id 기반 비교가 유효하다. 조건별로 peak을 독립적으로 호출한 경우
bedtools intersect/merge로 좌표를 reconcile하는 외부 전처리가 먼저 필요하다.
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from models.standard_columns import StandardColumns as SC

logger = logging.getLogger(__name__)


def get_peak_set(
    dataset,
    padj_threshold: Optional[float] = None,
    log2fc_threshold: Optional[float] = None,
) -> set:
    """ATAC_SEQ Dataset에서 peak_id set을 추출.

    peak_id 컬럼이 없으면 chr:start-end 로 합성한다.
    padj_threshold/log2fc_threshold가 주어지면 유의미한 peak만 포함한다.
    """
    df = dataset.dataframe

    if SC.PEAK_ID in df.columns:
        peak_id = df[SC.PEAK_ID].astype(str)
    elif {SC.CHROMOSOME, SC.PEAK_START, SC.PEAK_END} <= set(df.columns):
        peak_id = (
            df[SC.CHROMOSOME].astype(str) + ":" +
            df[SC.PEAK_START].astype(str) + "-" +
            df[SC.PEAK_END].astype(str)
        )
    else:
        logger.warning(f"Dataset '{dataset.name}': no peak_id or coordinate columns found")
        return set()

    mask = pd.Series(True, index=df.index)
    if padj_threshold is not None and SC.ADJ_PVALUE in df.columns:
        mask &= df[SC.ADJ_PVALUE] <= padj_threshold
    if log2fc_threshold is not None and SC.LOG2FC in df.columns:
        mask &= df[SC.LOG2FC].abs() >= log2fc_threshold

    return set(peak_id[mask].dropna())


def check_consensus(datasets) -> Optional[str]:
    """peak_id 교집합 비율을 점검해 consensus peak set 불일치 경고 메시지를 반환.

    문제가 없어 보이면 None을 반환한다.
    """
    sets = [get_peak_set(ds) for ds in datasets]
    named_sets = [(ds.name, s) for ds, s in zip(datasets, sets) if s]
    if len(named_sets) < 2:
        return None

    pairwise_overlaps = []
    for i in range(len(named_sets)):
        for j in range(i + 1, len(named_sets)):
            s_i, s_j = named_sets[i][1], named_sets[j][1]
            smaller = min(len(s_i), len(s_j))
            if smaller > 0:
                pairwise_overlaps.append(len(s_i & s_j) / smaller)

    if pairwise_overlaps and max(pairwise_overlaps) < 0.05:
        return (
            "선택한 데이터셋 간 peak_id가 거의 겹치지 않습니다 "
            f"(최대 교집합 비율 {max(pairwise_overlaps):.1%}).\n"
            "서로 다른 peak set에서 생성된 결과일 수 있습니다. "
            "동일한 consensus peak set에서 나온 DA 결과인지 확인하세요."
        )
    return None
