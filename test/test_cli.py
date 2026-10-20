"""
cli.py 테스트 — 커맨드라인으로 load/filter가 GUI와 동일한 경로(utils.dataset_detection
/ MainPresenter.compute_filtered_df)를 거쳐 정확히 동작하는지, Qt 없이 끝까지
동작하는지, 인식 안 되는 필수 컬럼은 exit code != 0 + 명확한 메시지로 실패하는지.
"""

import pandas as pd
import pytest

import cli


def _write_de_xlsx(tmp_path):
    df = pd.DataFrame({
        "gene_id": [f"G{i}" for i in range(10)],
        "log2fc": [2.0, -3.0, 0.1, 1.5, -0.2, 4.0, -1.8, 0.05, 2.2, -2.5],
        "adj_pvalue": [0.001, 0.02, 0.5, 0.04, 0.9, 0.0001, 0.03, 0.8, 0.01, 0.045],
    })
    f = tmp_path / "de.xlsx"
    df.to_excel(f, index=False)
    return f


class TestCliLoad:
    def test_load_reports_type_and_validity(self, tmp_path, capsys):
        f = _write_de_xlsx(tmp_path)
        rc = cli.main(["load", str(f)])
        out = capsys.readouterr().out
        assert rc == 0
        assert "type: differential_expression" in out
        assert "rows: 10" in out
        assert "valid: True" in out

    def test_load_atac_hint_fails_clearly_without_mapper(self, tmp_path, capsys):
        df = pd.DataFrame({"Region": ["r1"], "LFC": [1.5], "FDR_adj": [0.01]})
        f = tmp_path / "weird_atac.parquet"
        df.to_parquet(f)
        rc = cli.main(["load", str(f), "--type", "atac"])
        err = capsys.readouterr().err
        assert rc == 1
        assert "Missing required ATAC-seq columns" in err
        assert "Region" in err  # 실제 사용 가능한 컬럼도 메시지에 포함

    def test_load_de_parquet(self, tmp_path, capsys):
        df = pd.DataFrame({
            "gene_id": ["G1", "G2"], "log2fc": [1.0, -2.0],
            "adj_pvalue": [0.01, 0.02], "baseMean": [100.0, 200.0],
        })
        f = tmp_path / "de.parquet"
        df.to_parquet(f)
        rc = cli.main(["load", str(f)])
        out = capsys.readouterr().out
        assert rc == 0
        assert "type: differential_expression" in out
        assert "rows: 2" in out

    def test_load_json_reports_machine_readable_fields(self, tmp_path, capsys):
        import json
        f = _write_de_xlsx(tmp_path)
        rc = cli.main(["load", str(f), "--json"])
        out = capsys.readouterr().out
        assert rc == 0
        report = json.loads(out)
        assert report["dataset_type"] == "differential_expression"
        assert report["rows"] == 10
        assert report["valid"] is True
        assert report["missing_required_columns"] == []
        assert report["file"] == str(f)

    def test_load_type_hint_forces_multi_group(self, tmp_path, capsys):
        # padj/샘플 3개 패턴이 아니어도 --type으로 강제 가능해야 한다.
        df = pd.DataFrame({
            "gene_id": ["G1"], "condition": ["x"],
            "s1": [1.0], "s2": [2.0], "s3": [3.0],
        })
        f = tmp_path / "expression.csv"
        df.to_csv(f, index=False)
        rc = cli.main(["load", str(f), "--type", "multi_group", "--json"])
        out = capsys.readouterr().out
        assert rc == 0
        assert '"multi_group"' in out

    def test_load_composition_parquet_json(self, tmp_path, capsys):
        import json
        df = pd.DataFrame({
            "cell_type": ["T", "B"],
            "PropMean.Control": [0.6, 0.4],
            "PropMean.Treatment": [0.5, 0.5],
            "PropRatio": [-0.1, 0.1],
            "P.Value": [0.01, 0.02],
            "FDR": [0.02, 0.03],
        })
        f = tmp_path / "composition.parquet"
        df.to_parquet(f)
        rc = cli.main(["load", str(f), "--json"])
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["dataset_type"] == "composition"
        assert report["valid"] is True
        assert report["missing_required_columns"] == []

    def test_load_expression_summary_json(self, tmp_path, capsys):
        import json
        df = pd.DataFrame({
            "gene_id": ["G1", "G2"], "gene_name": ["A", "B"],
            "CT_A": [1.0, 2.0], "CT_B": [3.0, 4.0],
        })
        f = tmp_path / "expression.parquet"
        df.to_parquet(f)
        rc = cli.main(["load", str(f), "--type", "expression_summary", "--json"])
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["dataset_type"] == "expression_summary"
        assert report["valid"] is True
        assert report["missing_required_columns"] == []


class TestCliFilter:
    def test_filter_writes_table(self, tmp_path, capsys):
        f = _write_de_xlsx(tmp_path)
        out_path = tmp_path / "filtered.csv"
        rc = cli.main(["filter", str(f), "--adj-pvalue-max", "0.05",
                       "--log2fc-min", "1.0", "--out", str(out_path)])
        assert rc == 0
        assert out_path.exists()
        result = pd.read_csv(out_path)
        assert len(result) == 7
        assert set(result["gene_id"]) == {"G0", "G1", "G3", "G5", "G6", "G8", "G9"}

    def test_filter_without_out_prints_to_stdout(self, tmp_path, capsys):
        f = _write_de_xlsx(tmp_path)
        rc = cli.main(["filter", str(f), "--adj-pvalue-max", "0.05", "--log2fc-min", "1.0"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "filtered: 7/10 rows" in out
        assert "G0" in out

    def test_filter_defaults_match_filtercriteria_defaults(self, tmp_path):
        # --adj-pvalue-max/--log2fc-min 등을 생략해도 FilterCriteria 기본값과 같아야
        # GUI 기본 필터와 CLI 기본 필터가 어긋나지 않는다.
        from models.data_models import FilterCriteria
        parser = cli.build_parser()
        args = parser.parse_args(["filter", "dummy.xlsx"])
        defaults = FilterCriteria()
        assert args.adj_pvalue_max == defaults.adj_pvalue_max
        assert args.log2fc_min == defaults.log2fc_min
        assert args.regulation == defaults.regulation_direction
        assert args.fdr_max == defaults.fdr_max
        assert args.mg_padj_max == defaults.mg_padj_max
        assert args.mg_basemean_min == defaults.mg_basemean_min

    def test_unrecognized_output_format_raises(self, tmp_path, capsys):
        f = _write_de_xlsx(tmp_path)
        rc = cli.main(["filter", str(f), "--out", str(tmp_path / "out.pdf")])
        err = capsys.readouterr().err
        assert rc == 1
        assert "Unsupported output format" in err


class TestCliRun:
    def test_run_recipe_filters_and_writes(self, tmp_path, capsys):
        de_f = _write_de_xlsx(tmp_path)
        out_f = tmp_path / "out.csv"
        recipe_f = tmp_path / "recipe.yaml"
        recipe_f.write_text(
            f"input: {de_f}\n"
            "filter:\n"
            "  adj_pvalue_max: 0.05\n"
            "  log2fc_min: 1.0\n"
            f"output:\n  table: {out_f}\n",
            encoding="utf-8",
        )
        rc = cli.main(["run", str(recipe_f)])
        out = capsys.readouterr().out
        assert rc == 0
        assert "filtered: 7/10 rows" in out
        assert out_f.exists()
        assert len(pd.read_csv(out_f)) == 7

    def test_run_bad_recipe_fails_clearly(self, tmp_path, capsys):
        recipe_f = tmp_path / "recipe.yaml"
        recipe_f.write_text("input: data.xlsx\nbad_key: 1\n", encoding="utf-8")
        rc = cli.main(["run", str(recipe_f)])
        err = capsys.readouterr().err
        assert rc == 1
        assert "bad_key" in err


class TestCliBatch:
    def _write_recipe(self, tmp_path, out_table="filtered.xlsx"):
        recipe_f = tmp_path / "recipe.yaml"
        recipe_f.write_text(
            "input: unused.xlsx\n"
            "filter:\n"
            "  adj_pvalue_max: 0.05\n"
            "  log2fc_min: 1.0\n"
            f"output:\n  table: {out_table}\n",
            encoding="utf-8",
        )
        return recipe_f

    def test_batch_applies_recipe_to_all_matched_files(self, tmp_path, capsys):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        for i in range(3):
            df = pd.DataFrame({
                "gene_id": [f"G{i}_{j}" for j in range(5)],
                "log2fc": [2.0, -3.0, 0.1, 1.5, -0.2],
                "adj_pvalue": [0.001, 0.02, 0.5, 0.04, 0.9],
            })
            df.to_excel(data_dir / f"sample{i}.xlsx", index=False)

        recipe_f = self._write_recipe(tmp_path)
        out_dir = tmp_path / "results"
        manifest_f = tmp_path / "manifest.json"
        rc = cli.main([
            "batch", str(recipe_f),
            "--inputs", str(data_dir / "*.xlsx"),
            "--out-dir", str(out_dir),
            "--manifest", str(manifest_f),
        ])
        out = capsys.readouterr().out
        assert rc == 0
        assert "batch complete: 3/3 succeeded" in out
        assert (out_dir / "sample0.xlsx").exists()
        assert (out_dir / "sample1.xlsx").exists()
        assert (out_dir / "sample2.xlsx").exists()

        import json
        manifest = json.loads(manifest_f.read_text(encoding="utf-8"))
        assert len(manifest) == 3
        assert all(e["status"] == "ok" for e in manifest)
        assert all(e["rows_filtered"] == 3 for e in manifest)  # G_0/G_1/G_3 패턴, 5개 중 3개 통과

    def test_batch_partial_failure_continues_and_reports(self, tmp_path, capsys):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        good = pd.DataFrame({
            "gene_id": ["G0", "G1"], "log2fc": [2.0, -3.0], "adj_pvalue": [0.001, 0.001],
        })
        good.to_excel(data_dir / "good.xlsx", index=False)
        bad = pd.DataFrame({"Name": ["x"], "Hits": [1], "Adj_P": [0.1]})
        bad.to_excel(data_dir / "bad.xlsx", index=False)

        recipe_f = self._write_recipe(tmp_path)
        rc = cli.main(["batch", str(recipe_f), "--inputs", str(data_dir / "*.xlsx")])
        captured = capsys.readouterr()
        assert rc == 1  # 부분 실패 -> non-zero
        assert "[ok] good.xlsx" in captured.out
        assert "batch complete: 1/2 succeeded" in captured.out
        assert "[FAIL] bad.xlsx" in captured.err

    def test_batch_no_matches_fails(self, tmp_path, capsys):
        recipe_f = self._write_recipe(tmp_path)
        rc = cli.main(["batch", str(recipe_f), "--inputs", str(tmp_path / "nope" / "*.xlsx")])
        err = capsys.readouterr().err
        assert rc == 1
        assert "No files matched" in err


def test_cli_module_never_constructs_qapplication():
    # 서버/HPC 등 display 없는 환경에서도 그대로 동작해야 한다 — 다른 테스트가
    # 먼저 QApplication을 만들어둘 수 있어 런타임 "instance() is None" 체크는
    # 실행 순서에 flaky하므로, 소스 자체에 QApplication 생성 코드가 없다는 걸
    # 정적으로 확인한다.
    import inspect
    source = inspect.getsource(cli)
    assert "QApplication(" not in source
