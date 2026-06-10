"""
TF Motif Enrichment Result Loader

HOMER findMotifsGenome.pl 및 MEME-Suite AME 결과 파일을 파싱한다.

지원 파일:
  - HOMER: knownResults.txt  (탭 구분, 헤더 1행)
  - MEME AME: ame.tsv        (탭 구분, '#' 주석 행 제거 후 파싱)

Usage:
    loader = MotifLoader()
    dataset = loader.load(Path("homer_up_results/knownResults.txt"), name="UP peaks")
    dataset = loader.load(Path("ame_up_results/ame.tsv"), name="UP peaks (AME)")
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

import pandas as pd

from models.data_models import Dataset, DatasetType
from models.standard_columns import StandardColumns as SC

logger = logging.getLogger(__name__)


class MotifLoader:
    """HOMER knownResults.txt / MEME AME ame.tsv 로더."""

    def load(self, path: Path, name: Optional[str] = None) -> Dataset:
        path = Path(path)
        name = name or path.stem
        fname = path.name.lower()

        if fname == "knownresults.txt" or "knownresults" in fname:
            df = self._parse_homer(path)
            source = "HOMER"
        elif fname == "ame.tsv" or fname.endswith("_ame.tsv"):
            df = self._parse_ame(path)
            source = "AME"
        else:
            # 내용으로 자동 감지
            df, source = self._autodetect(path)

        logger.info(f"MotifLoader ({source}): {len(df)} motifs from {path.name}")
        return Dataset(
            name=name,
            dataset_type=DatasetType.MOTIF_ENRICHMENT,
            file_path=path,
            dataframe=df,
            original_columns={},
            metadata={"source_tool": source, "file_name": path.name},
        )

    # ── 파일 형식 감지 ────────────────────────────────────────────────────

    @staticmethod
    def is_motif_file(path: Path) -> bool:
        """파일명/내용으로 motif enrichment 결과 파일인지 판별."""
        fname = path.name.lower()
        if fname in ("knownresults.txt", "ame.tsv"):
            return True
        if "knownresult" in fname and fname.endswith(".txt"):
            return True
        if fname.endswith("_ame.tsv"):
            return True
        # 내용 헤더로 감지
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                head = f.read(500)
            if "Motif Name\tConsensus\tP-value" in head:
                return True
            if "motif_id\tmotif_alt_id" in head or "rank\tmotif_db" in head:
                return True
        except OSError:
            pass
        return False

    # ── HOMER 파서 ────────────────────────────────────────────────────────

    def _parse_homer(self, path: Path) -> pd.DataFrame:
        """
        HOMER knownResults.txt 파싱.

        컬럼 예:
          Motif Name | Consensus | P-value | Log P-value | q-value(Benjamini)
          | # of Target Sequences with Motif(of N Total)
          | % of Targets Sequences with Motif
          | # of Background Sequences with Motif(of N Total)
          | % of Background Sequences with Motif
        """
        df = pd.read_csv(path, sep="\t", encoding="utf-8")

        rename = {}
        for col in df.columns:
            cl = col.lower().strip()
            if "motif name" in cl:
                rename[col] = "_raw_motif_name"
            elif cl == "consensus":
                rename[col] = SC.CONSENSUS
            elif cl == "p-value":
                rename[col] = SC.MOTIF_PVALUE
            elif "log p-value" in cl:
                rename[col] = SC.MOTIF_LOG_PVALUE
            elif "q-value" in cl or "benjamini" in cl:
                rename[col] = SC.MOTIF_QVALUE
            elif "% of target" in cl:
                rename[col] = "_raw_target_pct"
            elif "% of background" in cl:
                rename[col] = "_raw_bg_pct"
            elif "# of target" in cl:
                rename[col] = "_raw_target_count"
            elif "# of background" in cl:
                rename[col] = "_raw_bg_count"

        df = df.rename(columns=rename)

        # motif_name: "IRF1(IRF)/HepG2.../Homer" → "IRF1"
        if "_raw_motif_name" in df.columns:
            df[SC.MOTIF_NAME] = df["_raw_motif_name"].apply(self._extract_tf_name)
            df[SC.MOTIF_ID] = df["_raw_motif_name"].apply(self._extract_motif_db_id)
            df.drop(columns=["_raw_motif_name"], inplace=True)

        # "50.62%" → 50.62
        for raw_col, std_col in [("_raw_target_pct", SC.TARGET_PCT), ("_raw_bg_pct", SC.BG_PCT)]:
            if raw_col in df.columns:
                df[std_col] = df[raw_col].astype(str).str.replace("%", "").str.strip()
                df[std_col] = pd.to_numeric(df[std_col], errors="coerce")
                df.drop(columns=[raw_col], inplace=True)

        # "771(of 1523)" → 771
        for raw_col, std_col in [("_raw_target_count", SC.TARGET_COUNT), ("_raw_bg_count", SC.BG_COUNT)]:
            if raw_col in df.columns:
                df[std_col] = df[raw_col].astype(str).apply(self._extract_count)
                df.drop(columns=[raw_col], inplace=True)

        # -log10(p) 계산 (log_pvalue가 없을 경우)
        if SC.MOTIF_LOG_PVALUE not in df.columns and SC.MOTIF_PVALUE in df.columns:
            import numpy as np
            pv = pd.to_numeric(df[SC.MOTIF_PVALUE], errors="coerce").clip(lower=1e-300)
            df[SC.MOTIF_LOG_PVALUE] = -np.log10(pv)

        # log p-value가 음수(HOMER 원본)이면 절댓값 사용
        if SC.MOTIF_LOG_PVALUE in df.columns:
            df[SC.MOTIF_LOG_PVALUE] = pd.to_numeric(df[SC.MOTIF_LOG_PVALUE], errors="coerce").abs()

        df[SC.MOTIF_PVALUE] = pd.to_numeric(df.get(SC.MOTIF_PVALUE, pd.Series(dtype=float)), errors="coerce")
        df[SC.MOTIF_QVALUE] = pd.to_numeric(df.get(SC.MOTIF_QVALUE, pd.Series(dtype=float)), errors="coerce")

        return df.reset_index(drop=True)

    # ── MEME AME 파서 ─────────────────────────────────────────────────────

    def _parse_ame(self, path: Path) -> pd.DataFrame:
        """
        MEME AME ame.tsv 파싱.

        '#' 시작 주석 행 제거 후 탭 구분 파싱.
        주요 컬럼: rank, motif_id, motif_alt_id, consensus, p-value, adj_p-value
        """
        rows = []
        header = None
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("#"):
                    continue
                parts = line.rstrip("\n").split("\t")
                if header is None:
                    header = parts
                else:
                    rows.append(parts)

        if header is None:
            raise ValueError(f"No header found in AME file: {path}")

        df = pd.DataFrame(rows, columns=header)

        rename = {}
        for col in df.columns:
            cl = col.lower().strip()
            if cl == "motif_alt_id":
                rename[col] = SC.MOTIF_NAME
            elif cl == "motif_id":
                rename[col] = SC.MOTIF_ID
            elif cl == "consensus":
                rename[col] = SC.CONSENSUS
            elif cl == "p-value":
                rename[col] = SC.MOTIF_PVALUE
            elif cl in ("adj_p-value", "adj_pvalue"):
                rename[col] = SC.MOTIF_QVALUE

        df = df.rename(columns=rename)

        # 숫자 변환
        for col in [SC.MOTIF_PVALUE, SC.MOTIF_QVALUE]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # -log10(p) 계산
        import numpy as np
        if SC.MOTIF_PVALUE in df.columns:
            pv = df[SC.MOTIF_PVALUE].clip(lower=1e-300)
            df[SC.MOTIF_LOG_PVALUE] = -np.log10(pv)

        # motif_name이 없으면 motif_id 사용
        if SC.MOTIF_NAME not in df.columns and SC.MOTIF_ID in df.columns:
            df[SC.MOTIF_NAME] = df[SC.MOTIF_ID]

        return df.reset_index(drop=True)

    # ── 자동 감지 ─────────────────────────────────────────────────────────

    def _autodetect(self, path: Path):
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                head = f.read(300)
        except OSError as e:
            raise ValueError(f"Cannot read file: {path}") from e

        if "Motif Name\tConsensus\tP-value" in head:
            return self._parse_homer(path), "HOMER"
        if "motif_id" in head and ("p-value" in head.lower() or "adj_p" in head.lower()):
            return self._parse_ame(path), "AME"
        raise ValueError(
            f"Cannot detect motif file format for: {path.name}\n"
            "Expected HOMER knownResults.txt or MEME AME ame.tsv"
        )

    # ── 헬퍼 ──────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_tf_name(raw: str) -> str:
        """
        "IRF1(IRF)/HepG2-IRF1-ChIP-Seq(GSE51800)/Homer" → "IRF1"
        """
        raw = str(raw).strip()
        m = re.match(r"^([A-Za-z0-9:._-]+?)(?:\(|/)", raw)
        return m.group(1) if m else raw.split("/")[0]

    @staticmethod
    def _extract_motif_db_id(raw: str) -> str:
        """
        "IRF1(IRF)/HepG2.../Homer" → database 출처 문자열 (슬래시 2번째 이후)
        """
        parts = str(raw).split("/")
        return parts[-1] if len(parts) >= 2 else ""

    @staticmethod
    def _extract_count(raw: str) -> int:
        """"771(of 1523)" → 771"""
        m = re.match(r"^\s*(\d+)", str(raw))
        return int(m.group(1)) if m else 0
