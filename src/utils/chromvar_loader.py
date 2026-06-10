"""
chromVAR Differential TF Activity Loader

지원 파일:
  - diff_tf CSV:  motif, mean_compare, mean_base, delta, p_value, padj
  - seqviewer parquet: tf_name, mean_zscore_compare, mean_zscore_base,
                       delta_zscore, p_value, padj

TF 이름 조회:
  - 같은 디렉토리 또는 부모 디렉토리에서 tf_variability.csv 를 자동 탐색
  - motif(JASPAR ID) → name 컬럼으로 조인

Usage:
    loader = ChromVARLoader()
    dataset = loader.load(Path("Acute_1D_vs_Control_diff_tf.csv"), name="Acute_1D")
    dataset = loader.load(Path("Acute_1D_vs_Control_chromVAR_DiffTF.parquet"))
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from models.data_models import Dataset, DatasetType
from models.standard_columns import StandardColumns as SC

logger = logging.getLogger(__name__)

# tf_variability.csv 를 탐색할 후보 파일명
_VARIABILITY_NAMES = ("tf_variability.csv", "tf_variability.tsv")


class ChromVARLoader:

    def load(self, path: Path, name: Optional[str] = None) -> Dataset:
        path = Path(path)
        name = name or path.stem
        suffix = path.suffix.lower()

        if suffix == ".parquet":
            df = self._load_parquet(path)
        elif suffix in (".csv", ".tsv"):
            df = self._load_csv(path)
        else:
            raise ValueError(f"Unsupported format for chromVAR loader: {suffix}")

        # TF 이름 조인
        var_path = self._find_variability_file(path)
        if var_path:
            df = self._join_tf_names(df, var_path)
            logger.info(f"ChromVARLoader: joined TF names from {var_path.name}")
        else:
            logger.warning("ChromVARLoader: tf_variability.csv not found; using JASPAR IDs as names")
            if SC.CHROMVAR_TF_NAME not in df.columns:
                df[SC.CHROMVAR_TF_NAME] = df[SC.CHROMVAR_MOTIF_ID]

        # -log10(padj) 계산
        import numpy as np
        padj = df[SC.CHROMVAR_PADJ].clip(lower=1e-300)
        df["chromvar_neg_log_padj"] = -np.log10(padj)

        logger.info(
            f"ChromVARLoader: {len(df)} TFs from {path.name}"
            f"  (sig padj<0.05: {(df[SC.CHROMVAR_PADJ] < 0.05).sum()})"
        )
        return Dataset(
            name=name,
            dataset_type=DatasetType.CHROMVAR_DIFF_TF,
            file_path=path,
            dataframe=df,
            original_columns={},
            metadata={"source_tool": "chromVAR", "file_name": path.name},
        )

    # ── 파일 형식 감지 ─────────────────────────────────────────────────

    @staticmethod
    def is_chromvar_file(path: Path) -> bool:
        """파일명 또는 헤더로 chromVAR diff TF 파일 판별."""
        fname = path.name.lower()
        # 파일명 패턴
        if "chromvar" in fname or "diff_tf" in fname:
            return True
        # CSV 헤더 확인
        if path.suffix.lower() in (".csv", ".tsv"):
            try:
                with open(path, encoding="utf-8", errors="replace") as f:
                    head = f.readline().lower()
                cols = {c.strip().strip('"') for c in head.split(",")}
                if {"motif", "delta", "padj"} <= cols:
                    return True
                if {"motif", "mean_compare", "mean_base"} <= cols:
                    return True
            except OSError:
                pass
        # Parquet 파일명 패턴
        if path.suffix.lower() == ".parquet" and ("chromvar" in fname or "difftf" in fname):
            return True
        return False

    # ── 로더 ──────────────────────────────────────────────────────────

    def _load_csv(self, path: Path) -> pd.DataFrame:
        sep = "\t" if path.suffix.lower() == ".tsv" else ","
        df = pd.read_csv(path, sep=sep, encoding="utf-8")
        return self._normalize_csv_columns(df)

    def _load_parquet(self, path: Path) -> pd.DataFrame:
        df = pd.read_parquet(path)
        return self._normalize_parquet_columns(df)

    def _normalize_csv_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """diff_tf.csv 컬럼 → 표준 컬럼명."""
        rename = {}
        for col in df.columns:
            cl = col.lower().strip().strip('"')
            if cl == "motif":
                rename[col] = SC.CHROMVAR_MOTIF_ID
            elif cl in ("mean_compare", "mean_zscore_compare"):
                rename[col] = SC.CHROMVAR_MEAN_COMPARE
            elif cl in ("mean_base", "mean_zscore_base"):
                rename[col] = SC.CHROMVAR_MEAN_BASE
            elif cl in ("delta", "delta_zscore"):
                rename[col] = SC.CHROMVAR_DELTA
            elif cl == "p_value":
                rename[col] = SC.CHROMVAR_PVALUE
            elif cl == "padj":
                rename[col] = SC.CHROMVAR_PADJ
            elif cl == "name":
                rename[col] = SC.CHROMVAR_TF_NAME

        df = df.rename(columns=rename)
        for col in [SC.CHROMVAR_MEAN_COMPARE, SC.CHROMVAR_MEAN_BASE,
                    SC.CHROMVAR_DELTA, SC.CHROMVAR_PVALUE, SC.CHROMVAR_PADJ]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df.reset_index(drop=True)

    def _normalize_parquet_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """seqviewer parquet 컬럼 → 표준 컬럼명."""
        rename = {}
        for col in df.columns:
            cl = col.lower()
            if cl == "tf_name":
                rename[col] = SC.CHROMVAR_MOTIF_ID    # 실제로 JASPAR ID
            elif cl == "mean_zscore_compare":
                rename[col] = SC.CHROMVAR_MEAN_COMPARE
            elif cl == "mean_zscore_base":
                rename[col] = SC.CHROMVAR_MEAN_BASE
            elif cl == "delta_zscore":
                rename[col] = SC.CHROMVAR_DELTA
            elif cl == "p_value":
                rename[col] = SC.CHROMVAR_PVALUE
            elif cl == "padj":
                rename[col] = SC.CHROMVAR_PADJ

        df = df.rename(columns=rename)
        for col in [SC.CHROMVAR_MEAN_COMPARE, SC.CHROMVAR_MEAN_BASE,
                    SC.CHROMVAR_DELTA, SC.CHROMVAR_PVALUE, SC.CHROMVAR_PADJ]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df.reset_index(drop=True)

    # ── TF 이름 조인 ──────────────────────────────────────────────────

    def _find_variability_file(self, data_path: Path) -> Optional[Path]:
        """data_path 기준으로 tf_variability.csv 를 탐색 (최대 3단계 상위 디렉토리)."""
        search_dirs = [data_path.parent]
        for _ in range(3):
            search_dirs.append(search_dirs[-1].parent)

        for d in search_dirs:
            for fname in _VARIABILITY_NAMES:
                candidate = d / fname
                if candidate.exists():
                    return candidate
                # chromvar 서브디렉토리
                candidate2 = d / "chromvar" / fname
                if candidate2.exists():
                    return candidate2
        return None

    def _join_tf_names(self, df: pd.DataFrame, var_path: Path) -> pd.DataFrame:
        """tf_variability.csv 의 name 컬럼을 motif ID 기준으로 조인."""
        try:
            var = pd.read_csv(var_path, encoding="utf-8")
            # 컬럼명 정규화
            var.columns = [c.lower().strip().strip('"') for c in var.columns]
            if "motif" not in var.columns or "name" not in var.columns:
                return df
            name_map = var.set_index("motif")["name"].to_dict()
            df[SC.CHROMVAR_TF_NAME] = df[SC.CHROMVAR_MOTIF_ID].map(name_map)
            # 매핑 실패한 경우 JASPAR ID 사용
            mask = df[SC.CHROMVAR_TF_NAME].isna()
            df.loc[mask, SC.CHROMVAR_TF_NAME] = df.loc[mask, SC.CHROMVAR_MOTIF_ID]
        except Exception as e:
            logger.warning(f"Failed to join TF names: {e}")
        return df
