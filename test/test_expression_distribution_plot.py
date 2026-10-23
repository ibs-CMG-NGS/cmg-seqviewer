"""Expression distribution renderer smoke test (Agg, no Qt)."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

from plots.expression_distribution import render_expression_distribution


def _df():
    rows = []
    for gene in ("Agrp", "Pomc"):
        for ct in ("CT_A", "CT_B", "CT_C"):
            for sample, condition in (("s1", "Control"), ("s2", "Control"),
                                      ("s3", "Treated")):
                rows.append({
                    "gene_id": gene,
                    "gene_name": gene,
                    "cell_type": ct,
                    "sample": sample,
                    "condition": condition,
                    "n_cells": 20,
                    "pct_expressing": 50.0,
                    "mean_expression": 1.0 + ("Treated" == condition) * 0.5,
                })
    return pd.DataFrame(rows)


def _render(plot_type):
    fig = plt.figure(figsize=(8, 4))
    info = render_expression_distribution(fig, _df(), {
        "genes": ["Agrp", "Pomc"],
        "cell_types": ["CT_A", "CT_B", "CT_C"],
        "group_by": "condition",
        "plot_type": plot_type,
        "layout": "pseudobulk",
        "pct_scale": "0-100",
        "min_n_cells": 10,
        "value_column": "mean_expression",
    })
    assert info["groups"] == ["Control", "Treated"]
    assert info["labels"] == ["CT_A", "CT_B", "CT_C"]
    assert len(fig.axes) == 2
    # multi-gene panels hide repeated x labels on all but the last panel
    assert all(not label.get_text() for label in fig.axes[0].get_xticklabels())
    plt.close(fig)


def test_render_violin_box_strip():
    for plot_type in ("violin", "box", "strip", "box+points"):
        _render(plot_type)


def test_quantile_violin_falls_back_to_box():
    df = _df().drop(columns=["sample"]).drop_duplicates(["gene_id", "cell_type"])
    for col, base in (("p10", 0.5), ("p25", 0.8), ("median", 1.0),
                      ("p75", 1.2), ("p90", 1.4)):
        df[col] = base
    fig = plt.figure(figsize=(8, 4))
    info = render_expression_distribution(fig, df, {
        "genes": ["Agrp"],
        "cell_types": ["CT_A", "CT_B", "CT_C"],
        "group_by": "condition",
        "plot_type": "violin",
        "layout": "quantile",
        "value_column": "mean_expression",
    })
    assert info["warnings"]
    assert fig.axes
    plt.close(fig)
