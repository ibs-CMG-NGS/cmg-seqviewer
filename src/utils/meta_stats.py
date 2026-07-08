"""
Late-integration meta-analysis statistics.

여러 독립 데이터셋(코호트)에서 나온 유전자별 p-value / log2FC 를 결합해
메타 시그널을 산출한다. 원시 count 재처리 없이 이미 계산된 DE 통계만 사용한다.

- Fisher's method: p-value 유의성 크기를 결합
- Stouffer's method: 발현 변화 방향성(부호)까지 반영한 z-score 결합
"""
from typing import Optional, Sequence, Dict

import numpy as np
from scipy import stats as st


def combine_pvalues(pvals: Sequence[float],
                    lfcs: Sequence[float]) -> Optional[Dict[str, float]]:
    """데이터셋 간 p-value / log2FC 를 메타 결합.

    Args:
        pvals: 데이터셋별 (adjusted) p-value. 유전자가 검정되지 않은 데이터셋은
               NaN 으로 두면 자동 제외된다.
        lfcs:  pvals 와 정렬된 데이터셋별 log2 fold change.

    Returns:
        메타 통계 dict, 유효 데이터셋이 2개 미만이면 None.
        키: meta_pvalue_fisher, meta_pvalue_stouffer, meta_z,
            meta_log2fc_mean, meta_direction, meta_found_in
    """
    p = np.asarray(pvals, dtype=float)
    l = np.asarray(lfcs, dtype=float)
    mask = np.isfinite(p) & np.isfinite(l)
    p, l = p[mask], l[mask]
    k = int(p.size)
    if k < 2:
        return None

    # log(0)/무한대 방지
    p = np.clip(p, 1e-300, 1.0)

    # Fisher: X = -2 Σ ln(p) ~ chi2(2k)
    chi2 = -2.0 * float(np.sum(np.log(p)))
    fisher = float(st.chi2.sf(chi2, df=2 * k))

    # Stouffer (방향성 반영): 양측 p → |z|, 부호는 log2FC 에서
    #   z_i = Φ^-1(1 - p_i/2) * sign(lfc_i),  meta_z = Σ z_i / sqrt(k)
    z = st.norm.isf(p / 2.0) * np.sign(l)
    meta_z = float(np.sum(z) / np.sqrt(k))
    stouffer = float(2.0 * st.norm.sf(abs(meta_z)))

    signs = np.sign(l)
    concordant = bool(np.all(signs == signs[0]) and signs[0] != 0)

    return {
        'meta_pvalue_fisher': fisher,
        'meta_pvalue_stouffer': stouffer,
        'meta_z': meta_z,
        'meta_log2fc_mean': float(np.mean(l)),
        'meta_direction': 'concordant' if concordant else 'discordant',
        'meta_found_in': k,
    }
