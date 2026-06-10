"""
TF Footprint Result Loader

TOBIAS BINDetect 결과 파일(bindetect_results.txt)을 파싱한다.

핵심 파싱 과제:
  - 조건명이 컬럼명에 포함됨 (동적 컬럼)
    예) Acute_1D_mean_score, Acute_1D_Control_change
  - 헤더를 읽어 조건명을 자동 감지

지원 파일:
  - TOBIAS BINDetect: bindetect_results.txt  (탭 구분)

Usage:
    loader = FootprintLoader()
    dataset = loader.load(Path("BINDetect_results/bindetect_results.txt"))
    # dataset.metadata['cond1_name'], ['cond2_name'] 으로 조건명 확인
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

from models.data_models import Dataset, DatasetType
from models.standard_columns import StandardColumns as SC

logger = logging.getLogger(__name__)


class FootprintLoader:
    """TOBIAS BINDetect bindetect_results.txt 로더."""

    def load(self, path: Path, name: Optional[str] = None) -> Dataset:
        path = Path(path)
        name = name or path.stem

        df, cond1, cond2 = self._parse_bindetect(path)

        logger.info(
            f"FootprintLoader: {len(df)} TFs from {path.name} "
            f"(cond1={cond1}, cond2={cond2})"
        )
        return Dataset(
            name=name,
            dataset_type=DatasetType.TF_FOOTPRINT,
            file_path=path,
            dataframe=df,
            original_columns={},
            metadata={
                "source_tool": "TOBIAS BINDetect",
                "file_name": path.name,
                "cond1_name": cond1,
                "cond2_name": cond2,
            },
        )

    # ── 파일 형식 감지 ────────────────────────────────────────────────────

    @staticmethod
    def is_footprint_file(path: Path) -> bool:
        """파일명/내용으로 TOBIAS BINDetect 결과 파일인지 판별."""
        fname = path.name.lower()
        if "bindetect_results" in fname and fname.endswith(".txt"):
            return True
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                head = f.readline()
            # 헤더에 _mean_score 또는 _change 패턴이 있으면 BINDetect로 판단
            if "_mean_score" in head and ("_change" in head or "_pvalue" in head):
                return True
        except OSError:
            pass
        return False

    # ── 파서 ──────────────────────────────────────────────────────────────

    def _parse_bindetect(self, path: Path) -> Tuple[pd.DataFrame, str, str]:
        """
        bindetect_results.txt 파싱.

        Returns:
            (DataFrame, cond1_name, cond2_name)
        """
        df = pd.read_csv(path, sep="\t", encoding="utf-8")
        cond1, cond2 = self._detect_conditions(df.columns.tolist())

        rename = {}
        for col in df.columns:
            cl = col.lower()
            # motif 이름/ID
            if cl in ("name", "motif_name"):
                rename[col] = SC.FOOTPRINT_MOTIF_NAME
            elif cl in ("output_prefix", "motif_id"):
                rename[col] = SC.FOOTPRINT_MOTIF_ID
            # cond1 컬럼
            elif col == f"{cond1}_mean_score":
                rename[col] = SC.COND1_SCORE
            elif col == f"{cond1}_bound":
                rename[col] = SC.COND1_BOUND
            # cond2 컬럼
            elif col == f"{cond2}_mean_score":
                rename[col] = SC.COND2_SCORE
            elif col == f"{cond2}_bound":
                rename[col] = SC.COND2_BOUND
            # change / pvalue (cond1_cond2 접두사)
            elif col == f"{cond1}_{cond2}_change":
                rename[col] = SC.FOOTPRINT_CHANGE
            elif col == f"{cond1}_{cond2}_pvalue":
                rename[col] = SC.FOOTPRINT_PVALUE

        df = df.rename(columns=rename)

        # 숫자 변환
        for col in [SC.COND1_SCORE, SC.COND2_SCORE, SC.FOOTPRINT_CHANGE,
                    SC.FOOTPRINT_PVALUE, SC.COND1_BOUND, SC.COND2_BOUND]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # motif_name 폴백: motif_id 에서 추출
        if SC.FOOTPRINT_MOTIF_NAME not in df.columns and SC.FOOTPRINT_MOTIF_ID in df.columns:
            df[SC.FOOTPRINT_MOTIF_NAME] = df[SC.FOOTPRINT_MOTIF_ID].apply(
                self._extract_tf_name_from_id
            )

        # -log10(pvalue) 계산
        if SC.FOOTPRINT_PVALUE in df.columns:
            import numpy as np
            pv = df[SC.FOOTPRINT_PVALUE].clip(lower=1e-300)
            df["fp_neg_log_pvalue"] = -np.log10(pv)

        return df.reset_index(drop=True), cond1, cond2

    # ── 조건명 감지 ───────────────────────────────────────────────────────

    @staticmethod
    def _detect_conditions(columns: list[str]) -> Tuple[str, str]:
        """
        컬럼명 패턴에서 조건명 2개를 추출한다.

        전략:
          1. `{cond1}_{cond2}_change` 패턴을 찾아 `(cond1, cond2)` 반환
          2. 없으면 `{cond}_mean_score` 패턴에서 2개 추출
        """
        # 전략 1: _change 컬럼 이용
        # 조건명 자체에 '_'가 포함될 수 있으므로 _mean_score 컬럼 목록을 먼저 수집
        score_cols = [c for c in columns if c.endswith("_mean_score")]
        if len(score_cols) >= 2:
            cond_names = [c[: -len("_mean_score")] for c in score_cols[:2]]
            cond1, cond2 = cond_names[0], cond_names[1]
            # 검증: {cond1}_{cond2}_change 또는 {cond2}_{cond1}_change 존재 여부
            if f"{cond1}_{cond2}_change" in columns:
                return cond1, cond2
            if f"{cond2}_{cond1}_change" in columns:
                return cond2, cond1
            # change 컬럼 없어도 score가 있으면 그냥 반환
            return cond1, cond2

        # 전략 2: _change 패턴에서 역추론
        for col in columns:
            if col.endswith("_change"):
                # score_cols에서 prefix 찾기
                prefix = col[: -len("_change")]
                for sc in score_cols:
                    c = sc[: -len("_mean_score")]
                    remainder = prefix[len(c):]
                    if remainder.startswith("_"):
                        cond2 = remainder[1:]
                        if f"{cond2}_mean_score" in columns:
                            return c, cond2

        # 감지 실패 → 기본값
        logger.warning("Could not detect condition names from BINDetect columns; using 'cond1'/'cond2'")
        return "cond1", "cond2"

    # ── 헬퍼 ──────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_tf_name_from_id(raw: str) -> str:
        """
        "MA0002.1_RUNX1" → "RUNX1"
        "MA0002.1" → "MA0002.1"
        """
        raw = str(raw).strip()
        parts = raw.split("_", 1)
        # 첫 부분이 JASPAR ID 형식(MA\d+\.\d+)이면 두 번째 부분이 TF 이름
        if len(parts) == 2 and re.match(r"^[A-Z]{2}\d+\.\d+$", parts[0]):
            return parts[1]
        return raw
