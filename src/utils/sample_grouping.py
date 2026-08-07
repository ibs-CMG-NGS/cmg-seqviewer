"""샘플 컬럼명 → 조건(그룹) 추론 (공용).

여러 다이얼로그(PCA · Multi-Group Heatmap · Gene Expression Bar)가 같은 규칙으로
복제(replicate)를 조건으로 묶도록 단일 소스로 제공한다.
"""
import re


def auto_group_samples(sample_cols) -> dict:
    """샘플 컬럼명에서 조건(그룹)을 추출해 복제를 하나로 묶는다.

    끝의 전역 인덱스(_S20 등)와 복제 번호를 제거해 조건명을 얻는다.
      JHL_Con1_S20 / JHL_Con2_S21 / JHL_Con3_S22 -> 'JHL_Con'
      JHL_1D_1_S23 / JHL_1D_2_S24 / JHL_1D_3_S25 -> 'JHL_1D'
      JHL_24h_1_S26 -> 'JHL_24h'
    반환: {group_label: [cols...]} (입력 순서 보존)
    """
    groups: dict = {}
    for c in sample_cols:
        g = re.sub(r'[_\-.]?[Ss]\d+$', '', str(c))   # 전역 인덱스 (_S20)
        g = re.sub(r'[_\-.]?\d+$', '', g)             # 복제 번호
        g = g.strip('_-. ') or str(c)
        groups.setdefault(g, []).append(c)
    return groups


def useful_grouping(groups: dict, n_samples: int) -> bool:
    """복제를 실제로 묶는 유효한 그룹핑인가 (그룹 1개도, 샘플당 1개도 아님)."""
    k = len(groups)
    return bool(groups) and 1 < k < n_samples and any(len(v) > 1 for v in groups.values())
