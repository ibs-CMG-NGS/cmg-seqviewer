"""
utils.recipe.Recipe 테스트 — YAML/JSON 파싱, 알 수 없는 키/모드 거부(G14: 조용한
fallback 금지), FilterCriteria 변환.
"""

import pytest

from models.data_models import FilterCriteria, FilterMode
from utils.recipe import Recipe


def test_load_yaml(tmp_path):
    f = tmp_path / "recipe.yaml"
    f.write_text(
        "input: data.xlsx\n"
        "filter:\n"
        "  mode: statistical\n"
        "  adj_pvalue_max: 0.01\n"
        "output:\n"
        "  table: out.xlsx\n",
        encoding="utf-8",
    )
    recipe = Recipe.load(f)
    assert recipe.input == "data.xlsx"
    assert recipe.filter["adj_pvalue_max"] == 0.01
    assert recipe.output["table"] == "out.xlsx"


def test_load_json(tmp_path):
    f = tmp_path / "recipe.json"
    f.write_text('{"input": "data.xlsx", "filter": {"adj_pvalue_max": 0.2}}', encoding="utf-8")
    recipe = Recipe.load(f)
    assert recipe.input == "data.xlsx"
    assert recipe.filter["adj_pvalue_max"] == 0.2


def test_missing_input_key_raises(tmp_path):
    f = tmp_path / "recipe.yaml"
    f.write_text("filter:\n  adj_pvalue_max: 0.05\n", encoding="utf-8")
    with pytest.raises(ValueError, match="input"):
        Recipe.load(f)


def test_unknown_top_level_key_raises(tmp_path):
    f = tmp_path / "recipe.yaml"
    f.write_text("input: data.xlsx\ntypo_key: 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="typo_key"):
        Recipe.load(f)


def test_unsupported_extension_raises(tmp_path):
    f = tmp_path / "recipe.txt"
    f.write_text("input: data.xlsx\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported recipe format"):
        Recipe.load(f)


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        Recipe.load(tmp_path / "does_not_exist.yaml")


class TestBuildFilterCriteria:
    def test_defaults_match_filtercriteria(self):
        recipe = Recipe(input="x.xlsx")
        criteria = recipe.build_filter_criteria()
        assert criteria == FilterCriteria()

    def test_mode_string_converted_to_enum(self):
        recipe = Recipe(input="x.xlsx", filter={"mode": "gene_list", "gene_list": ["A", "B"]})
        criteria = recipe.build_filter_criteria()
        assert criteria.mode == FilterMode.GENE_LIST
        assert criteria.gene_list == ["A", "B"]

    def test_invalid_mode_raises(self):
        recipe = Recipe(input="x.xlsx", filter={"mode": "not_a_real_mode"})
        with pytest.raises(ValueError, match="not_a_real_mode"):
            recipe.build_filter_criteria()

    def test_unknown_filter_key_raises(self):
        recipe = Recipe(input="x.xlsx", filter={"adj_pvalue_mxa": 0.05})  # 오탈자
        with pytest.raises(ValueError, match="adj_pvalue_mxa"):
            recipe.build_filter_criteria()

    def test_custom_thresholds_applied(self):
        recipe = Recipe(input="x.xlsx", filter={"adj_pvalue_max": 0.01, "log2fc_min": 2.0})
        criteria = recipe.build_filter_criteria()
        assert criteria.adj_pvalue_max == 0.01
        assert criteria.log2fc_min == 2.0
