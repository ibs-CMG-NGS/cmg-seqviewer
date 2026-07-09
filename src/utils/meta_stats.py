"""
Late-integration meta-analysis statistics.

여러 독립 데이터셋(코호트)에서 나온 유전자별 p-value / log2FC 를 결합해
메타 시그널을 산출한다. 원시 count 재처리 없이 이미 계산된 DE 통계만 사용한다.

- Fisher's method: p-value 유의성 크기를 결합
- Stouffer's method: 발현 변화 방향성(부호)까지 반영한 z-score 결합
- Random-effects (DerSimonian-Laird): log2FC + SE로 통합 효과크기·이질성(I²) 추정
"""
from typing import Optional, Sequence, Dict

import numpy as np
from scipy import stats as st


def random_effects(effects: Sequence[float],
                   ses: Sequence[float]) -> Optional[Dict[str, float]]:
    """DerSimonian-Laird random-effects 메타 분석 (효과크기 결합).

    각 연구의 효과크기(log2FC)와 표준오차(SE)를 역분산 가중으로 통합하고,
    연구 간 이질성(τ²)을 추가해 random-effects 통합 추정치를 낸다.

    Args:
        effects: 데이터셋별 log2FC. 검정 안 된 데이터셋은 NaN → 자동 제외.
        ses:     effects와 정렬된 데이터셋별 표준오차(lfcSE). ≤0/NaN도 제외.

    Returns:
        dict 또는 유효 데이터셋 2개 미만이면 None.
        키: meta_effect_log2fc, meta_effect_se, meta_ci_low, meta_ci_high,
            meta_pvalue_re, meta_i2, meta_effect_k
    """
    y = np.asarray(effects, dtype=float)
    s = np.asarray(ses, dtype=float)
    mask = np.isfinite(y) & np.isfinite(s) & (s > 0)
    y, s = y[mask], s[mask]
    k = int(y.size)
    if k < 2:
        return None

    v = s ** 2                      # 분산
    w = 1.0 / v                     # fixed-effect 가중
    sw = float(np.sum(w))
    y_fixed = float(np.sum(w * y) / sw)
    Q = float(np.sum(w * (y - y_fixed) ** 2))

    # DerSimonian-Laird τ²
    c = sw - float(np.sum(w ** 2)) / sw
    tau2 = max(0.0, (Q - (k - 1)) / c) if c > 0 else 0.0
    i2 = max(0.0, (Q - (k - 1)) / Q) * 100.0 if Q > 0 else 0.0

    # random-effects 가중
    w_re = 1.0 / (v + tau2)
    sw_re = float(np.sum(w_re))
    effect = float(np.sum(w_re * y) / sw_re)
    se = float(np.sqrt(1.0 / sw_re))
    z = effect / se if se > 0 else 0.0
    p_re = float(2.0 * st.norm.sf(abs(z)))

    return {
        'meta_effect_log2fc': effect,
        'meta_effect_se':     se,
        'meta_ci_low':        effect - 1.96 * se,
        'meta_ci_high':       effect + 1.96 * se,
        'meta_pvalue_re':     p_re,
        'meta_i2':            i2,
        'meta_effect_k':      k,
    }


def benjamini_hochberg(pvals: Sequence[float]) -> np.ndarray:
    """Benjamini-Hochberg FDR 보정. NaN은 그대로 통과.

    메타 p-value(예: Fisher 결합값)를 유전자 전체에 대해 다중검정 보정해
    메타 FDR을 산출할 때 사용한다.
    """
    p = np.asarray(pvals, dtype=float)
    out = np.full(p.shape, np.nan)
    finite = np.isfinite(p)
    q = p[finite]
    n = q.size
    if n == 0:
        return out
    order = np.argsort(q)
    ranked = q[order] * n / (np.arange(n) + 1)
    # 뒤에서부터 누적 최소로 단조성 보장
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    adj = np.empty(n)
    adj[order] = np.clip(ranked, 0.0, 1.0)
    out[finite] = adj
    return out


def combine_pvalues(pvals: Sequence[float],
                    lfcs: Sequence[float]) -> Optional[Dict[str, float]]:
    """데이터셋 간 p-value / log2FC 를 메타 결합.

    Args:
        pvals: 데이터셋별 raw p-value (권장). 유전자가 검정되지 않은 데이터셋은
               NaN 으로 두면 자동 제외된다. 결합 후 메타 FDR은 호출부에서
               benjamini_hochberg() 로 별도 산출한다.
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
