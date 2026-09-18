"""
DEG 입력 추상화 — plan §6.1 (G3/G16/A6).

3소스 + ranked 인터페이스:
- DegInput                 : 공통 출력 dataclass (symbols/direction/species/meta/ranked).
- normalize_case           : species-aware 심볼 casing (human=UPPER, mouse=Title — A6).
- extract_deg_from_dataset : ① 단일 DE 데이터셋 (log2fc/adj_pvalue 임계값 + direction).
- parse_gene_list          : ② 붙여넣기 gene list (다구분자 + 경고).
- extract_meta_signature   : ③ meta-signature (Comparison: Statistics) + ranked (G16).
- extract_ranked           : standalone prerank ranking helper (G16).

컬럼 계약은 standard columns(`symbol`/`log2fc`/`adj_pvalue` 등)이며 alias 매핑
(logfc→log2fc, padj→adj_pvalue)은 data_loader가 처리한다 — 여기서는 표준 컬럼명
부재 시 명시적 KeyError (G14 — 조용한 fallback 금지).
meta_fdr_fisher 부재 시 meta_pvalue_fisher에 BH 직접 적용 (main_window.py:2192-2194
동일 규칙). 효과크기 변종 폴백: meta_log2fc_mean 우선, 없으면 meta_log2fe_mean.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from statsmodels.stats.multitest import multipletests

logger = logging.getLogger(__name__)

# meta 시트 (Comparison: Statistics) 컬럼
_META_FDR = "meta_fdr_fisher"
_META_PVALUE = "meta_pvalue_fisher"
_META_EFFECT_MAIN = "meta_log2fc_mean"
_META_EFFECT_VARIANT = "meta_log2fe_mean"
_META_DIRECTION = "meta_direction"
_META_Z = "meta_z"
_META_DATASET_COLS = ("meta_datasets", "datasets", "dataset")

_PASTE_SPLIT_RE = re.compile(r"[\s,;\t]+")
_GENE_LIKE_RE = re.compile(r"^[A-Za-z0-9._-]+$")

VALID_DIRECTIONS = ("UP", "DOWN", "TOTAL")
VALID_ORGANISMS = ("human", "mouse")


@dataclass
class DegInput:
    """DEG 입력 공통 출력 (plan §6.1 G3/G16)."""

    symbols: List[str]                        # species-aware cased, deduped, order-preserving
    direction: str                            # 'UP' | 'DOWN' | 'TOTAL'
    species: str                              # 'human' | 'mouse'
    meta: Dict[str, Any]                      # 추출 메타데이터 (§6.9 재현성 기록)
    ranked: Optional[List[Tuple[str, float]]] = None  # Phase 4 prerank (G16)


def normalize_case(symbol: str, species: str) -> str:
    """Species-aware 심볼 casing (A6): human=UPPER, mouse=Title."""
    if species == "human":
        return symbol.upper()
    if species == "mouse":
        return symbol.title()
    raise ValueError(f"unknown species: {species!r} (expected 'human' or 'mouse')")


def _require_columns(df: pd.DataFrame, required: List[str], fname: str) -> None:
    """필수 컬럼 검증 — 부재 시 명시적 KeyError (G14)."""
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(
            f"{fname}: missing required column(s) {missing} — "
            "alias mapping (logfc→log2fc, padj→adj_pvalue) is handled by data_loader, so the "
            "DataFrame must already use standard column names."
        )


def _clean_symbols(raw_values, species: str) -> List[str]:
    """NaN/빈 심볼 제거 + normalize_case + 순서 보존 dedupe."""
    seen = set()
    out = []
    for v in raw_values:
        if pd.isna(v):
            continue
        s = str(v).strip()
        if not s:
            continue
        normalized = normalize_case(s, species)
        if normalized not in seen:
            seen.add(normalized)
            out.append(normalized)
    return out


def extract_deg_from_dataset(
    dataframe: pd.DataFrame,
    fc_min: float,
    fdr_max: float,
    direction: str = "TOTAL",
    species: str = "human",
    symbol_col: str = "symbol",
) -> DegInput:
    """source ① 단일 DE 데이터셋 → DegInput.

    필터: abs(log2fc) >= fc_min AND adj_pvalue <= fdr_max AND
    direction=UP → log2fc>0 / DOWN → log2fc<0 / TOTAL → 전부 (경계 포함).
    심볼은 species-aware casing + 순서 보존 dedupe (A6).
    """
    if direction not in VALID_DIRECTIONS:
        raise ValueError(
            f"invalid direction: {direction!r} (expected one of {VALID_DIRECTIONS})"
        )
    _require_columns(dataframe, [symbol_col, "log2fc", "adj_pvalue"], "extract_deg_from_dataset")

    df = dataframe
    log2fc = pd.to_numeric(df["log2fc"], errors="coerce")
    adj_pvalue = pd.to_numeric(df["adj_pvalue"], errors="coerce")
    mask = log2fc.abs() >= fc_min
    mask &= adj_pvalue <= fdr_max
    if direction == "UP":
        mask &= log2fc > 0.0
    elif direction == "DOWN":
        mask &= log2fc < 0.0
    # NaN 값은 모든 비교가 False → 자동 제외

    passed = df.loc[mask.to_numpy()]
    symbols = _clean_symbols(passed[symbol_col].tolist(), species)
    meta: Dict[str, Any] = {
        "source": "dataset",
        "fc_min": fc_min,
        "fdr_max": fdr_max,
        "direction_requested": direction,
        "columns_used": [symbol_col, "log2fc", "adj_pvalue"],
        "n_rows_input": int(len(df)),
        "n_rows": int(len(passed)),
    }
    return DegInput(symbols=symbols, direction=direction, species=species, meta=meta)


def parse_gene_list(text: str, species: str = "human") -> Tuple[List[str], List[str]]:
    """source ② 붙여넣기 gene list → (symbols, warnings).

    [\\s,;\\t]+ 분리 → strip → 빈 토큰 제거 → gene-like 검증 → normalize_case →
    순서 보존 dedupe. 경고 1건/비유전자 토큰, 1건/빈 프래그먼트(빈 줄/연속 구분자).
    완전히 빈 입력은 경고 없이 빈 목록 반환 (trailing newline은 strip으로 제거).
    """
    text = text.strip()
    if not text:
        return [], []
    symbols: List[str] = []
    warnings: List[str] = []
    seen = set()
    for fragment in _PASTE_SPLIT_RE.split(text):
        token = fragment.strip()
        if not token:
            warnings.append("empty gene token ignored")
            continue
        if not _GENE_LIKE_RE.fullmatch(token):
            warnings.append(f"non-gene token ignored: {token!r}")
            continue
        normalized = normalize_case(token, species)
        if normalized not in seen:
            seen.add(normalized)
            symbols.append(normalized)
    return symbols, warnings


def _fdr_mask(df: pd.DataFrame, cutoff: float, fname: str) -> Tuple[np.ndarray, str, bool]:
    """FDR 통과 마스크 — meta_fdr_fisher 직접 사용, 부재 시 meta_pvalue_fisher BH 폴백.

    Returns (mask, fdr_column_used, fallback_flag).
    multipletests는 NaN을 만나면 전체 결과를 NaN으로 오염시키므로 NaN을 사전 제거한다.
    """
    if _META_FDR in df.columns:
        mask = pd.to_numeric(df[_META_FDR], errors="coerce").to_numpy(dtype=float) <= cutoff
        return mask, _META_FDR, False
    if _META_PVALUE not in df.columns:
        raise KeyError(
            f"{fname}: missing FDR column {_META_FDR!r} — cannot fall back, "
            f"{_META_PVALUE!r} also absent"
        )
    logger.warning("meta_fdr_fisher missing -> BH fallback on meta_pvalue_fisher")
    pvals = pd.to_numeric(df[_META_PVALUE], errors="coerce").to_numpy(dtype=float)
    adj = np.full(len(pvals), np.nan)
    ok = ~np.isnan(pvals)
    if ok.any():
        adj[ok] = multipletests(pvals[ok], method="fdr_bh")[1]
    return adj <= cutoff, f"bh({_META_PVALUE})", True


def _effect_array(df: pd.DataFrame) -> Tuple[np.ndarray, str]:
    """효과크기 배열 — meta_log2fc_mean 우선, meta_log2fe_mean 변종 폴백 (plan §6.1)."""
    if _META_EFFECT_MAIN in df.columns:
        col = _META_EFFECT_MAIN
    elif _META_EFFECT_VARIANT in df.columns:
        col = _META_EFFECT_VARIANT
    else:
        raise KeyError(
            f"effect-size column required: neither {_META_EFFECT_MAIN!r} nor "
            f"{_META_EFFECT_VARIANT!r} present"
        )
    return pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=float), col


def _rank_score(pvalues: np.ndarray, effect: np.ndarray) -> np.ndarray:
    """-log10(pvalue) × sign(effect) — p=0은 최소 양수로 대체해 inf 방지."""
    pv = np.asarray(pvalues, dtype=float)
    ef = np.asarray(effect, dtype=float)
    safe = np.where(np.isnan(pv), np.nan, np.where(pv > 0, pv, np.finfo(float).tiny))
    return -np.log10(safe) * np.sign(ef)


def _record_combined_datasets(df: pd.DataFrame) -> Optional[List[str]]:
    """DataFrame에 결합 데이터셋 컬럼이 있으면 고유값 기록 (순서 결정적)."""
    for col in _META_DATASET_COLS:
        if col in df.columns:
            vals = sorted({str(v) for v in df[col].dropna().unique()})
            if vals:
                return vals
    return None


def extract_meta_signature(
    dataframe: pd.DataFrame,
    cutoff: float,
    require_direction_concordant: bool = False,
    species: str = "human",
) -> DegInput:
    """source ③ meta-signature (Comparison: Statistics) → DegInput (+ranked, G16).

    - FDR: meta_fdr_fisher <= cutoff (부재 시 meta_pvalue_fisher에 BH 직접 적용).
    - 효과크기: meta_log2fc_mean 우선, 없으면 meta_log2fe_mean (변종 폴백).
    - 방향: 효과크기 부호 (UP>0 / DOWN<0). require_direction_concordant=True이고
      'meta_direction' 컬럼이 있으면 부호 불일치 행 제거 (대소문자 무관).
    - ranked: 'meta_z' 있으면 z, 없으면 -log10(meta_pvalue_fisher) × sign(effect).
    """
    if "symbol" not in dataframe.columns:
        raise KeyError("extract_meta_signature: missing required column 'symbol'")
    df = dataframe
    fdr_mask, fdr_used, fallback = _fdr_mask(df, cutoff, "extract_meta_signature")
    effect, effect_col = _effect_array(df)

    keep = fdr_mask & ~np.isnan(effect)
    concordant_applied = False
    if require_direction_concordant and _META_DIRECTION in df.columns:
        concordant_applied = True
        mdir = df[_META_DIRECTION].astype(str).str.strip().str.upper().to_numpy()
        concordant = ((effect > 0) & (mdir == "UP")) | ((effect < 0) & (mdir == "DOWN"))
        keep &= concordant

    valid_sym = (
        df["symbol"].notna().to_numpy()
        & (df["symbol"].astype(str).str.strip() != "").to_numpy()
    )
    keep &= valid_sym
    sel = df.loc[keep]
    raw_symbols = df["symbol"].to_numpy()[keep]
    symbols = _clean_symbols(raw_symbols.tolist(), species)
    eff_selected = effect[keep]

    if len(eff_selected) == 0:
        overall_direction = "TOTAL"
    elif bool(np.all(eff_selected > 0)):
        overall_direction = "UP"
    elif bool(np.all(eff_selected < 0)):
        overall_direction = "DOWN"
    else:
        overall_direction = "TOTAL"

    ranked = None
    ranked_from = None
    if _META_Z in df.columns:
        z = pd.to_numeric(df[_META_Z], errors="coerce").to_numpy(dtype=float)[keep]
        ranked_from = _META_Z
        ranked = [
            (normalize_case(str(s), species), float(sc))
            for s, sc in zip(raw_symbols, z)
            if not np.isnan(sc)
        ]
    elif _META_PVALUE in df.columns:
        p = pd.to_numeric(df[_META_PVALUE], errors="coerce").to_numpy(dtype=float)[keep]
        scores = _rank_score(p, eff_selected)
        ranked_from = f"-log10({_META_PVALUE})*sign({effect_col})"
        ranked = [
            (normalize_case(str(s), species), float(sc))
            for s, sc in zip(raw_symbols, scores)
            if not np.isnan(sc)
        ]

    columns_used = ["symbol", fdr_used, effect_col]
    if concordant_applied:
        columns_used.append(_META_DIRECTION)
    if _META_Z in df.columns:
        columns_used.append(_META_Z)
    if ranked_from is not None and _META_PVALUE in df.columns:
        columns_used.append(_META_PVALUE)

    meta: Dict[str, Any] = {
        "source": "meta",
        "cutoff": cutoff,
        "fdr_column_used": fdr_used,
        "fdr_fallback": "bh_on_meta_pvalue_fisher" if fallback else None,
        "effect_column_used": effect_col,
        "direction": overall_direction,
        "direction_rule": "sign_effect",
        "direction_concordant_required": bool(require_direction_concordant),
        "direction_concordant_applied": concordant_applied,
        "ranked_from": ranked_from,
        "n_rows_input": int(len(df)),
        "n_rows": int(len(sel)),
        "columns_used": columns_used,
    }
    combined = _record_combined_datasets(df)
    if combined:
        meta["combined_datasets"] = combined
    return DegInput(
        symbols=symbols,
        direction=overall_direction,
        species=species,
        meta=meta,
        ranked=ranked,
    )


def extract_ranked(dataframe: pd.DataFrame, cutoff: float) -> List[Tuple[str, float]]:
    """Standalone prerank ranking helper (G16) — extract_meta_signature와 동일 규칙.

    meta_z 있으면 z 사용(효과크기 불필요), 없으면 -log10(meta_pvalue_fisher) ×
    sign(effect). FDR은 meta_fdr_fisher 직접 / meta_pvalue_fisher BH 폴백.
    심볼은 DataFrame 원본 값 그대로 반환 (species-aware casing은 ORA 전송(A6) 전용 —
    prerank 매핑은 Phase 4에서 결정).
    """
    if "symbol" not in dataframe.columns:
        raise KeyError("extract_ranked: missing required column 'symbol'")
    df = dataframe
    fdr_mask, _, _ = _fdr_mask(df, cutoff, "extract_ranked")
    keep = fdr_mask.copy()
    if _META_Z in df.columns:
        scores_full = pd.to_numeric(df[_META_Z], errors="coerce").to_numpy(dtype=float)
    elif _META_PVALUE in df.columns:
        effect, _ = _effect_array(df)
        keep &= ~np.isnan(effect)
        p = pd.to_numeric(df[_META_PVALUE], errors="coerce").to_numpy(dtype=float)
        scores_full = _rank_score(p, effect)
    else:
        raise KeyError(
            f"extract_ranked: cannot rank — neither {_META_Z!r} nor {_META_PVALUE!r} present"
        )
    symbols = df["symbol"].to_numpy()[keep]
    scores = scores_full[keep]
    ranked: List[Tuple[str, float]] = []
    for s, sc in zip(symbols, scores):
        if pd.isna(s) or str(s).strip() == "" or np.isnan(sc):
            continue
        ranked.append((str(s), float(sc)))
    return ranked
