"""
Unit tests for src/utils/deg_input.py (plan §12 deg_input cases).

- ① extract_deg_from_dataset : threshold boundary / direction / empty / KeyError / casing
- ② parse_gene_list          : 다구분자 / dedupe / 빈 토큰 / 비유전자 경고 / casing
- ③ extract_meta_signature   : fdr 직접 사용 / BH 폴백(multipletests 대조) / 변종 효과컬럼 /
                               부호 방향 / concordant 필터 / ranked(sign rule + z)
- extract_ranked             : standalone prerank ranking
- determinism

All offline (no network, F1). No dependency on parallel cache/mapper slices.
"""

import logging
import math

import numpy as np
import pandas as pd
import pytest
from statsmodels.stats.multitest import multipletests

from models.enrichment_models import VALID_DIRECTIONS, VALID_ORGANISMS
from utils.deg_input import (
    DegInput,
    extract_deg_from_dataset,
    extract_meta_signature,
    extract_ranked,
    normalize_case,
    parse_gene_list,
)


def _make_de_df() -> pd.DataFrame:
    """경계값 포함 DE 프레임:
    A  = 경계 통과 (|log2fc|==fc_min, adj_pvalue==fdr_max)
    B  = 경계 통과 (|log2fc|==fc_min, DOWN)
    C  = |log2fc|가 fc_min 미만 → 제외
    D  = 통과 (UP)
    E  = adj_pvalue가 fdr_max 초과 → 제외
    F  = log2fc==0 (|0| < fc_min) → 제외
    G  = adj_pvalue NaN → 제외
    H  = log2fc NaN → 제외
    """
    return pd.DataFrame({
        "symbol": ["A", "B", "C", "D", "E", "F", "G", "H"],
        "log2fc": [1.0, -1.0, 0.999, 2.0, -3.0, 0.0, 4.0, np.nan],
        "adj_pvalue": [0.05, 0.01, 0.05, 0.049, 0.0501, 0.04, np.nan, 0.02],
    })


class TestNormalizeCase:
    """species-aware casing (A6)."""

    def test_human_upper(self):
        assert normalize_case("Tp53", "human") == "TP53"
        assert normalize_case("brca1", "human") == "BRCA1"

    def test_mouse_title(self):
        assert normalize_case("TP53", "mouse") == "Tp53"
        assert normalize_case("tp53", "mouse") == "Tp53"
        assert normalize_case("BRCA1", "mouse") == "Brca1"

    def test_unknown_species_raises(self):
        with pytest.raises(ValueError):
            normalize_case("TP53", "rat")


class TestExtractDegFromDataset:
    """source ① 단일 DE 데이터셋."""

    def test_threshold_boundary_inclusive(self):
        r = extract_deg_from_dataset(_make_de_df(), fc_min=1.0, fdr_max=0.05, direction="TOTAL")
        assert r.symbols == ["A", "B", "D"]   # |log2fc|==fc_min, adj_pvalue==fdr_max 포함
        assert r.direction == "TOTAL"
        assert r.species == "human"
        assert r.meta["n_rows"] == 3
        assert r.meta["n_rows_input"] == 8
        assert r.meta["fc_min"] == 1.0
        assert r.meta["fdr_max"] == 0.05

    def test_direction_up_down_total(self):
        df = _make_de_df()
        assert extract_deg_from_dataset(df, 1.0, 0.05, "UP").symbols == ["A", "D"]
        assert extract_deg_from_dataset(df, 1.0, 0.05, "DOWN").symbols == ["B"]

    def test_direction_sign_boundary_at_zero(self):
        df = pd.DataFrame({"symbol": ["Z"], "log2fc": [0.0], "adj_pvalue": [0.01]})
        assert extract_deg_from_dataset(df, 0.0, 0.05, "UP").symbols == []
        assert extract_deg_from_dataset(df, 0.0, 0.05, "DOWN").symbols == []
        assert extract_deg_from_dataset(df, 0.0, 0.05, "TOTAL").symbols == ["Z"]

    def test_empty_result(self):
        df = pd.DataFrame({
            "symbol": ["X", "Y"],
            "log2fc": [1.0, -1.0],
            "adj_pvalue": [0.9, 0.9],
        })
        r = extract_deg_from_dataset(df, 1.0, 0.05, "TOTAL")
        assert r.symbols == []
        assert r.direction == "TOTAL"
        assert r.meta["n_rows"] == 0

    def test_invalid_direction_raises(self):
        df = _make_de_df()
        with pytest.raises(ValueError):
            extract_deg_from_dataset(df, 1.0, 0.05, direction="up")

    def test_missing_column_raises_keyerror(self):
        df = _make_de_df().drop(columns=["log2fc"])
        with pytest.raises(KeyError) as excinfo:
            extract_deg_from_dataset(df, 1.0, 0.05)
        assert "log2fc" in str(excinfo.value)

    def test_missing_symbol_column_raises_keyerror(self):
        df = _make_de_df().drop(columns=["symbol"])
        with pytest.raises(KeyError) as excinfo:
            extract_deg_from_dataset(df, 1.0, 0.05)
        assert "symbol" in str(excinfo.value)

    def test_custom_symbol_col(self):
        df = _make_de_df().rename(columns={"symbol": "Gene"})
        r = extract_deg_from_dataset(df, 1.0, 0.05, "TOTAL", symbol_col="Gene")
        assert r.symbols == ["A", "B", "D"]

    def test_species_case_normalization(self):
        df = pd.DataFrame({
            "symbol": ["Tp53", "Brca1", "BRCA1"],
            "log2fc": [1.0, 2.0, 3.0],
            "adj_pvalue": [0.01, 0.01, 0.01],
        })
        human = extract_deg_from_dataset(df, 1.0, 0.05, "TOTAL", species="human")
        assert human.symbols == ["TP53", "BRCA1"]  # Tp53→TP53, Brca1/BRCA1→BRCA1 dedupe
        mouse = extract_deg_from_dataset(df, 1.0, 0.05, "TOTAL", species="mouse")
        assert mouse.symbols == ["Tp53", "Brca1"]  # Brca1/BRCA1→Brca1 dedupe

    def test_order_preserving_dedupe(self):
        df = pd.DataFrame({
            "symbol": ["B", "A", "B", "A"],
            "log2fc": [1.0, 1.0, 1.0, 1.0],
            "adj_pvalue": [0.01, 0.01, 0.01, 0.01],
        })
        assert extract_deg_from_dataset(df, 1.0, 0.05, "TOTAL").symbols == ["B", "A"]

    def test_deg_input_defaults(self):
        di = DegInput(symbols=["A"], direction="TOTAL", species="human", meta={})
        assert di.ranked is None


class TestParseGeneList:
    """source ② 붙여넣기 gene list."""

    def test_mixed_delimiters(self):
        text = "A;B,C\tD E\nF"   # 줄/세미콜론/콤마/탭/공백 혼합
        syms, warns = parse_gene_list(text, "human")
        assert syms == ["A", "B", "C", "D", "E", "F"]
        assert warns == []

    def test_dedupe_order_preserved_case_insensitive(self):
        text = "A, b, A\nB\ta"
        syms, warns = parse_gene_list(text, "human")
        assert syms == ["A", "B"]
        assert warns == []

    def test_empty_tokens_dropped_and_warned(self):
        # [\s,;\t]+ 는 내부 연속 구분자를 병합 → 빈 프래그먼트는 가장자리 구분자에서만 발생
        syms, warns = parse_gene_list(",TP53,,BRCA1,")
        assert syms == ["TP53", "BRCA1"]
        assert warns.count("empty gene token ignored") == 2

    def test_trailing_newline_no_warning(self):
        syms, warns = parse_gene_list("TP53\n")
        assert syms == ["TP53"]
        assert warns == []

    def test_empty_input(self):
        assert parse_gene_list("") == ([], [])
        assert parse_gene_list("   \n  ") == ([], [])

    def test_non_gene_token_warns(self):
        syms, warns = parse_gene_list("GENE1 ???GENE2\nGENE3")
        assert syms == ["GENE1", "GENE3"]
        assert any("non-gene token ignored" in w and "???GENE2" in w for w in warns)

    def test_hash_token_warns(self):
        syms, warns = parse_gene_list("GENE1 #broken GENE2")
        assert syms == ["GENE1", "GENE2"]
        assert any("#broken" in w for w in warns)

    def test_case_normalization_per_species(self):
        text = "Tp53; TP53\ttp53, MYC"
        syms_h, _ = parse_gene_list(text, "human")
        assert syms_h == ["TP53", "MYC"]
        syms_m, _ = parse_gene_list(text, "mouse")
        assert syms_m == ["Tp53", "Myc"]

    def test_direction_is_total(self):
        # ② 소스는 direction=TOTAL 고정 — 반환 타입은 (symbols, warnings)
        _, _ = parse_gene_list("A, B")


class TestExtractMetaSignature:
    """source ③ meta-signature (Comparison: Statistics) + ranked (G16)."""

    def test_fdr_column_used_directly(self):
        df = pd.DataFrame({
            "symbol": ["A", "B", "C", "D"],
            "meta_pvalue_fisher": [0.001, 0.002, 0.01, 0.02],
            "meta_fdr_fisher": [0.05, 0.06, 0.03, 0.09],
            "meta_log2fc_mean": [1.5, -0.5, 2.0, 3.0],
            "meta_direction": ["UP", "DOWN", "UP", "UP"],
        })
        r = extract_meta_signature(df, 0.05)
        # B는 raw p로는 통과(0.002)지만 meta_fdr_fisher 0.06 초과 → fdr 컬럼 직접 사용 증명
        assert r.symbols == ["A", "C"]
        assert r.meta["fdr_fallback"] is None
        assert r.meta["fdr_column_used"] == "meta_fdr_fisher"
        assert r.meta["cutoff"] == 0.05

    def test_bh_fallback_matches_multipletests(self):
        pvals = [0.001, 0.002, 0.01, 0.02, 0.05, 0.3]
        symbols = ["A", "B", "C", "D", "E", "F"]
        df = pd.DataFrame({
            "symbol": symbols,
            "meta_pvalue_fisher": pvals,
            "meta_log2fc_mean": [1.5, -0.5, 2.0, 0.5, -1.0, 0.5],
        })
        ref_adj = multipletests(np.asarray(pvals), method="fdr_bh")[1]
        ref_symbols = [s for s, a in zip(symbols, ref_adj) if a <= 0.05]
        r = extract_meta_signature(df, 0.05)
        assert r.symbols == ref_symbols
        assert "E" not in r.symbols  # raw 0.05≤0.05지만 BH 보정 후 0.06 초과 → 폴백 적용 증명
        assert r.meta["fdr_fallback"] == "bh_on_meta_pvalue_fisher"
        assert r.meta["fdr_column_used"] == "bh(meta_pvalue_fisher)"
        assert r.meta["n_rows"] == len(ref_symbols)

    def test_bh_fallback_logs_warning(self, caplog):
        df = pd.DataFrame({
            "symbol": ["A", "B"],
            "meta_pvalue_fisher": [0.001, 0.002],
            "meta_log2fc_mean": [1.0, 2.0],
        })
        with caplog.at_level(logging.WARNING):
            extract_meta_signature(df, 0.05)
        assert "meta_fdr_fisher missing -> BH fallback on meta_pvalue_fisher" in caplog.text

    def test_variant_effect_column(self):
        df = pd.DataFrame({
            "symbol": ["A", "B"],
            "meta_pvalue_fisher": [0.001, 0.002],
            "meta_fdr_fisher": [0.01, 0.02],
            "meta_log2fe_mean": [1.0, -2.0],
        })
        r = extract_meta_signature(df, 0.05)
        assert r.meta["effect_column_used"] == "meta_log2fe_mean"
        assert r.direction == "TOTAL"  # 혼합 부호

    def test_missing_both_effect_columns_raises(self):
        df = pd.DataFrame({"symbol": ["A"], "meta_pvalue_fisher": [0.001]})
        with pytest.raises(KeyError) as excinfo:
            extract_meta_signature(df, 0.05)
        assert "meta_log2fc_mean" in str(excinfo.value)
        assert "meta_log2fe_mean" in str(excinfo.value)

    def test_missing_symbol_raises(self):
        df = pd.DataFrame({"meta_pvalue_fisher": [0.001], "meta_log2fc_mean": [1.0]})
        with pytest.raises(KeyError):
            extract_meta_signature(df, 0.05)

    def test_missing_fdr_and_pvalue_raises(self):
        df = pd.DataFrame({"symbol": ["A"], "meta_log2fc_mean": [1.0]})
        with pytest.raises(KeyError):
            extract_meta_signature(df, 0.05)

    def test_sign_direction(self):
        up = pd.DataFrame({
            "symbol": ["A", "B"],
            "meta_pvalue_fisher": [0.001, 0.002],
            "meta_log2fc_mean": [1.0, 2.0],
        })
        down = up.copy()
        down["meta_log2fc_mean"] = [-1.0, -2.0]
        mixed = up.copy()
        mixed["meta_log2fc_mean"] = [1.0, -2.0]
        assert extract_meta_signature(up, 0.05).direction == "UP"
        assert extract_meta_signature(down, 0.05).direction == "DOWN"
        assert extract_meta_signature(mixed, 0.05).direction == "TOTAL"

    def test_concordant_filter_case_insensitive(self):
        df = pd.DataFrame({
            "symbol": ["A", "B", "C", "D"],
            "meta_pvalue_fisher": [0.001, 0.001, 0.001, 0.001],
            "meta_log2fc_mean": [1.5, -0.5, 2.0, 3.0],
            "meta_direction": ["UP", "down", "Down", "DOWN"],
        })
        all_rows = extract_meta_signature(df, 0.05)
        assert all_rows.symbols == ["A", "B", "C", "D"]
        assert all_rows.meta["direction_concordant_applied"] is False
        conc = extract_meta_signature(df, 0.05, require_direction_concordant=True)
        assert conc.symbols == ["A", "B"]  # C(UP vs Down), D(UP vs DOWN) 제거
        assert conc.meta["direction_concordant_applied"] is True
        assert conc.meta["direction_concordant_required"] is True

    def test_concordant_no_column_keeps_rows(self):
        df = pd.DataFrame({
            "symbol": ["A", "B"],
            "meta_pvalue_fisher": [0.001, 0.001],
            "meta_log2fc_mean": [1.0, -1.0],
        })
        r = extract_meta_signature(df, 0.05, require_direction_concordant=True)
        assert r.symbols == ["A", "B"]
        assert r.meta["direction_concordant_applied"] is False

    def test_ranked_sign_rule(self):
        df = pd.DataFrame({
            "symbol": ["UP1", "DN1", "ZERO"],
            "meta_pvalue_fisher": [0.01, 0.001, 0.05],
            "meta_fdr_fisher": [0.01, 0.001, 0.05],
            "meta_log2fc_mean": [2.0, -3.0, 0.0],
        })
        r = extract_meta_signature(df, 0.05)
        assert r.ranked is not None
        score = dict(r.ranked)
        assert score["UP1"] == pytest.approx(-math.log10(0.01) * 1.0)
        assert score["DN1"] == pytest.approx(-math.log10(0.001) * -1.0)
        assert score["ZERO"] == pytest.approx(0.0)
        assert r.meta["ranked_from"] == "-log10(meta_pvalue_fisher)*sign(meta_log2fc_mean)"

    def test_ranked_uses_z(self):
        df = pd.DataFrame({
            "symbol": ["A", "B", "C"],
            "meta_z": [1.25, -0.75, 0.0],
            "meta_pvalue_fisher": [0.001, 0.001, 0.001],
            "meta_fdr_fisher": [0.01, 0.01, 0.01],
            "meta_log2fc_mean": [1.0, -1.0, 1.0],
        })
        r = extract_meta_signature(df, 0.05)
        assert r.ranked == [("A", 1.25), ("B", -0.75), ("C", 0.0)]
        assert r.meta["ranked_from"] == "meta_z"

    def test_empty_meta_result(self):
        df = pd.DataFrame({
            "symbol": ["A", "B"],
            "meta_pvalue_fisher": [0.3, 0.4],
            "meta_log2fc_mean": [1.0, -1.0],
        })
        r = extract_meta_signature(df, 0.05)
        assert r.symbols == []
        assert r.direction == "TOTAL"
        assert r.ranked == []
        assert r.meta["n_rows"] == 0

    def test_combined_datasets_recorded(self):
        df = pd.DataFrame({
            "symbol": ["A", "B"],
            "meta_pvalue_fisher": [0.001, 0.001],
            "meta_log2fc_mean": [1.0, 2.0],
            "datasets": ["d2", "d1"],
        })
        r = extract_meta_signature(df, 0.05)
        assert r.meta["combined_datasets"] == ["d1", "d2"]

    def test_nan_pvalue_row_survives_via_fdr(self):
        # BH 폴백 시 NaN pvalue 행은 multipletests 오염 없이 제외
        df = pd.DataFrame({
            "symbol": ["A", "B", "C"],
            "meta_pvalue_fisher": [0.001, 0.002, np.nan],
            "meta_log2fc_mean": [1.0, 2.0, 3.0],
        })
        r = extract_meta_signature(df, 0.05)
        assert r.symbols == ["A", "B"]


class TestExtractRanked:
    """standalone prerank ranking helper (G16)."""

    def test_sign_rule_standalone(self):
        df = pd.DataFrame({
            "symbol": ["UP", "DN"],
            "meta_pvalue_fisher": [0.01, 0.001],
            "meta_log2fc_mean": [2.0, -3.0],
        })
        ranked = extract_ranked(df, 0.05)
        assert ranked[0][0] == "UP"
        assert ranked[0][1] == pytest.approx(-math.log10(0.01) * 1.0)
        assert ranked[1][0] == "DN"
        assert ranked[1][1] == pytest.approx(-math.log10(0.001) * -1.0)

    def test_z_without_effect_columns(self):
        df = pd.DataFrame({
            "symbol": ["A", "B"],
            "meta_z": [1.25, -0.75],
            "meta_fdr_fisher": [0.01, 0.02],
        })
        assert extract_ranked(df, 0.05) == [("A", 1.25), ("B", -0.75)]

    def test_no_ranking_column_raises(self):
        df = pd.DataFrame({"symbol": ["A"], "meta_log2fc_mean": [1.0]})
        with pytest.raises(KeyError):
            extract_ranked(df, 0.05)


class TestDeterminism:
    """동일 입력 → 동일 출력."""

    def test_dataset_extraction(self):
        df = _make_de_df()
        a = extract_deg_from_dataset(df, 1.0, 0.05, "UP", "human")
        b = extract_deg_from_dataset(df, 1.0, 0.05, "UP", "human")
        assert a == b

    def test_paste_parsing(self):
        text = "Tp53; TP53\ttp53, MYC\nMYC"
        assert parse_gene_list(text, "human") == parse_gene_list(text, "human")
        assert parse_gene_list(text, "mouse") == parse_gene_list(text, "mouse")

    def test_meta_extraction(self):
        df = pd.DataFrame({
            "symbol": ["A", "B", "C"],
            "meta_pvalue_fisher": [0.001, 0.002, 0.05],
            "meta_log2fe_mean": [1.0, -2.0, 3.0],
            "meta_direction": ["UP", "down", "UP"],
        })
        a = extract_meta_signature(df, 0.05, require_direction_concordant=True)
        b = extract_meta_signature(df, 0.05, require_direction_concordant=True)
        assert a == b
        assert extract_ranked(df, 0.05) == extract_ranked(df, 0.05)


class TestSharedContract:
    """enrichment_models 공유 상수와의 정합 (리더 모듈과 분리 독립)."""

    def test_direction_and_species_values(self):
        df = _make_de_df()
        r = extract_deg_from_dataset(df, 1.0, 0.05, "TOTAL", "mouse")
        assert r.species in VALID_ORGANISMS
        assert r.direction in VALID_DIRECTIONS
        m = extract_meta_signature(
            pd.DataFrame({
                "symbol": ["A"], "meta_pvalue_fisher": [0.001], "meta_log2fc_mean": [1.0],
            }),
            0.05,
        )
        assert m.species in VALID_ORGANISMS
        assert m.direction in VALID_DIRECTIONS
        assert VALID_ORGANISMS == ("human", "mouse")
        assert VALID_DIRECTIONS == ("UP", "DOWN", "TOTAL")
