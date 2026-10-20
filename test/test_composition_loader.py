"""Cell-type Composition 로더/감지/렌더러 테스트."""

import pandas as pd

from models.data_models import DatasetType
from utils.composition_loader import CompositionLoader, prop_mean_condition
from utils.data_loader import DataLoader
from utils.multi_group_loader import MultiGroupLoader


def _comp_df():
    return pd.DataFrame({
        "cell_type": ["T cell", "B cell", "NK cell"],
        "PropMean.Control": [0.45, 0.30, 0.25],
        "PropMean.Treatment": [0.55, 0.20, 0.25],
        "PropRatio": [0.10, -0.10, 0.0],
        "P.Value": [0.001, 0.02, 0.9],
        "FDR": [0.003, 0.03, 0.95],
    })


def test_detection_and_standardization():
    df = _comp_df()
    assert CompositionLoader.is_composition_dataframe(df)

    ds = CompositionLoader().load_from_dataframe(df, name="comp")
    assert ds.dataset_type == DatasetType.COMPOSITION
    assert ds.is_valid
    assert "prop_ratio" in ds.dataframe.columns
    assert "pvalue" in ds.dataframe.columns
    assert "fdr" in ds.dataframe.columns
    assert ds.metadata["conditions"] == ["Control", "Treatment"]
    assert ds.metadata["mean_columns"] == ["PropMean.Control", "PropMean.Treatment"]


def test_alias_standardization():
    df = pd.DataFrame({
        "CellType": ["T", "B"],
        "prop_mean_ctrl": [0.6, 0.4],
        "prop_mean_trt": [0.5, 0.5],
        "Prop.Ratio": [-0.1, 0.1],
        "P.Value": [0.01, 0.02],
        "adj_pvalue": [0.02, 0.03],
    })
    ds = CompositionLoader().load_from_dataframe(df, name="aliased")
    assert list(ds.dataframe["cell_type"]) == ["T", "B"]
    assert {"prop_ratio", "pvalue", "fdr"} <= set(ds.dataframe.columns)
    assert ds.metadata["conditions"] == ["ctrl", "trt"]


def test_not_detected_for_de_or_multi_group():
    de = pd.DataFrame({"gene_id": ["G1"], "log2fc": [1.0], "adj_pvalue": [0.01]})
    assert not CompositionLoader.is_composition_dataframe(de)

    mg = pd.DataFrame({
        "gene_id": ["G1"], "padj": [0.01],
        "s1": [1.0], "s2": [2.0], "s3": [3.0],
    })
    assert not CompositionLoader.is_composition_dataframe(mg)


def test_data_loader_detects_composition_before_multi_group():
    df = _comp_df().rename(columns={"P.Value": "p_value", "FDR": "padj"})
    # padj + 숫자형 PropMean 3개↑ 조합이어도 MULTI_GROUP이 아니라 COMPOSITION이어야 한다.
    assert MultiGroupLoader.is_multi_group_dataframe(df)
    assert DataLoader()._detect_dataset_type(df) == DatasetType.COMPOSITION


def test_condition_label_parsing():
    assert prop_mean_condition("PropMean.Control") == "Control"
    assert prop_mean_condition("prop_mean_24h") == "24h"
    assert prop_mean_condition("PropMean") is None
    assert prop_mean_condition("sample_1") is None


def test_render_composition_smoke():
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.figure import Figure
    from plots.composition import render_composition, select_composition_rows

    ds = CompositionLoader().load_from_dataframe(_comp_df(), name="comp")
    base = {
        "mean_columns": ds.metadata["mean_columns"],
        "conditions": ds.metadata["conditions"],
        "fdr_threshold": 0.05,
        "top_n": 30,
    }
    for mode in ("ratio", "means"):
        fig = Figure()
        ax = fig.add_subplot(111)
        render_composition(ax, ds.dataframe, {**base, "mode": mode})
        assert ax.get_xticks().size or ax.get_yticks().size

    rows = select_composition_rows(ds.dataframe, {
        **base, "mode": "ratio", "significant_only": True})
    assert list(rows["cell_type"]) == ["T cell", "B cell"]
