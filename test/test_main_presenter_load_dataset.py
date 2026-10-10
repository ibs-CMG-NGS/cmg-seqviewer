"""
MainPresenter.load_dataset()의 dataset_type_hint 테스트 (반입 일반성 감사 후속).

"Open ATAC-seq Dataset..." 메뉴가 넘기는 dataset_type_hint는 자동 감지(스니핑)
체인을 건너뛰고 해당 타입 로더로 직행해야 한다 — peak_id 등 컬럼명이 감지
휴리스틱과 안 맞는 파일도(§감사 finding #5) 사용자가 명시한 타입으로 강제되고,
필수 컬럼이 없으면 컬럼 매퍼로 수동 매핑하게 된다.
"""

from types import SimpleNamespace

import pandas as pd
from PyQt6.QtWidgets import QApplication

from models.data_models import DatasetType
from presenters.main_presenter import MainPresenter

_QAPP = QApplication.instance() or QApplication([])


def _make_presenter():
    presenter = MainPresenter(SimpleNamespace())
    captured = {}
    presenter._store_and_signal_dataset = lambda ds, start: captured.__setitem__("ds", ds)
    return presenter, captured


class TestDatasetTypeHint:
    def test_hint_forces_atac_even_with_unrecognized_columns(self, tmp_path):
        # 컬럼명이 ATACSeqLoader.is_atac_dataframe()의 peak-id 패턴과 전혀 안 맞아서
        # 힌트 없이 열었으면 자동 감지 체인이 ATAC로 인식조차 못 했을 파일.
        df = pd.DataFrame([{"Region": "r1", "LFC": 1.2, "FDR_adj": 0.01}])
        f = tmp_path / "weird_atac_naming.parquet"
        df.to_parquet(f)

        presenter, captured = _make_presenter()

        def fake_mapper(d, dataset_type, auto_mapping):
            assert dataset_type == DatasetType.ATAC_SEQ
            return {"peak_id": "Region", "log2fc": "LFC", "adj_pvalue": "FDR_adj"}

        import gui.column_mapper_dialog as cmd_module

        class FakeDialog:
            def __init__(self, df, dataset_type, auto_mapping, parent):
                self._mapping = fake_mapper(df, dataset_type, auto_mapping)

            def exec(self):
                return True

            def get_mapping(self):
                return self._mapping

            def should_save_mapping(self):
                return False

        orig = cmd_module.ColumnMapperDialog
        cmd_module.ColumnMapperDialog = FakeDialog
        try:
            presenter.load_dataset(f, custom_name="ATACWithHint",
                                   dataset_type_hint=DatasetType.ATAC_SEQ)
        finally:
            cmd_module.ColumnMapperDialog = orig

        ds = captured.get("ds")
        assert ds is not None, "ATAC hint path failed to produce a dataset"
        assert ds.dataset_type == DatasetType.ATAC_SEQ
        assert ds.is_valid

    def test_no_hint_preserves_existing_auto_detection(self, tmp_path):
        # 회귀 방지: 힌트 없이 호출하면 기존 자동 감지 체인이 그대로 동작해야 함
        # (GO 표준 프레임 parquet 복원 경로, P3-7).
        df = pd.DataFrame([
            {"term_id": "GO:0000001", "description": "x", "gene_count": 2, "fdr": 0.01,
             "gene_ratio": "2/10", "bg_ratio": "4/100", "gene_symbols": "A/B",
             "direction": "TOTAL", "ontology": "BP", "gene_set": "TOTAL",
             "_gene_set": {"A", "B"}},
        ])
        f = tmp_path / "go_frame.parquet"
        df.to_parquet(f)

        presenter, captured = _make_presenter()
        presenter.load_dataset(f, custom_name="GOFrame")

        ds = captured.get("ds")
        assert ds is not None
        assert ds.dataset_type == DatasetType.GO_ANALYSIS


class TestLoadDatasetNoShadowedPandas:
    def test_excel_de_load_does_not_unboundlocalerror(self, tmp_path):
        # 회귀 방지: load_dataset()의 csv/parquet 분기 안에 있던 로컬
        # `import pandas as pd`가 (그 분기가 실행되는지와 무관하게, 파이썬 스코프
        # 규칙상 함수 전체의 pd를 로컬로 만들어) 뒤쪽 Excel 분기의 pd.read_excel()을
        # UnboundLocalError로 깨뜨리고 있었다 — .xlsx 파일 하나만 로드해도 100% 재현
        # (Phase 0 CLI 타당성 검증 중 발견. dataset_type_hint 작업 때 같은 패턴을
        # ATAC 분기에서 한 번 고쳤는데 csv/parquet 분기에 하나 더 남아 있었다).
        xlsx_df = pd.DataFrame({
            "gene_id": ["G1", "G2"], "log2fc": [1.0, -2.0], "adj_pvalue": [0.01, 0.02],
        })
        xlsx_f = tmp_path / "de.xlsx"
        xlsx_df.to_excel(xlsx_f, index=False)

        presenter, captured = _make_presenter()
        presenter.load_dataset(xlsx_f, custom_name="DE")

        ds = captured.get("ds")
        assert ds is not None, "Excel load failed (pd shadowing regression)"
        assert ds.dataset_type == DatasetType.DIFFERENTIAL_EXPRESSION
        assert ds.is_valid
