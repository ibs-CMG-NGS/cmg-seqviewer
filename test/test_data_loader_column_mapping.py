"""
DataLoader._map_columns() 매칭 우선순위 회귀 테스트.

표준 컬럼 단위로 완전일치->부분일치를 순서대로 처리하면, 패턴 딕셔너리 뒤쪽
표준 컬럼(예: adj_pvalue)의 완전 일치 대상을, 앞쪽 표준 컬럼(pvalue)의 부분
포함 단계("pvalue" in "adj_pvalue")가 먼저 가로채는 버그가 있었다 — 이 앱 자신의
표준 컬럼명을 그대로 쓴 파일(예: 파이프라인이 이미 adj_pvalue로 내보낸 경우)조차
잘못 매핑되거나 통째로 누락되는, "일반 반입"과 직결되는 문제였다.
"""

import pandas as pd

from models.data_models import DatasetType
from utils.data_loader import DataLoader


def test_adj_pvalue_only_maps_correctly_not_stolen_by_pvalue_pattern():
    # 별도 raw pvalue 컬럼이 없을 때 — 'pvalue' 패턴의 부분 포함 단계가 'adj_pvalue'
    # 헤더를 먼저 가로채면 adj_pvalue가 아예 미매핑됐었다.
    df = pd.DataFrame({"gene_id": ["G1"], "log2fc": [1.0], "adj_pvalue": [0.03]})
    loader = DataLoader()
    mapping = loader._map_columns(df, DatasetType.DIFFERENTIAL_EXPRESSION)
    assert mapping.get("adj_pvalue") == "adj_pvalue"


def test_pvalue_and_adj_pvalue_both_present_map_independently():
    # 둘 다 있을 때 — pvalue는 pvalue로, adj_pvalue는 adj_pvalue로 각각 매핑돼야 함
    # (이전엔 adj_pvalue가 완전히 누락됐음: 자기 패턴 목록에 'adj_pvalue' 리터럴이
    # 없었고, pvalue 표준 컬럼이 이미 'pvalue' 헤더를 가져가 버려 그 쪽 부분포함
    # 단계도 못 돌았음).
    df = pd.DataFrame({
        "gene_id": ["G1"], "log2fc": [1.0], "pvalue": [0.01], "adj_pvalue": [0.03],
    })
    loader = DataLoader()
    mapping = loader._map_columns(df, DatasetType.DIFFERENTIAL_EXPRESSION)
    assert mapping.get("pvalue") == "pvalue"
    assert mapping.get("adj_pvalue") == "adj_pvalue"


def test_de_required_columns_satisfied_for_canonical_headers():
    # 회귀 방지: 이 앱 표준 헤더 그대로인 가장 단순한 파일이 "필수 컬럼 누락"으로
    # 안 걸려야 한다 (끝까지: _has_required_columns 통과 확인).
    df = pd.DataFrame({"gene_id": ["G1", "G2"], "log2fc": [1.0, -2.0],
                       "adj_pvalue": [0.03, 0.001]})
    loader = DataLoader()
    dt = loader._detect_dataset_type(df)
    assert dt == DatasetType.DIFFERENTIAL_EXPRESSION
    mapping = loader._map_columns(df, dt)
    check_mapping = {v: k for k, v in mapping.items()}
    assert loader._has_required_columns(check_mapping, dt)


def test_go_fdr_pattern_also_recognizes_adj_pvalue_alias():
    # GO 쪽 fdr 패턴에도 동일한 'adj_pvalue' 별칭이 빠져 있었다 (GO 결과를 app이
    # 이미 표준화한 뒤 재반입하는 경우 등 — description/fdr 둘 다 'adj_pvalue'가
    # 아니라 term/fdr 패턴이라 직접 영향은 없지만, pvalue/fdr 공존 시나리오는 DE와
    # 동일 구조이므로 같이 고정).
    df = pd.DataFrame({
        "description": ["term A"], "gene_count": [5], "pvalue": [0.01], "adj_pvalue": [0.02],
    })
    loader = DataLoader()
    mapping = loader._map_columns(df, DatasetType.GO_ANALYSIS)
    assert mapping.get("pvalue") == "pvalue"
    assert mapping.get("adj_pvalue") == "fdr"
